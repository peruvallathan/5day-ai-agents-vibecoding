# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Security checkpoint node for the expense-approval workflow.

Responsibilities
----------------
1. PII scrubbing  — replace SSNs and credit-card numbers with labelled
   placeholders so that neither the LLM nor any log ever sees raw PII.
2. Prompt-injection detection — if the description contains adversarial
   instructions designed to coerce the model into auto-approving the
   expense, skip the LLM entirely and route to a human security reviewer.

This module is intentionally free of ADK imports so it can be unit-tested
without a running ADK runtime.  Only ``security_checkpoint`` is an ADK
node (it imports ``Event`` for routing).
"""

from __future__ import annotations

import logging
import re

from google.adk.events.event import Event

from .models import ExpenseRequest, SecurityResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "SSN",
        re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    ),
    (
        "CREDIT_CARD",
        re.compile(
            r"\b(?:"
            r"4[0-9]{12}(?:[0-9]{3})?"           # Visa (13 or 16 digits)
            r"|5[1-5][0-9]{14}"                   # Mastercard
            r"|3[47][0-9]{13}"                    # American Express
            r"|6(?:011|5[0-9]{2})[0-9]{12}"      # Discover
            r"|\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}"  # Generic spaced 16-digit
            r")\b"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Prompt-injection patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "override_instructions",
        re.compile(
            r"\b(ignore|disregard|override|bypass|forget)\b.{0,60}"
            r"\b(instructions?|rules?|above|previous|system|prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "auto_approval_coercion",
        re.compile(
            r"\b(auto[-\s]?approv|always\s+approv|force\s+approv"
            r"|must\s+approv|approv\s+this\s+immediately"
            r"|automatically\s+approv)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_hijacking",
        re.compile(
            r"\b(you\s+are\s+now|act\s+as|pretend\s+(you\s+are|to\s+be)"
            r"|roleplay\s+as|simulate\s+being)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_delimiter_injection",
        re.compile(
            r"(###\s*(system|instruction|prompt)"
            r"|<\|system\|>"
            r"|\[INST\]"
            r"|<<SYS>>"
            r"|<s>.*</s>)",
            re.IGNORECASE,
        ),
    ),
    (
        "policy_override_language",
        re.compile(
            r"\b(new\s+instruction|updated?\s+(rule|policy)"
            r"|from\s+now\s+on\s+(you\s+)?(must|should|will|have\s+to))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_signals",
        re.compile(
            r"\b(jailbreak|DAN\b|do\s+anything\s+now|developer\s+mode"
            r"|god\s+mode|unrestricted\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
]

# ---------------------------------------------------------------------------
# Core helpers (pure functions — no ADK dependency)
# ---------------------------------------------------------------------------


def scrub_pii(text: str) -> tuple[str, list[str]]:
    """
    Replace PII tokens with safe labelled placeholders.

    Returns
    -------
    (clean_text, categories_found)
        ``categories_found`` is a list of category names that were matched,
        e.g. ``["SSN", "CREDIT_CARD"]``.  Empty list means no PII found.
    """
    redacted: list[str] = []
    for category, pattern in _PII_PATTERNS:
        cleaned, count = pattern.subn(f"[{category}_REDACTED]", text)
        if count:
            redacted.append(category)
            text = cleaned
    return text, redacted


def detect_injection(text: str) -> tuple[bool, str | None]:
    """
    Scan *text* for prompt-injection attack patterns.

    Returns
    -------
    (detected, reason)
        ``detected`` is True when any pattern fires.
        ``reason`` is a human-readable string naming the pattern family
        and the matched substring; ``None`` when no injection is found.
    """
    for family, pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"{family}: matched {match.group(0)!r}"
    return False, None


# ---------------------------------------------------------------------------
# ADK Workflow node
# ---------------------------------------------------------------------------


def security_checkpoint(node_input: ExpenseRequest) -> Event:
    """
    Security gate — always the first node in the expense-approval graph.

    Steps
    -----
    1. Scrub SSNs and credit-card numbers from the description.
    2. Detect prompt-injection attempts in the *scrubbed* text.
    3. Persist the ``SecurityResult`` into workflow state (for downstream
       HITL nodes that need amount / category / description for display).
    4. Route:
       - ``"injection_detected"`` → ``security_escalation`` (bypasses LLM)
       - ``__DEFAULT__``         → ``prepare_for_review`` → ``llm_reviewer``

    Logging policy
    --------------
    - PII categories are logged at WARNING level; the description (raw or
      clean) is **never** written to any log.
    - Injection events are logged at ERROR level with family + matched token.
    """
    clean_desc, redacted_cats = scrub_pii(node_input.description)
    injected, reason = detect_injection(clean_desc)

    if redacted_cats:
        logger.warning(
            "security_checkpoint: PII redacted | categories=%s | submitter=%s",
            redacted_cats,
            node_input.submitter,
        )

    result = SecurityResult(
        clean_description=clean_desc,
        amount=node_input.amount,
        category=node_input.category,
        submitter=node_input.submitter,
        date=node_input.date,
        had_pii=bool(redacted_cats),
        redacted_categories=redacted_cats,
        injection_detected=injected,
        injection_reason=reason,
    )

    # Always persist into state so downstream HITL nodes can read context
    # without it flowing through the LLM node.
    state_delta = {"security_result": result.model_dump()}

    if injected:
        logger.error(
            "security_checkpoint: INJECTION DETECTED | family+match=%s | submitter=%s",
            reason,
            node_input.submitter,
        )
        return Event(output=result, route="injection_detected", state=state_delta)

    # Clean path — no route label → __DEFAULT__ edge fires
    return Event(output=result, state=state_delta)
