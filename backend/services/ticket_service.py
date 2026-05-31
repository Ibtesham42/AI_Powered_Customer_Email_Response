"""Tenant-scoped domain operations for Customers, Tickets and Messages.

Every function takes a ``company_id`` and scopes all queries by it — tenant
isolation is enforced here, not in route handlers. Status changes go through
the state machine.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.logging_config import get_logger
from backend.models.customer import Customer
from backend.models.enums import MessageDirection, ReviewStatus, TicketStatus
from backend.models.message import Message
from backend.models.ticket import Ticket
from backend.services.state_machine import (
    assert_review_transition,
    assert_ticket_transition,
)

logger = get_logger(__name__)


# ---------------- Customers ----------------
def get_or_create_customer(
    db: Session, company_id: int, email: str, name: str | None = None
) -> Customer:
    """Return the Company's Customer for this email, creating it if absent."""
    customer = (
        db.query(Customer)
        .filter(Customer.company_id == company_id, Customer.email == email)
        .first()
    )
    if customer is None:
        customer = Customer(company_id=company_id, email=email, name=name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
    return customer


def get_customer(db: Session, company_id: int, customer_id: int) -> Customer | None:
    return (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == company_id)
        .first()
    )


# ---------------- Tickets ----------------
def get_ticket_for_thread(
    db: Session, company_id: int, thread_id: str
) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.company_id == company_id, Ticket.thread_id == thread_id)
        .first()
    )


def open_ticket(
    db: Session,
    company_id: int,
    customer_id: int,
    subject: str | None,
    thread_id: str | None,
) -> Ticket:
    ticket = Ticket(
        company_id=company_id,
        customer_id=customer_id,
        subject=subject,
        thread_id=thread_id,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def find_or_open_ticket(
    db: Session,
    company_id: int,
    customer_id: int,
    subject: str | None,
    message_id: str | None,
    in_reply_to: str | None = None,
) -> Ticket:
    """Find the Ticket an inbound email belongs to via In-Reply-To threading,
    or open a new one. A reply to a resolved/closed Ticket reopens it."""
    if in_reply_to:
        parent = (
            db.query(Message)
            .filter(
                Message.company_id == company_id,
                Message.message_id == in_reply_to,
            )
            .first()
        )
        if parent is not None:
            ticket = get_ticket(db, company_id, parent.ticket_id)
            if ticket is not None:
                if ticket.status != TicketStatus.OPEN:
                    transition_ticket(db, ticket, TicketStatus.OPEN)
                return ticket
    return open_ticket(db, company_id, customer_id, subject, thread_id=message_id)


def get_ticket(db: Session, company_id: int, ticket_id: int) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.company_id == company_id)
        .first()
    )


def list_tickets(
    db: Session, company_id: int, status: str | None = None
) -> list[Ticket]:
    query = db.query(Ticket).filter(Ticket.company_id == company_id)
    if status:
        query = query.filter(Ticket.status == status)
    return query.order_by(Ticket.id.desc()).all()


def list_resolved_ticket_summaries(
    db: Session,
    company_id: int,
    customer_id: int,
    exclude_ticket_id: int | None = None,
    limit: int = 10,
) -> list[str]:
    """A Customer's past Ticket summaries (newest first) for Memory injection.

    Tenant-scoped; only Tickets that already carry a summary, excluding the
    current one. Capped by ``limit``; the caller still trims to a char budget.
    """
    query = db.query(Ticket.summary).filter(
        Ticket.company_id == company_id,
        Ticket.customer_id == customer_id,
        Ticket.summary.isnot(None),
    )
    if exclude_ticket_id is not None:
        query = query.filter(Ticket.id != exclude_ticket_id)
    rows = query.order_by(Ticket.id.desc()).limit(limit).all()
    return [summary for (summary,) in rows if summary and summary.strip()]


def transition_ticket(db: Session, ticket: Ticket, new_status: str) -> Ticket:
    assert_ticket_transition(ticket.status, new_status)
    ticket.status = new_status
    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = func.now()
    elif new_status == TicketStatus.CLOSED:
        ticket.closed_at = func.now()
    db.commit()
    db.refresh(ticket)

    # A resolved/closed Ticket gets a one-line summary that feeds Memory on the
    # Customer's future Tickets. Generated once (don't overwrite on re-resolve).
    if (
        new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
        and not ticket.summary
    ):
        _summarize_on_close(db, ticket)
    return ticket


def _summarize_on_close(db: Session, ticket: Ticket) -> None:
    """Best-effort Ticket summarisation. A failed/slow LLM call must never break
    the status transition, so this swallows errors after logging them."""
    # Lazy import: ai_service pulls in the LLM stack, and importing it at module
    # load would couple this widely-imported service to it (and risk a cycle).
    from backend.services import ai_service

    try:
        summary = ai_service.summarize_ticket(db, ticket)
        if summary:
            ticket.summary = summary
            db.commit()
            db.refresh(ticket)
    except Exception:
        logger.exception("Summarising ticket %s failed", ticket.id)
        db.rollback()


def escalate_ticket(db: Session, ticket: Ticket, reason: str) -> Ticket:
    ticket.escalated = True
    ticket.escalation_reason = reason
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------- Messages ----------------
def add_message(
    db: Session,
    *,
    company_id: int,
    ticket_id: int,
    direction: str,
    body: str,
    subject: str | None = None,
    sender_email: str | None = None,
    recipient_email: str | None = None,
    message_id: str | None = None,
    in_reply_to: str | None = None,
) -> Message:
    """Append a Message to a Ticket. Inbound messages enter the review flow;
    outbound messages are not applicable to it."""
    review_status = (
        ReviewStatus.AWAITING_AI
        if direction == MessageDirection.INBOUND
        else ReviewStatus.NOT_APPLICABLE
    )
    message = Message(
        company_id=company_id,
        ticket_id=ticket_id,
        direction=direction,
        body=body,
        subject=subject,
        sender_email=sender_email,
        recipient_email=recipient_email,
        message_id=message_id,
        in_reply_to=in_reply_to,
        review_status=review_status,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def transition_message(db: Session, message: Message, new_status: str) -> Message:
    assert_review_transition(message.review_status, new_status)
    message.review_status = new_status
    db.commit()
    db.refresh(message)
    return message


def record_ai_draft(
    db: Session,
    message: Message,
    draft: str,
    confidence: int | None = None,
    intent: str | None = None,
) -> Message:
    """Store an AI draft on an inbound Message and move it to DRAFTED."""
    assert_review_transition(message.review_status, ReviewStatus.DRAFTED)
    message.ai_draft = draft
    message.confidence = confidence
    if intent is not None:
        message.intent = intent
    message.review_status = ReviewStatus.DRAFTED
    db.commit()
    db.refresh(message)
    return message


def get_message(db: Session, company_id: int, message_id: int) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.id == message_id, Message.company_id == company_id)
        .first()
    )


def list_ticket_messages(db: Session, company_id: int, ticket_id: int) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.company_id == company_id, Message.ticket_id == ticket_id)
        .order_by(Message.id.asc())
        .all()
    )


def count_outbound_messages(db: Session, company_id: int, ticket_id: int) -> int:
    """How many replies have already gone out on a Ticket. Feeds the
    repeated-replies escalation rule."""
    return (
        db.query(func.count(Message.id))
        .filter(
            Message.company_id == company_id,
            Message.ticket_id == ticket_id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .scalar()
        or 0
    )


def list_review_queue(db: Session, company_id: int) -> list[Message]:
    """Inbound Messages awaiting human review: DRAFTED, on a non-escalated
    Ticket, lowest confidence first."""
    return (
        db.query(Message)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .filter(
            Message.company_id == company_id,
            Message.review_status == ReviewStatus.DRAFTED,
            Ticket.escalated.is_(False),
        )
        .order_by(Message.confidence.asc())
        .all()
    )


def company_stats(db: Session, company_id: int) -> dict:
    """Aggregate Ticket counts for a Company's dashboard overview."""
    tickets = db.query(Ticket).filter(Ticket.company_id == company_id)
    return {
        "tickets_total": tickets.count(),
        "tickets_open": tickets.filter(Ticket.status == TicketStatus.OPEN).count(),
        "tickets_pending": tickets.filter(
            Ticket.status == TicketStatus.PENDING
        ).count(),
        "tickets_resolved": tickets.filter(
            Ticket.status == TicketStatus.RESOLVED
        ).count(),
        "tickets_closed": tickets.filter(Ticket.status == TicketStatus.CLOSED).count(),
        "tickets_escalated": tickets.filter(Ticket.escalated.is_(True)).count(),
        "review_queue": len(list_review_queue(db, company_id)),
    }
