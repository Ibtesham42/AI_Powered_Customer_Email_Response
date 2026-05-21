"""Plain-dict serializers for API responses — keeps ORM objects out of the
JSON layer and the response shape consistent across routes.
"""

from backend.models.message import Message
from backend.models.ticket import Ticket


def ticket_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "thread_id": ticket.thread_id,
        "status": ticket.status,
        "escalated": ticket.escalated,
        "escalation_reason": ticket.escalation_reason,
        "intent": ticket.intent,
        "customer_id": ticket.customer_id,
        "assigned_to": ticket.assigned_to,
    }


def message_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "direction": message.direction,
        "subject": message.subject,
        "body": message.body,
        "sender_email": message.sender_email,
        "recipient_email": message.recipient_email,
        "review_status": message.review_status,
        "intent": message.intent,
        "confidence": message.confidence,
        "ai_draft": message.ai_draft,
        "final_reply": message.final_reply,
    }
