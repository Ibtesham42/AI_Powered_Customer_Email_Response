"""Plain-dict serializers for API responses — keeps ORM objects out of the
JSON layer and the response shape consistent across routes.
"""

from backend.models.kb_document import KbDocument
from backend.models.mailbox import Mailbox
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


def mailbox_dict(mailbox: Mailbox) -> dict:
    """Serialize a Mailbox for an API response. Never includes the encrypted
    credential."""
    return {
        "id": mailbox.id,
        "company_id": mailbox.company_id,
        "email_address": mailbox.email_address,
        "provider": mailbox.provider,
        "imap_host": mailbox.imap_host,
        "smtp_host": mailbox.smtp_host,
        "status": mailbox.status,
        "last_polled_at": mailbox.last_polled_at,
    }


def kb_document_dict(document: KbDocument) -> dict:
    """Serialize a KbDocument for an API response."""
    return {
        "id": document.id,
        "filename": document.filename,
        "doc_type": document.doc_type,
        "status": document.status,
        "error": document.error,
        "created_at": document.created_at,
        "indexed_at": document.indexed_at,
    }
