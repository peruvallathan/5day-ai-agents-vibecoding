# STRIDE Threat Model Assessment: Shopping Assistant Agent

This document outlines the security posture of the `shopping-assistant` agent codebase and architecture based on the STRIDE threat modeling framework.

---

## 1. System Boundaries & Entry Points

*   **Entry Points**:
    *   **FASTAPI Server Endpoint (`/run_sse`)**: Exposes the LLM conversation stream to clients.
    *   **FASTAPI Session Management (`/apps/app/users/{user_id}/sessions`)**: Allows managing conversation state.
    *   **FASTAPI Feedback Endpoint (`/feedback`)**: Accepts post-interaction feedback.
*   **Logical Components**:
    *   **Root Agent (`shopping_assistant`)**: Orchestrates conversation flow using Gemini Flash.
    *   **Discount Redemption Tool (`redeem_discount`)**: Handles verifying and marking codes as used.
*   **Data Storage**:
    *   **`DISCOUNT_CODES` (In-Memory Dictionary)**: Stores discount validity and ownership mappings globally within the app server process memory.
    *   **Session State (In-Memory)**: Non-persistent conversation histories.

---

## 2. STRIDE Evaluation

### 👤 Spoofing (Identity Spoofing)
*   **Risk**: The `redeem_discount` tool accepts `user_id` as an LLM-provided parameter. An attacker can instruct the LLM to redeem a discount on behalf of a different user ID (e.g., *"Redeem code SUMMER20 for user 'admin'"*). Since the agent uses Automatic Function Calling (AFC), it will pass the attacker-supplied `user_id` to the tool without verifying the caller's authentic identity.
*   **Severity**: **High**
*   **Remediation**: Retrieve the authenticated user identity directly from the application context or token rather than letting the LLM supply the user identity as a mutable tool argument.

### ✍️ Tampering (Data Tampering)
*   **Risk**: The tool inputs (`user_id` and `code`) are not validated against strict patterns or schemas (e.g., length restrictions, character allowlists).
*   **Risk**: `DISCOUNT_CODES` is a mutable global dictionary. While scoped to the process, concurrency issues or state pollution could lead to incorrect discount allocations.
*   **Severity**: **Medium**
*   **Remediation**: Use Pydantic models to validate all tool parameters (enforcing strict patterns on `user_id` and `code` formats).

### 📜 Repudiation (Audit Trail Lack)
*   **Risk**: Although the FastAPI app logs user feedback, it does **not** log critical transactions like discount code redemptions to an audit log. If a dispute or malicious draining of codes occurs, there is no tamper-proof record (such as Cloud Logging / BigQuery) showing when, how, and by whom a code was redeemed.
*   **Severity**: **Medium**
*   **Remediation**: Integrate structured audit logging inside the `redeem_discount` tool to record every transaction event.

### 🔓 Information Disclosure (Data Leakage)
*   **Risk**: In-memory session logging or verbose exception tracebacks during FastAPI error states could leak internal details, stack traces, or configuration info (such as model attributes) to users.
*   **Severity**: **Medium**
*   **Remediation**: Implement a generic error handler in FastAPI to return sanitised messages to the client while logging verbose traces only to secure server-side logging.

### 🚫 Denial of Service (Availability Loss)
*   **Risk**: The API endpoints (`/run_sse`, `/feedback`) lack rate-limiting. A malicious client could send spam queries to consume LLM tokens or overwhelm the single-threaded in-memory session manager, leading to high cost and Denial of Service.
*   **Severity**: **Medium**
*   **Remediation**: Configure rate-limiting middleware (e.g., Slowapi) and define LLM generation limits (max output tokens).

### 🔑 Elevation of Privilege (Access Control Bypass)
*   **Risk**: The FastAPI server exposes session creation and execution endpoints without any authentication middleware. Any caller on the network can create sessions for arbitrary user IDs and invoke tools (such as redeeming discounts).
*   **Severity**: **High**
*   **Remediation**: Implement JWT or OAuth2 bearer token authentication to restrict access to endpoints and tie active sessions strictly to authenticated identity.
