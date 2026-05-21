"""Background worker: polls the support mailbox over IMAP, ingests email into
the Ticket/Message model, and drains the AI draft queue.

Per-company mailboxes are Phase 3; until then a single global mailbox is used
and its email is attached to the Company named by ``INGEST_COMPANY_ID``.
"""

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.email.email_listener import EmailListener  # noqa: E402
from app.email.email_queue import add_to_queue, clear_queue, get_queue  # noqa: E402
from app.utils.config import Config  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.logging_config import configure_logging, get_logger  # noqa: E402
from backend.models.company import Company  # noqa: E402
from backend.models.enums import MessageDirection, ReviewStatus  # noqa: E402
from backend.models.message import Message  # noqa: E402

# User is imported so the `users` table is registered for FK resolution.
from backend.models.user import User  # noqa: E402, F401
from backend.services import ai_service, ticket_service  # noqa: E402

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 10


def fetch_emails(db) -> None:
    """Poll the global mailbox and ingest unread email into Tickets/Messages."""
    company_id = settings.INGEST_COMPANY_ID
    if not company_id:
        logger.warning("INGEST_COMPANY_ID is not set — skipping ingestion")
        return
    if db.query(Company).filter(Company.id == company_id).first() is None:
        logger.error(
            "INGEST_COMPANY_ID=%s but no such Company — skipping ingestion",
            company_id,
        )
        return

    listener = EmailListener(
        host="imap.gmail.com",
        email_user=Config.EMAIL_USER,
        password=Config.EMAIL_PASS,
    )
    for e in listener.fetch_unread_emails():
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
            "Ingested email -> ticket %s, message %s", ticket.id, message.id
        )


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
            # queue is replaced by a DB-backed queue in Phase 3.
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
            fetch_emails(db)
        except Exception:
            logger.exception("Email fetch failed")
        finally:
            db.close()

        try:
            process_queue()
        except Exception:
            logger.exception("Queue processing failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
