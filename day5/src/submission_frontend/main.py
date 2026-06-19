# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0

"""
Manager Dashboard — FastAPI service for the Ambient Expense Agent.

Endpoints:
  GET  /              → Serves the glassmorphic manager dashboard HTML
  GET  /api/pending   → Queries Agent Runtime sessions for paused HITL events
  POST /api/action/{session_id} → Resumes a paused session with APPROVE/REJECT

Environment variables:
  GOOGLE_CLOUD_PROJECT  — GCP project ID
  AGENT_RUNTIME_ID      — Agent Runtime engine ID (from deployment_metadata.json)
  GOOGLE_CLOUD_REGION   — Defaults to us-west1
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import google.auth
import google.auth.transport.requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
AGENT_RUNTIME_ID = os.environ.get("AGENT_RUNTIME_ID", "YOUR_AGENT_RUNTIME_ID")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-west1")

AGENT_RUNTIME_BASE = (
    f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/"
    f"{PROJECT_ID}/locations/{REGION}/reasoningEngines/{AGENT_RUNTIME_ID}"
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Expense Manager Dashboard", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_auth_headers() -> dict[str, str]:
    """Get Google Cloud auth headers using Application Default Credentials."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ActionRequest(BaseModel):
    approved: bool
    interrupt_id: str
    notes: str | None = None


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/pending")
async def get_pending_approvals() -> list[dict[str, Any]]:
    """
    Query Agent Runtime sessions and identify paused HITL events.
    Returns sessions with unresolved adk_request_input events.
    """
    import httpx

    headers = _get_auth_headers()
    pending = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # List all sessions
            sessions_url = f"{AGENT_RUNTIME_BASE}/sessions"
            sessions_resp = await client.get(sessions_url, headers=headers)
            sessions_resp.raise_for_status()
            sessions_data = sessions_resp.json()
            sessions = sessions_data.get("sessions", [])

            for session in sessions:
                session_id = session.get("name", "").split("/")[-1]
                if not session_id:
                    continue

                # Get full session history
                history_url = f"{AGENT_RUNTIME_BASE}/sessions/{session_id}/events"
                history_resp = await client.get(history_url, headers=headers)
                if history_resp.status_code != 200:
                    continue

                events = history_resp.json().get("events", [])

                # Find unresolved adk_request_input events
                request_inputs = {}
                resolved_ids = set()

                for event in events:
                    content = event.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        fn_call = part.get("functionCall", {})
                        fn_resp = part.get("functionResponse", {})

                        if fn_call.get("name") == "adk_request_input":
                            interrupt_id = fn_call.get("id") or event.get("id")
                            args = fn_call.get("args", {})
                            request_inputs[interrupt_id] = {
                                "interrupt_id": interrupt_id,
                                "message": args.get("message", ""),
                                "session_id": session_id,
                            }

                        if fn_resp.get("name") == "adk_request_input":
                            resolved_ids.add(fn_resp.get("id"))

                # Only include unresolved
                for interrupt_id, data in request_inputs.items():
                    if interrupt_id not in resolved_ids:
                        # Parse expense details from the HITL message
                        msg = data["message"]
                        expense = _parse_expense_from_message(msg)
                        pending.append({
                            "session_id": session_id,
                            "interrupt_id": interrupt_id,
                            "expense": expense,
                            "message": msg,
                        })

    except Exception as e:
        logger.error("Error fetching pending approvals: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return pending


def _parse_expense_from_message(message: str) -> dict:
    """Extract expense details from the HITL RequestInput message string."""
    lines = message.split("\n")
    expense = {}
    for line in lines:
        if "Submitter" in line:
            expense["submitter"] = line.split(":")[-1].strip()
        elif "Amount" in line and "$" in line:
            try:
                expense["amount"] = float(line.split("$")[-1].strip())
            except ValueError:
                pass
        elif "Category" in line:
            expense["category"] = line.split(":")[-1].strip()
        elif "Description" in line:
            expense["description"] = line.split(":")[-1].strip()
        elif "Date" in line:
            expense["date"] = line.split(":")[-1].strip()
    return expense


@app.post("/api/action/{session_id}")
async def take_action(session_id: str, body: ActionRequest) -> dict:
    """
    Resume a paused Agent Runtime session with APPROVE or REJECT decision.
    """
    import httpx

    headers = _get_auth_headers()
    decision = "APPROVE" if body.approved else "REJECT"
    notes = f" {body.notes}" if body.notes else ""

    resume_payload = {
        "message": {
            "role": "user",
            "parts": [
                {
                    "functionResponse": {
                        "id": body.interrupt_id,
                        "name": "adk_request_input",
                        "response": {
                            "approved": body.approved,
                            "decision": decision,
                            "notes": body.notes,
                        }
                    }
                }
            ]
        },
        "userId": "default-user",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            query_url = f"{AGENT_RUNTIME_BASE}:query"
            payload = {
                "input": {
                    "session_id": session_id,
                    **resume_payload,
                }
            }
            resp = await client.post(query_url, headers=headers,
                                     content=json.dumps(payload))
            resp.raise_for_status()
            result = resp.json()

        logger.info("Action taken: session=%s decision=%s", session_id, decision)
        return {"status": "ok", "decision": decision, "response": result}

    except Exception as e:
        logger.error("Error resuming session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Serve the glassmorphic manager dashboard."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Expense Manager Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: rgba(255,255,255,0.05);
    --border: rgba(255,255,255,0.08);
    --accent: #4f8ef7;
    --accent2: #7c3aed;
    --green: #10b981;
    --red: #ef4444;
    --amber: #f59e0b;
    --text: #e2e8f0;
    --muted: #64748b;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }
  body::before {
    content: '';
    position: fixed; inset: 0; z-index: -1;
    background:
      radial-gradient(ellipse 800px 600px at 20% 20%, rgba(79,142,247,0.08) 0%, transparent 60%),
      radial-gradient(ellipse 600px 500px at 80% 80%, rgba(124,58,237,0.07) 0%, transparent 60%);
  }
  header {
    padding: 20px 40px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 14px;
    background: rgba(0,0,0,0.3);
    backdrop-filter: blur(12px);
    position: sticky; top: 0; z-index: 10;
  }
  .logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  header h1 { font-size: 18px; font-weight: 600; letter-spacing: -0.3px; }
  header span { font-size: 12px; color: var(--muted); margin-left: auto; }
  .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--green);
    animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }

  main { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
  .stats {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px;
  }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 20px; backdrop-filter: blur(10px);
  }
  .stat-card .label { font-size: 11px; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; }
  .stat-card .value { font-size: 28px; font-weight: 600; margin-top: 4px; }

  .section-title {
    font-size: 13px; font-weight: 500; color: var(--muted);
    letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 16px;
  }
  #cards-container { display: flex; flex-direction: column; gap: 14px; }

  .expense-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 24px; backdrop-filter: blur(10px);
    transition: border-color 0.2s, transform 0.2s;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
  .expense-card:hover { border-color: rgba(255,255,255,0.15); transform: translateY(-1px); }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
  .submitter { font-size: 15px; font-weight: 600; }
  .amount {
    font-size: 22px; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .card-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
  .badge {
    font-size: 11px; padding: 3px 10px; border-radius: 20px;
    background: rgba(255,255,255,0.06); border: 1px solid var(--border);
    color: var(--muted);
  }
  .badge.high { background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.3); color: #fca5a5; }
  .description { font-size: 13px; color: var(--muted); margin-bottom: 20px; line-height: 1.5; }
  .card-actions { display: flex; gap: 10px; }
  .btn {
    flex: 1; padding: 10px; border-radius: 10px; font-size: 13px; font-weight: 500;
    border: none; cursor: pointer; transition: all 0.2s; display: flex;
    align-items: center; justify-content: center; gap: 6px;
  }
  .btn-approve {
    background: linear-gradient(135deg, #065f46, #10b981);
    color: #ecfdf5; border: 1px solid rgba(16,185,129,0.3);
  }
  .btn-approve:hover { background: linear-gradient(135deg, #047857, #34d399); }
  .btn-reject {
    background: linear-gradient(135deg, #7f1d1d, #ef4444);
    color: #fef2f2; border: 1px solid rgba(239,68,68,0.3);
  }
  .btn-reject:hover { background: linear-gradient(135deg, #991b1b, #f87171); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .empty-state {
    text-align: center; padding: 80px 20px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; backdrop-filter: blur(10px);
  }
  .empty-state .icon { font-size: 48px; margin-bottom: 16px; }
  .empty-state h2 { font-size: 17px; font-weight: 500; margin-bottom: 6px; }
  .empty-state p { color: var(--muted); font-size: 13px; }

  /* Modal */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.7);
    backdrop-filter: blur(4px); z-index: 100; display: none;
    align-items: center; justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: #0f1117; border: 1px solid var(--border);
    border-radius: 20px; padding: 32px; max-width: 480px; width: 90%;
    animation: slideUp 0.25s ease;
  }
  @keyframes slideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:none} }
  .modal h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
  .modal .result { font-size: 13px; color: var(--muted); line-height: 1.7;
    background: rgba(255,255,255,0.03); border-radius: 10px; padding: 14px; }
  .modal-close {
    margin-top: 20px; width: 100%; padding: 10px; background: rgba(255,255,255,0.06);
    border: 1px solid var(--border); border-radius: 10px; color: var(--text);
    cursor: pointer; font-size: 13px; transition: background 0.2s;
  }
  .modal-close:hover { background: rgba(255,255,255,0.1); }
</style>
</head>
<body>
<header>
  <div class="logo">💸</div>
  <h1>Expense Manager Dashboard</h1>
  <div class="pulse"></div>
  <span id="last-refresh">Refreshing...</span>
</header>

<main>
  <div class="stats">
    <div class="stat-card">
      <div class="label">Pending Approvals</div>
      <div class="value" id="stat-pending" style="color:var(--amber)">—</div>
    </div>
    <div class="stat-card">
      <div class="label">Approved Today</div>
      <div class="value" id="stat-approved" style="color:var(--green)">—</div>
    </div>
    <div class="stat-card">
      <div class="label">Total Value Pending</div>
      <div class="value" id="stat-value" style="color:var(--accent)">—</div>
    </div>
  </div>

  <div class="section-title">Pending Approvals</div>
  <div id="cards-container"></div>
</main>

<div class="modal-overlay" id="modal">
  <div class="modal">
    <h2 id="modal-title">Agent Response</h2>
    <div class="result" id="modal-content"></div>
    <button class="modal-close" onclick="closeModal()">Close</button>
  </div>
</div>

<script>
let pendingData = [];
let approvedCount = 0;

async function fetchPending() {
  try {
    const resp = await fetch('/api/pending');
    const data = await resp.json();
    pendingData = data;
    renderCards(data);
    document.getElementById('stat-pending').textContent = data.length;
    const total = data.reduce((s, d) => s + (d.expense?.amount || 0), 0);
    document.getElementById('stat-value').textContent =
      '$' + total.toLocaleString('en-US', {minimumFractionDigits: 2});
    document.getElementById('stat-approved').textContent = approvedCount;
    document.getElementById('last-refresh').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch(e) {
    console.error('Failed to fetch pending:', e);
  }
}

function renderCards(items) {
  const container = document.getElementById('cards-container');
  if (!items.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="icon">✅</div>
        <h2>All caught up!</h2>
        <p>No expenses are currently pending manager approval.</p>
      </div>`;
    return;
  }
  container.innerHTML = items.map((item, i) => {
    const e = item.expense || {};
    const amount = e.amount || 0;
    const isHigh = amount >= 500;
    return `
    <div class="expense-card" id="card-${i}">
      <div class="card-header">
        <div class="submitter">${e.submitter || 'Unknown'}</div>
        <div class="amount">$${parseFloat(amount).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
      </div>
      <div class="card-meta">
        <span class="badge">${e.category || 'general'}</span>
        ${e.date ? `<span class="badge">${e.date}</span>` : ''}
        ${isHigh ? '<span class="badge high">⚠ High Value</span>' : ''}
        <span class="badge">Session: ${item.session_id.slice(-8)}</span>
      </div>
      <div class="description">${e.description || 'No description provided.'}</div>
      <div class="card-actions">
        <button class="btn btn-approve" onclick="takeAction(${i}, true)">
          ✅ Approve
        </button>
        <button class="btn btn-reject" onclick="takeAction(${i}, false)">
          ❌ Reject
        </button>
      </div>
    </div>`;
  }).join('');
}

async function takeAction(index, approved) {
  const item = pendingData[index];
  const card = document.getElementById(`card-${index}`);
  const buttons = card.querySelectorAll('.btn');
  buttons.forEach(b => {
    b.disabled = true;
    b.innerHTML = '<div class="spinner"></div>';
  });

  try {
    const resp = await fetch(`/api/action/${item.session_id}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        approved,
        interrupt_id: item.interrupt_id,
      }),
    });
    const result = await resp.json();

    if (approved) approvedCount++;
    card.style.opacity = '0.3';
    card.style.pointerEvents = 'none';

    showModal(
      approved ? '✅ Expense Approved' : '❌ Expense Rejected',
      JSON.stringify(result.response || result, null, 2)
    );

    setTimeout(() => {
      card.remove();
      fetchPending();
    }, 800);

  } catch(e) {
    buttons.forEach(b => { b.disabled = false; });
    alert('Action failed: ' + e.message);
  }
}

function showModal(title, content) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-content').textContent = content;
  document.getElementById('modal').classList.add('open');
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
}

// Poll every 5 seconds
fetchPending();
setInterval(fetchPending, 5000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
