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
Ambient expense-approval service.

Accepts Pub/Sub push messages, decodes the expense payload, and drives
the ADK expense-approval workflow.  Human reviewers complete the HITL
nodes by POSTing to /resume/{session_id}.

Endpoints
---------
POST /pubsub               Pub/Sub push webhook — new expense event
POST /resume/{session_id}  Submit APPROVE/REJECT to resume a paused HITL session
GET  /health               Liveness probe
"""

import base64
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow.utils._workflow_hitl_utils import (
    REQUEST_INPUT_FUNCTION_CALL_NAME,
    get_request_input_interrupt_ids,
)
from google.genai import types
from pydantic import BaseModel

from app.agent import app as adk_app
from app.app_utils.telemetry import setup_telemetry

# ---------------------------------------------------------------------------
# Logging — standard Python logging to console; no Cloud Logging client.
# otel_to_cloud=False: setup_telemetry() only activates cloud OTEL export
# when LOGS_BUCKET_NAME is set, which is never the case locally.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ADK app name comes from agent.py: App(name="app", ...)
APP_NAME: str = adk_app.name

_session_svc = InMemorySessionService()
_runner: Runner | None = None

# Tracks user_id and pending interrupt IDs per session.
# Lost on restart — intentional for a local ambient service.
_session_state: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Lifespan — build Runner once at startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    global _runner
    setup_telemetry()  # no-op locally when LOGS_BUCKET_NAME is unset
    _runner = Runner(
        app=adk_app,
        session_service=_session_svc,
        # auto_create_session=False (default): we create sessions explicitly
        # so the session_id can be derived from the Pub/Sub messageId.
    )
    logger.info("Ambient expense-approval service started (app_name=%s)", APP_NAME)
    yield
    logger.info("Service shutting down.")


app = FastAPI(
    title="ambient-expense-agent",
    description="Ambient expense-approval service — event-driven via Pub/Sub",
    lifespan=_lifespan,
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class _PubSubMessage(BaseModel):
    data: str  # base64-encoded JSON matching ExpenseRequest
    messageId: str = ""
    publishTime: str = ""
    attributes: dict[str, str] = {}


class PubSubPushPayload(BaseModel):
    message: _PubSubMessage
    # Pub/Sub sends the fully-qualified path:
    # "projects/{project}/subscriptions/{name}"
    subscription: str


class ResumeRequest(BaseModel):
    decision: str  # "APPROVE [notes]" or "REJECT [notes]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_subscription(sub: str) -> str:
    """Return the short subscription name from a fully-qualified path.

    "projects/my-proj/subscriptions/expense-sub" → "expense-sub"
    """
    return sub.rsplit("/", 1)[-1]


def _build_resume_content(interrupt_id: str, decision: str) -> types.Content:
    """Build the FunctionResponse Content that resumes a suspended HITL node.

    ADK's rehydration layer calls _unwrap_response on the dict, extracting
    the "result" key so ctx.resume_inputs[interrupt_id] receives the plain
    string that human_review / security_escalation expect.
    """
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=interrupt_id,
                    name=REQUEST_INPUT_FUNCTION_CALL_NAME,
                    response={"result": decision},
                )
            )
        ],
    )


async def _run_and_collect(
    user_id: str,
    session_id: str,
    message: types.Content,
) -> list[str]:
    """Drive the workflow to the next pause or completion.

    Returns the interrupt_ids of any pending HITL nodes, empty list when
    the workflow finished.
    """
    assert _runner is not None, "Runner not initialised — service not started"
    interrupt_ids: list[str] = []
    try:
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        logger.info("agent: %s", part.text[:200])
            interrupt_ids.extend(get_request_input_interrupt_ids(event))
            if event.error_code:
                logger.error(
                    "workflow error | session=%s code=%s msg=%s",
                    session_id,
                    event.error_code,
                    event.error_message,
                )
    except Exception:
        logger.exception("run_async failed | session=%s", session_id)
        raise
    return interrupt_ids


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pubsub", status_code=202)
async def receive_pubsub(payload: PubSubPushPayload) -> dict[str, Any]:
    """Decode a Pub/Sub push message and start the expense-approval workflow.

    The subscription path is normalised to a short name and used as the ADK
    user_id so session records remain readable
    (e.g. "expense-subscription" instead of
    "projects/my-project/subscriptions/expense-subscription").

    Returns the session_id and interrupt_ids so a reviewer knows where to
    POST their decision.
    """
    short_sub = _normalize_subscription(payload.subscription)

    try:
        raw_json = base64.b64decode(payload.message.data).decode()
        expense_dict = json.loads(raw_json)
    except Exception as exc:
        logger.error("pubsub: decode error | sub=%s | %s", short_sub, exc)
        raise HTTPException(status_code=400, detail=f"Bad message data: {exc}") from exc

    # Use the Pub/Sub messageId as the session_id for traceability.
    session_id = payload.message.messageId or str(uuid.uuid4())

    logger.info(
        "pubsub: new expense | sub=%s session=%s amount=%s submitter=%s",
        short_sub,
        session_id,
        expense_dict.get("amount"),
        expense_dict.get("submitter"),
    )

    await _session_svc.create_session(
        app_name=APP_NAME,
        user_id=short_sub,
        session_id=session_id,
    )

    interrupt_ids = await _run_and_collect(
        user_id=short_sub,
        session_id=session_id,
        message=types.Content(
            role="user",
            parts=[types.Part.from_text(text=raw_json)],
        ),
    )

    status = "awaiting_review" if interrupt_ids else "completed"
    _session_state[session_id] = {
        "user_id": short_sub,
        "interrupt_ids": interrupt_ids,
    }

    logger.info(
        "pubsub: workflow %s | session=%s interrupts=%s",
        status,
        session_id,
        interrupt_ids,
    )
    return {
        "session_id": session_id,
        "user_id": short_sub,
        "status": status,
        "interrupt_ids": interrupt_ids,
    }


@app.post("/resume/{session_id}")
async def resume_hitl(session_id: str, body: ResumeRequest) -> dict[str, Any]:
    """Submit a human decision to resume a paused HITL workflow session.

    The decision string is forwarded to the suspended HITL node
    (human_review or security_escalation) as ctx.resume_inputs[interrupt_id].
    The node parses the leading word — APPROVE or REJECT — and stores optional
    trailing text as reviewer_notes.
    """
    state = _session_state.get(session_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Session {session_id!r} not found"
        )

    interrupt_ids = state.get("interrupt_ids", [])
    if not interrupt_ids:
        raise HTTPException(
            status_code=409, detail="Session has no pending interrupts"
        )

    user_id: str = state["user_id"]
    interrupt_id: str = interrupt_ids[0]

    logger.info(
        "resume: session=%s interrupt=%s decision=%r",
        session_id,
        interrupt_id,
        body.decision[:60],
    )

    remaining = await _run_and_collect(
        user_id=user_id,
        session_id=session_id,
        message=_build_resume_content(interrupt_id, body.decision),
    )

    status = "awaiting_review" if remaining else "completed"
    _session_state[session_id] = {"user_id": user_id, "interrupt_ids": remaining}

    logger.info("resume: workflow %s | session=%s", status, session_id)
    return {
        "session_id": session_id,
        "status": status,
        "interrupt_ids": remaining,
    }


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
