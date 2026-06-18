# ruff: noqa
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
Expense-approval workflow — ADK 2.0 graph API.

Graph topology
--------------

  START (input_schema=ExpenseRequest)
        │
        ▼
  security_checkpoint          ← PII scrub + injection detect
        │
        ├── route="injection_detected"
        │         │
        │         ▼
        │   security_escalation   ← HITL, bypasses LLM, flags security event
        │
        └── route=__DEFAULT__  (clean path)
                  │
                  ▼
          prepare_for_review   ← formats SecurityResult → readable string for LLM
                  │
                  ▼
           llm_reviewer        ← LlmAgent, output_schema=LlmReviewOutput
                  │
                  ▼
           human_review        ← HITL, shows LLM recommendation, collects decision
"""

from __future__ import annotations

import logging
from typing import Literal

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.models import Gemini
from google.adk.workflow import Workflow, node
from google.genai import types

from .models import ExpenseRequest, HumanDecision, LlmReviewOutput, SecurityResult
from .security import security_checkpoint

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node: prepare_for_review
# Translates SecurityResult → a clean, human-readable prompt string so the
# LlmAgent receives plain text rather than a raw Pydantic dict.
# ---------------------------------------------------------------------------


def prepare_for_review(node_input: SecurityResult) -> str:
    """Format the scrubbed expense as a plain-text review prompt for the LLM."""
    pii_note = (
        f"\n⚠️  Note: PII was redacted from the description "
        f"(categories: {', '.join(node_input.redacted_categories)})."
        if node_input.had_pii
        else ""
    )
    date_line = f"\nDate      : {node_input.date}" if node_input.date else ""
    return (
        f"Please review this expense claim:\n"
        f"Submitter : {node_input.submitter}"
        f"{date_line}\n"
        f"Amount    : ${node_input.amount:.2f}\n"
        f"Category  : {node_input.category}\n"
        f"Description: {node_input.clean_description}"
        f"{pii_note}"
    )


# ---------------------------------------------------------------------------
# Node: llm_reviewer  (LlmAgent — structured output)
# ---------------------------------------------------------------------------

llm_reviewer = LlmAgent(
    name="llm_reviewer",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a corporate expense-policy reviewer. "
        "Evaluate the expense claim provided and respond with a JSON object "
        "that matches the required schema exactly.\n\n"
        "Policy guidelines:\n"
        "- Amount > $500 OR unusual category → risk_level HIGH\n"
        "- Amount $100–$500 → risk_level MEDIUM; below $100 → LOW\n"
        "- Common categories (meals, travel, software, office) are standard\n"
        "- Recommend ESCALATE when genuinely uncertain\n"
        "- If PII was redacted, note it in reasoning but do not guess the values\n\n"
        "Respond ONLY with the JSON schema — no prose outside the JSON object."
    ),
    output_schema=LlmReviewOutput,
    output_key="llm_review",
)


# ---------------------------------------------------------------------------
# Node: human_review  (HITL — normal approval path)
# Receives the LLM recommendation and asks a human for the final decision.
# ---------------------------------------------------------------------------


@node(rerun_on_resume=True)
async def human_review(ctx: Context, node_input: LlmReviewOutput) -> Event:  # type: ignore[override]
    """
    Present the LLM recommendation to a human reviewer and collect APPROVE/REJECT.

    Uses ``rerun_on_resume=True`` so the node can inspect ``ctx.resume_inputs``
    on re-entry and build a typed ``HumanDecision`` output.
    """
    if "human_decision" not in ctx.resume_inputs:
        # First call — suspend and ask for input
        sec: dict = ctx.state.get("security_result", {})
        pii_note = (
            f"\n⚠️  PII was redacted from the description "
            f"(categories: {sec.get('redacted_categories', [])})."
            if sec.get("had_pii")
            else ""
        )
        date_line = f"\nDate      : {sec.get('date')}" if sec.get("date") else ""
        yield RequestInput(
            interrupt_id="human_decision",
            message=(
                f"╔══════════════════════════════════════╗\n"
                f"║        EXPENSE REVIEW REQUEST        ║\n"
                f"╚══════════════════════════════════════╝\n"
                f"Submitter : {sec.get('submitter', 'unknown')}"
                f"{date_line}\n"
                f"Amount    : ${sec.get('amount', 0):.2f}\n"
                f"Category  : {sec.get('category', 'unknown')}\n"
                f"Description: {sec.get('clean_description', '')}"
                f"{pii_note}\n\n"
                f"🤖 LLM Recommendation : {node_input.recommendation}"
                f" (risk: {node_input.risk_level})\n"
                f"   Reasoning          : {node_input.reasoning}\n\n"
                f"Enter your decision — type APPROVE or REJECT "
                f"(optionally followed by notes, e.g. 'APPROVE looks fine'):"
            ),
        )
        return

    # Resumed — process the human's response
    raw: str = ctx.resume_inputs["human_decision"]
    upper = raw.strip().upper()
    decision: Literal["APPROVE", "REJECT"] = (
        "APPROVE" if upper.startswith("APPROVE") else "REJECT"
    )
    notes_raw = raw.strip()[len(decision):].strip()
    notes: str | None = notes_raw if notes_raw else None

    logger.info(
        "human_review: decision=%s | submitter=%s | risk=%s",
        decision,
        ctx.state.get("security_result", {}).get("submitter"),
        node_input.risk_level,
    )

    result = HumanDecision(decision=decision, reviewer_notes=notes)
    yield Event(
        output=result.model_dump(),
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=(
                        f"✅ Decision recorded: **{decision}**"
                        + (f"\nNotes: {notes}" if notes else "")
                    )
                )
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Node: security_escalation  (HITL — injection-detected path)
# The LLM is bypassed entirely.  A human decides and the event is flagged.
# ---------------------------------------------------------------------------


@node(rerun_on_resume=True)
async def security_escalation(ctx: Context, node_input: SecurityResult) -> Event:  # type: ignore[override]
    """
    Handle expenses that triggered the injection detector.

    The expense description (clean) is shown to a human alongside the
    security alert.  The LLM is never invoked.  The final ``HumanDecision``
    has ``flagged_security_event=True`` for the audit trail.
    """
    if "security_decision" not in ctx.resume_inputs:
        date_line = f"\nDate      : {node_input.date}" if node_input.date else ""
        pii_note = (
            f"\n⚠️  PII also redacted: {node_input.redacted_categories}"
            if node_input.had_pii
            else ""
        )
        yield RequestInput(
            interrupt_id="security_decision",
            message=(
                f"🚨🚨🚨 SECURITY ALERT — PROMPT INJECTION DETECTED 🚨🚨🚨\n"
                f"This expense was NOT sent to the LLM.\n\n"
                f"Submitter : {node_input.submitter}"
                f"{date_line}\n"
                f"Amount    : ${node_input.amount:.2f}\n"
                f"Category  : {node_input.category}"
                f"{pii_note}\n"
                f"Injection : {node_input.injection_reason}\n\n"
                f"Scrubbed description (for reference only):\n"
                f"  {node_input.clean_description}\n\n"
                f"Enter APPROVE or REJECT "
                f"(optionally followed by notes):"
            ),
        )
        return

    # Resumed
    raw: str = ctx.resume_inputs["security_decision"]
    upper = raw.strip().upper()
    decision: Literal["APPROVE", "REJECT"] = (
        "APPROVE" if upper.startswith("APPROVE") else "REJECT"
    )
    notes_raw = raw.strip()[len(decision):].strip()
    notes: str | None = notes_raw if notes_raw else None

    logger.error(
        "security_escalation: SECURITY EVENT CLOSED | decision=%s | submitter=%s | reason=%s",
        decision,
        node_input.submitter,
        node_input.injection_reason,
    )

    result = HumanDecision(
        decision=decision,
        reviewer_notes=notes,
        flagged_security_event=True,
    )
    yield Event(
        output=result.model_dump(),
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=(
                        f"🚨 Security event closed: **{decision}** — "
                        f"flagged in audit log."
                        + (f"\nNotes: {notes}" if notes else "")
                    )
                )
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

root_agent = Workflow(
    name="expense_approval_workflow",
    description=(
        "Expense approval workflow with security checkpoint (PII scrubbing + "
        "prompt-injection detection), LLM policy review, and human-in-the-loop "
        "final decision."
    ),
    input_schema=ExpenseRequest,
    edges=[
        # ── Gate ──────────────────────────────────────────────────────────
        ("START", security_checkpoint),
        # ── Conditional routing via RoutingMap dict ───────────────────────
        # (source, {route_value: target, ...}) is the real ADK 2.0 API.
        # "__DEFAULT__" fires when security_checkpoint emits no route (clean).
        # "injection_detected" fires when Event(route="injection_detected").
        (
            security_checkpoint,
            {
                "injection_detected": security_escalation,  # bypass LLM
                "__DEFAULT__": prepare_for_review,          # clean path
            },
        ),
        # ── Clean path continues ──────────────────────────────────────────
        (prepare_for_review, llm_reviewer),
        (llm_reviewer, human_review),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
