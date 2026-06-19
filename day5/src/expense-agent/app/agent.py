# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0

"""
Ambient Expense Agent — ADK 2.0 Graph Workflow
===============================================

Graph topology:
  START (input_schema=ExpenseRequest)
        │
        ▼
  auto_approve       ← Instantly approves expenses < $100
        │
        └── amount >= $100
                  │
                  ▼
          review_agent   ← LLM risk analysis + HITL pause (RequestInput)
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
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ExpenseRequest(BaseModel):
    """Input schema for an expense claim submitted for approval."""
    amount: float
    submitter: str = "unknown"
    category: str = "general"
    description: str = ""
    date: str | None = None


class ReviewOutput(BaseModel):
    """Structured output from the LLM reviewer."""
    recommendation: Literal["APPROVE", "REJECT", "ESCALATE"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reasoning: str


# ---------------------------------------------------------------------------
# Node: auto_approve
# Instantly approves expenses under $100, routes larger ones to review_agent
# ---------------------------------------------------------------------------

@node
def auto_approve(node_input: ExpenseRequest) -> Event:
    """Auto-approve standard claims under $100; route larger ones for review."""
    if node_input.amount < 100:
        logger.info(
            "auto_approve: APPROVED | amount=%.2f | submitter=%s",
            node_input.amount,
            node_input.submitter,
        )
        return Event(
            output={"status": "approved", "amount": node_input.amount,
                    "submitter": node_input.submitter},
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text=f"✅ Expense of ${node_input.amount:.2f} "
                         f"by {node_input.submitter} automatically approved "
                         f"(standard claim under $100)."
                )],
            ),
        )
    # Route to human review for amounts >= $100
    return Event(
        output=node_input.model_dump(),
        route="needs_review",
        state={"expense": node_input.model_dump()},
    )


# ---------------------------------------------------------------------------
# Node: review_agent (LlmAgent + HITL)
# ---------------------------------------------------------------------------

_review_llm = LlmAgent(
    name="llm_risk_analyser",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a corporate expense policy reviewer. "
        "Evaluate the submitted expense and respond ONLY with a JSON object "
        "matching the required schema.\n\n"
        "Policy:\n"
        "- amount > $500 or unusual category → risk_level HIGH\n"
        "- $100–$500 → MEDIUM; below $100 → LOW\n"
        "- Standard categories (meals, travel, software, office) are routine\n"
        "- Recommend ESCALATE when genuinely uncertain\n"
        "Respond ONLY with the JSON schema — no prose outside the object."
    ),
    output_schema=ReviewOutput,
    output_key="llm_review",
)


@node(rerun_on_resume=True)
async def review_agent(ctx: Context, node_input: ExpenseRequest) -> Event:
    """LLM risk analysis followed by HITL pause for manager decision."""

    if "manager_decision" not in ctx.resume_inputs:
        # First call — run LLM analysis then pause for human
        expense = ctx.state.get("expense", node_input.model_dump())
        date_line = f"\nDate      : {expense.get('date')}" if expense.get("date") else ""

        yield RequestInput(
            interrupt_id="manager_decision",
            message=(
                f"╔══════════════════════════════════════╗\n"
                f"║       EXPENSE APPROVAL REQUIRED      ║\n"
                f"╚══════════════════════════════════════╝\n"
                f"Submitter : {expense.get('submitter', 'unknown')}"
                f"{date_line}\n"
                f"Amount    : ${expense.get('amount', 0):.2f}\n"
                f"Category  : {expense.get('category', 'unknown')}\n"
                f"Description: {expense.get('description', '')}\n\n"
                f"⚠️  This expense exceeds the $100 auto-approval threshold.\n\n"
                f"Enter APPROVE or REJECT (optionally followed by notes):"
            ),
        )
        return

    # Resumed — process manager decision
    raw: str = ctx.resume_inputs["manager_decision"]
    upper = raw.strip().upper()
    decision: Literal["APPROVE", "REJECT"] = (
        "APPROVE" if upper.startswith("APPROVE") else "REJECT"
    )
    notes = raw.strip()[len(decision):].strip() or None

    logger.info(
        "review_agent: decision=%s | submitter=%s",
        decision,
        ctx.state.get("expense", {}).get("submitter"),
    )

    yield Event(
        output={"decision": decision, "reviewer_notes": notes},
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(
                text=(
                    f"{'✅' if decision == 'APPROVE' else '❌'} "
                    f"Expense **{decision}** by manager."
                    + (f"\nNotes: {notes}" if notes else "")
                )
            )],
        ),
    )


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

root_agent = Workflow(
    name="expense_approval_workflow",
    description=(
        "Ambient expense approval workflow — auto-approves claims under $100 "
        "and routes larger expenses to LLM risk analysis + human-in-the-loop."
    ),
    input_schema=ExpenseRequest,
    edges=[
        ("START", auto_approve),
        (auto_approve, {"needs_review": review_agent}),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
