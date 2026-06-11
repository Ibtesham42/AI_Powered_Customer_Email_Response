"""Escalation engine: rule priority, thresholds, and idempotency."""

import pytest

import backend.services.escalation_service as esc
from backend.config import settings
from backend.models.enums import Intent


class FakeTicket:
    def __init__(self, escalated=False, reason=None):
        self.escalated = escalated
        self.escalation_reason = reason
        self.company_id = 1
        self.id = 9


@pytest.fixture
def patched(monkeypatch):
    """Control the outbound-reply count and capture escalate calls."""
    state = {"outbound": 0, "escalated_reason": None}

    monkeypatch.setattr(
        esc.ticket_service,
        "count_outbound_messages",
        lambda db, c, t: state["outbound"],
    )

    def fake_escalate(db, ticket, reason):
        ticket.escalated = True
        ticket.escalation_reason = reason
        state["escalated_reason"] = reason

    monkeypatch.setattr(esc.ticket_service, "escalate_ticket", fake_escalate)
    return state


GOOD = {"needs_human": False, "intent": Intent.GENERAL_SUPPORT.value, "confidence": 90}


def test_needs_human_wins_first(patched):
    assert (
        esc.evaluate(None, FakeTicket(), {**GOOD, "needs_human": True}) == "needs_human"
    )


def test_complaint(patched):
    result = {**GOOD, "intent": Intent.COMPLAINT.value}
    assert esc.evaluate(None, FakeTicket(), result) == "complaint"


def test_repeated_replies(patched):
    patched["outbound"] = settings.ESCALATION_MAX_REPLIES
    assert esc.evaluate(None, FakeTicket(), GOOD) == "repeated_replies"


def test_low_confidence_boundary(patched):
    threshold = settings.ESCALATION_CONFIDENCE_THRESHOLD
    assert (
        esc.evaluate(None, FakeTicket(), {**GOOD, "confidence": threshold - 1})
        == "low_confidence"
    )
    # Exactly at the threshold is not below it — no escalation.
    assert esc.evaluate(None, FakeTicket(), {**GOOD, "confidence": threshold}) is None


def test_priority_needs_human_over_complaint(patched):
    result = {"needs_human": True, "intent": Intent.COMPLAINT.value, "confidence": 0}
    assert esc.evaluate(None, FakeTicket(), result) == "needs_human"


def test_apply_escalates_and_is_idempotent(patched):
    ticket = FakeTicket()
    reason = esc.apply_draft_escalation(None, ticket, {**GOOD, "confidence": 5})
    assert reason == "low_confidence"
    assert ticket.escalated is True

    # Already escalated: no-op, keeps the original reason.
    patched["escalated_reason"] = None
    already = FakeTicket(escalated=True, reason="agent_rejected")
    assert (
        esc.apply_draft_escalation(None, already, {**GOOD, "confidence": 0})
        == "agent_rejected"
    )
    assert patched["escalated_reason"] is None  # escalate_ticket not called
