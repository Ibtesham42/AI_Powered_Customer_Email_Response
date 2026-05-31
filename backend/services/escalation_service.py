"""Escalation engine — decides when a Ticket needs a human rather than the AI
auto-reply path, and flags it.

Rules, evaluated against a fresh AI draft in priority order (first match wins):

  needs_human       the model deferred (unsure, or the customer asked for a human)
  complaint         the detected intent is a complaint
  repeated_replies  the thread already has ESCALATION_MAX_REPLIES replies out
                    (the AI's answers aren't resolving it)
  low_confidence    confidence below ESCALATION_CONFIDENCE_THRESHOLD

Manual reject is the fifth rule and lives at the route layer
(``/messages/{id}/reject`` -> ``escalate_ticket(reason="agent_rejected")``).
An escalated Ticket leaves the auto-AI review queue (see CONTEXT.md).
"""

import logging

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.enums import Intent
from backend.models.ticket import Ticket
from backend.services import ticket_service

logger = logging.getLogger(__name__)


def evaluate(db: Session, ticket: Ticket, result: dict) -> str | None:
    """Return the escalation reason for a fresh draft, or None to leave it in
    the normal review queue. First matching rule wins."""
    if result.get("needs_human"):
        return "needs_human"
    if result.get("intent") == Intent.COMPLAINT.value:
        return "complaint"
    if (
        ticket_service.count_outbound_messages(db, ticket.company_id, ticket.id)
        >= settings.ESCALATION_MAX_REPLIES
    ):
        return "repeated_replies"
    if (result.get("confidence") or 0) < settings.ESCALATION_CONFIDENCE_THRESHOLD:
        return "low_confidence"
    return None


def apply_draft_escalation(db: Session, ticket: Ticket, result: dict) -> str | None:
    """Evaluate the rules for a fresh draft and escalate the Ticket if any
    fires. Returns the reason applied, or None. No-op (and keeps the existing
    reason) if the Ticket is already escalated."""
    if ticket.escalated:
        return ticket.escalation_reason
    reason = evaluate(db, ticket, result)
    if reason:
        ticket_service.escalate_ticket(db, ticket, reason)
        logger.info("Ticket %s escalated (%s)", ticket.id, reason)
    return reason
