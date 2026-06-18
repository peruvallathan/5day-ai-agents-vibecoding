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

"""Pydantic schemas shared across all expense-approval workflow nodes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ExpenseRequest(BaseModel):
    """An expense claim submitted for approval — the graph's input_schema."""

    description: str
    amount: float
    category: str
    submitter: str = "unknown"
    date: str | None = None


class SecurityResult(BaseModel):
    """
    Output of the security_checkpoint node.

    ``clean_description`` has all PII tokens replaced with labelled
    placeholders.  The original description is never stored in this
    model or emitted to any log.
    """

    clean_description: str
    amount: float
    category: str
    submitter: str
    date: str | None

    # PII metadata
    had_pii: bool
    redacted_categories: list[str]  # e.g. ["SSN", "CREDIT_CARD"]

    # Injection metadata
    injection_detected: bool
    injection_reason: str | None = None


class LlmReviewOutput(BaseModel):
    """Structured recommendation produced by the llm_reviewer LlmAgent."""

    recommendation: Literal["APPROVE", "REJECT", "ESCALATE"]
    reasoning: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]


class HumanDecision(BaseModel):
    """Final decision recorded after a human reviewer acts."""

    decision: Literal["APPROVE", "REJECT"]
    reviewer_notes: str | None = None
    flagged_security_event: bool = False  # True on the injection-detected path
