"""Integration test for the Ambient Expense Agent workflow."""
import pytest
from app.agent import auto_approve, ExpenseRequest


def test_auto_approve_under_100():
    """Expenses under $100 should be auto-approved without HITL."""
    req = ExpenseRequest(amount=45.0, submitter="user@test.com",
                         category="meals", description="Lunch")
    event = auto_approve(req)
    assert event.output["status"] == "approved"
    assert event.output["amount"] == 45.0


def test_routes_to_review_at_100():
    """Expenses of exactly $100 should route to review_agent."""
    req = ExpenseRequest(amount=100.0, submitter="user@test.com",
                         category="travel", description="Taxi")
    event = auto_approve(req)
    assert event.route == "needs_review"


def test_routes_to_review_above_100():
    """Expenses above $100 should route to review_agent."""
    req = ExpenseRequest(amount=250.0, submitter="alice@test.com",
                         category="travel", description="Flight")
    event = auto_approve(req)
    assert event.route == "needs_review"
    assert event.state["expense"]["amount"] == 250.0
