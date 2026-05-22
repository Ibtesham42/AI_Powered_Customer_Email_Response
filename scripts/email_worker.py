"""Background worker: polls every connected Company mailbox over IMAP,
ingests email into the Ticket/Message model, and drains the AI draft queue.

Each Company connects its own support mailbox (Phase 3). For every stored
``Mailbox`` the worker decrypts the App Password, fetches unread mail through
a ``MailboxConnector``, ingests it, and records the poll result on the mailbox
row. One mailbox failing never stops the others.
"""

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func  # noqa: E402

from app.email.email_queue import (  # noqa: E402
    add_to_queue,
    clear_queue,
    get_queue,
)
from backend.config import settings  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.logging_config import configure_logging, get_logger  # noqa: E402

# Company and User are imported so their tables register with Base.metadata
# for foreign-key resolution when querying Mailbox / Message.
from backend.models.company import Company  # noqa: E402, F401
from backend.models.enums import (  # noqa: E402
    MailboxStatus,
    MessageDirection,
    ReviewStatus,
)
from backend.models.mailbox import Mailbox  # noqa: E402
from backend.models.message import Message  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.services import (  # noqa: E402
    ai_service,
    mailbox_service,
    ticket_service,
)

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 10


def _ingest_email(db, company_id: int, e: dict) -> None:
    """Ingest one fetched email into the Ticket/Message model and queue it
    for an AI draft."""
    customer = ticket_service.get_or_create_customer(
        db, company_id, e.get("sender") or "unknown@unknown"
    )
    ticket = ticket_service.find_or_open_ticket(
        db,
        company_id,
        customer.id,
        subject=e.get("subject"),
        message_id=e.get("message_id"),
        in_reply_to=e.get("in_reply_to"),
    )
    message = ticket_service.add_message(
        db,
        company_id=company_id,
        ticket_id=ticket.id,
        direction=MessageDirection.INBOUND,
        body=e.get("body") or "",
        subject=e.get("subject"),
        sender_email=e.get("sender"),
        message_id=e.get("message_id"),
        in_reply_to=e.get("in_reply_to"),
    )
    add_to_queue(message.id, company_id)
    logger.info(
        "Ingested email -> company %s, ticket %s, message %s",
        company_id,
        ticket.id,
        message.id,
    )


def _poll_mailbox(db, mailbox: Mailbox) -> None:
    """Fetch and ingest unread email for one Company's mailbox, then record a
    successful poll on the mailbox row."""
    connector = mailbox_service.build_connector(mailbox)
    emails = connector.fetch_unread()
    for e in emails:
        _ingest_email(db, mailbox.company_id, e)

    mailbox.last_polled_at = func.now()
    mailbox.status = MailboxStatus.CONNECTED
    db.commit()
    logger.info(
        "Polled mailbox %s (company %s): %d new email(s)",
        mailbox.email_address,
        mailbox.company_id,
        len(emails),
    )


def _mark_mailbox_error(db, mailbox: Mailbox) -> None:
    """Record a failed poll on the mailbox row."""
    try:
        mailbox.status = MailboxStatus.ERROR
        mailbox.last_polled_at = func.now()
        db.commit()
    except Exception:
        logger.exception("Could not mark mailbox %s as errored", mailbox.id)
        db.rollback()


def poll_mailboxes(db) -> None:
    """Poll every connected Company mailbox. One failure never stops the rest."""
    mailboxes = db.query(Mailbox).all()
    if not mailboxes:
        logger.info("No mailboxes connected — nothing to poll")
        return

    for mailbox in mailboxes:
        try:
            _poll_mailbox(db, mailbox)
        except Exception:
            logger.exception(
                "Polling mailbox %s (company %s) failed",
                mailbox.email_address,
                mailbox.company_id,
            )
            db.rollback()
            _mark_mailbox_error(db, mailbox)


def process_queue() -> None:
    """Generate an AI draft for each queued inbound Message."""
    db = SessionLocal()
    try:
        queue = get_queue()
        if not queue:
            return
        logger.info("Processing %d queued message(s)", len(queue))
        for item in queue:
            # The JSON queue's "email_id" field carries a Message id here; the
            # queue is replaced by a DB-backed queue in Phase 3 chunk 4.
            message = (
                db.query(Message).filter(Message.id == item["email_id"]).first()
            )
            if message is None:
                continue
            if message.review_status != ReviewStatus.AWAITING_AI:
                continue  # already drafted
            result = ai_service.generate_draft(db, message)
            ticket_service.record_ai_draft(
                db, message, result["reply"], result["confidence"]
            )
            logger.info("Drafted reply for message %s", message.id)
        clear_queue()
    finally:
        db.close()


def run() -> None:
    logger.info("AI worker started (poll every %ss)", POLL_INTERVAL_SECONDS)
    while True:
        db = SessionLocal()
        try:
            poll_mailboxes(db)
        except Exception:
            logger.exception("Mailbox polling failed")
        finally:
            db.close()

        try:
            process_queue()
        except Exception:
            logger.exception("Queue processing failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
