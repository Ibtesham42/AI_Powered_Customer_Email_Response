"""Background worker: polls every connected Company mailbox over IMAP,
ingests email into the Ticket/Message model, and drains the AI draft queue.

Each Company connects its own support mailbox (Phase 3). For every stored
``Mailbox`` the worker decrypts the App Password, fetches unread mail through
a ``MailboxConnector``, ingests it, and records the poll result on the mailbox
row. One mailbox failing never stops the others.
"""

import os
import signal
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func  # noqa: E402

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
    escalation_service,
    mailbox_service,
    ticket_service,
)

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 10

# Most AI drafts to generate in one worker cycle, so a backlog cannot starve
# mailbox polling.
MAX_DRAFTS_PER_CYCLE = 25

# Backoff after an *unexpected* top-level failure (e.g. the DB is completely
# down at SessionLocal() time). Short enough to recover quickly, long enough not
# to hot-loop while the dependency is unavailable.
CRASH_BACKOFF_SECONDS = 5

# Set by the SIGTERM/SIGINT handlers so the main loop can finish its current
# cycle and exit cleanly — `docker stop` / Cloud Run shutdown sends SIGTERM and
# we don't want to be killed mid-draft.
_shutdown = False


def _request_shutdown(signum, _frame) -> None:
    """Signal handler: ask the main loop to stop after the current cycle."""
    global _shutdown
    _shutdown = True
    logger.info("Received signal %s — shutting down after current cycle", signum)


def _interruptible_sleep(seconds: float) -> None:
    """Sleep in short slices so a shutdown request is noticed promptly."""
    deadline = time.monotonic() + seconds
    while not _shutdown and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


def _ingest_email(db, company_id: int, e: dict) -> None:
    """Ingest one fetched email into the Ticket/Message model.

    The new inbound Message is stored ``review_status = awaiting_ai`` by
    ``add_message`` — that state *is* the AI draft queue (see process_queue)."""
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
    """Draft replies for inbound Messages awaiting AI.

    The queue is not a separate store — it is every Message with
    ``review_status = awaiting_ai``. Each Message is claimed with
    ``SELECT ... FOR UPDATE SKIP LOCKED`` so concurrent workers never draft the
    same one twice; the claim's row lock is released by ``record_ai_draft``'s
    commit, which in the same transaction moves the Message to ``drafted``.
    """
    db = SessionLocal()
    try:
        # Messages whose draft failed this cycle — excluded so a bad Message
        # cannot be re-claimed in a tight loop; they are retried next cycle.
        failed_ids: set[int] = set()
        drafted = 0
        while drafted < MAX_DRAFTS_PER_CYCLE:
            query = db.query(Message).filter(
                Message.review_status == ReviewStatus.AWAITING_AI
            )
            if failed_ids:
                query = query.filter(Message.id.notin_(failed_ids))
            message = (
                query.order_by(Message.id.asc())
                .with_for_update(skip_locked=True)
                .first()
            )
            if message is None:
                break
            try:
                result = ai_service.generate_draft(db, message)
                ticket_service.record_ai_draft(
                    db,
                    message,
                    result["reply"],
                    result["confidence"],
                    result["intent"],
                )
                ticket = ticket_service.get_ticket(
                    db, message.company_id, message.ticket_id
                )
                if ticket is not None:
                    escalation_service.apply_draft_escalation(db, ticket, result)
                drafted += 1
                logger.info("Drafted reply for message %s", message.id)
            except Exception:
                logger.exception("Drafting message %s failed", message.id)
                db.rollback()
                failed_ids.add(message.id)
        if drafted:
            logger.info("Drafted %d message(s) this cycle", drafted)
    finally:
        db.close()


def _run_cycle() -> None:
    """One poll-then-drain cycle. Per-step failures are already contained by the
    inner try/excepts in poll_mailboxes / process_queue."""
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


def run() -> None:
    # Install handlers so a container stop (SIGTERM) or Ctrl-C (SIGINT) lets the
    # worker finish its current cycle and exit cleanly rather than dying mid-draft.
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)

    logger.info(
        "AI worker started (poll every %ss, max %s drafts/cycle)",
        POLL_INTERVAL_SECONDS,
        MAX_DRAFTS_PER_CYCLE,
    )
    while not _shutdown:
        # Top-level crash guard: anything the per-step handlers didn't catch
        # (e.g. SessionLocal() raising because the DB is fully down) is logged
        # and we back off instead of crashing the process. With
        # restart: unless-stopped this self-heals without relying on the
        # orchestrator's restart loop.
        try:
            _run_cycle()
        except Exception:
            logger.exception(
                "Worker cycle failed — backing off %ss", CRASH_BACKOFF_SECONDS
            )
            _interruptible_sleep(CRASH_BACKOFF_SECONDS)
            continue

        _interruptible_sleep(POLL_INTERVAL_SECONDS)

    logger.info("AI worker stopped cleanly")


if __name__ == "__main__":
    run()
