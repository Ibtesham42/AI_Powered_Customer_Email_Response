"""Send idempotency (pilot blocker B-5): one delivery per reviewed draft.

The send route claims the Message atomically (REVIEWED -> SENDING), so
duplicate/concurrent sends 409 instead of double-emailing the Customer, and an
SMTP failure releases the claim (back to REVIEWED) for a safe retry.
"""

import pytest

from app.email.mailbox_connector import MailboxError
from backend.models.enums import (
    MailboxProvider,
    MailboxStatus,
    MessageDirection,
    ReviewStatus,
)
from backend.models.mailbox import Mailbox
from backend.models.message import Message
from backend.services import mailbox_service, ticket_service
from tests.helpers import register_company


class FakeConnector:
    """Records sends; optionally fails like an unreachable SMTP host."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[dict] = []

    def send(self, **kwargs):
        if self.fail:
            raise MailboxError("SMTP login failed")
        self.sent.append(kwargs)


@pytest.fixture
def seeded(client, db, monkeypatch):
    """A Company with a mailbox and one REVIEWED inbound Message, SMTP faked."""

    async def _build():
        acc = await register_company(client, "send@acme.com", "Acme")
        cid = acc["company_id"]
        customer = ticket_service.get_or_create_customer(db, cid, "cust@x.com")
        ticket = ticket_service.open_ticket(
            db, cid, customer.id, subject="Order", thread_id="t-1"
        )
        message = ticket_service.add_message(
            db,
            company_id=cid,
            ticket_id=ticket.id,
            direction=MessageDirection.INBOUND,
            body="Where is my order?",
        )
        ticket_service.record_ai_draft(db, message, "Draft", 80, "general_support")
        message.final_reply = "Your order ships tomorrow."
        ticket_service.transition_message(db, message, ReviewStatus.REVIEWED)
        db.add(
            Mailbox(
                company_id=cid,
                email_address="support@acme.com",
                provider=MailboxProvider.GMAIL_APP_PASSWORD,
                encrypted_credential=b"ciphertext",
                imap_host="imap.gmail.com",
                smtp_host="smtp.gmail.com",
                status=MailboxStatus.CONNECTED,
            )
        )
        db.commit()
        connector = FakeConnector()
        monkeypatch.setattr(mailbox_service, "build_connector", lambda mb: connector)
        return acc, ticket, message, connector

    return _build


async def test_send_success_delivers_once(client, db, seeded):
    acc, ticket, message, connector = await seeded()

    res = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert res.status_code == 200
    assert len(connector.sent) == 1

    db.expire_all()
    assert db.query(Message).get(message.id).review_status == ReviewStatus.SENT
    outbound = (
        db.query(Message)
        .filter(
            Message.ticket_id == ticket.id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )
    assert outbound == 1


async def test_resend_after_sent_is_rejected(client, db, seeded):
    acc, ticket, message, connector = await seeded()
    first = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert first.status_code == 200

    dup = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert dup.status_code == 409
    assert len(connector.sent) == 1  # never delivered twice

    outbound = (
        db.query(Message)
        .filter(
            Message.ticket_id == ticket.id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )
    assert outbound == 1


async def test_concurrent_claim_is_rejected(client, db, seeded):
    """A Message already claimed (SENDING) cannot be claimed again."""
    acc, _ticket, message, connector = await seeded()
    # Simulate another request having won the claim.
    ticket_service.transition_message(db, message, ReviewStatus.SENDING)

    res = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert res.status_code == 409
    assert connector.sent == []


async def test_smtp_failure_releases_claim_then_retry_succeeds(client, db, seeded):
    acc, _ticket, message, connector = await seeded()
    connector.fail = True

    fail = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert fail.status_code == 502
    db.expire_all()
    # Claim released — the draft is back in review, nothing delivered.
    assert db.query(Message).get(message.id).review_status == ReviewStatus.REVIEWED
    assert connector.sent == []

    # The retry is safe and succeeds.
    connector.fail = False
    retry = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert retry.status_code == 200
    assert len(connector.sent) == 1


async def test_unreviewed_draft_cannot_send(client, db, seeded):
    acc, _ticket, message, connector = await seeded()
    # Pull it back to DRAFTED — sending must be refused before any claim.
    ticket_service.transition_message(db, message, ReviewStatus.DRAFTED)

    res = await client.post(
        f"/api/v1/messages/{message.id}/send", headers=acc["headers"]
    )
    assert res.status_code == 409
    assert connector.sent == []
