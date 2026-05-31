"""Tenant isolation: one Company must never read or act on another's data.

Company A's domain rows are seeded directly (the same in-memory DB the API
uses), then every read/action is attempted as Company B and must be denied,
while Company A still sees its own.
"""

from backend.models.enums import (
    KbDocType,
    MailboxProvider,
    MailboxStatus,
    MessageDirection,
)
from backend.models.mailbox import Mailbox
from backend.services import kb_service, ticket_service
from tests.helpers import register_company


async def test_company_cannot_access_another_companys_data(client, db):
    a = await register_company(client, "a@acme.com", "Acme")
    b = await register_company(client, "b@globex.com", "Globex")

    # --- Seed Company A's data directly in the DB ---
    customer = ticket_service.get_or_create_customer(db, a["company_id"], "cust@x.com")
    ticket = ticket_service.open_ticket(
        db, a["company_id"], customer.id, subject="A's ticket", thread_id="thread-a"
    )
    message = ticket_service.add_message(
        db,
        company_id=a["company_id"],
        ticket_id=ticket.id,
        direction=MessageDirection.INBOUND,
        body="Where is my order?",
    )
    ticket_service.record_ai_draft(db, message, "Draft reply", 50, "general_support")

    db.add(
        Mailbox(
            company_id=a["company_id"],
            email_address="support@acme.com",
            provider=MailboxProvider.GMAIL_APP_PASSWORD,
            encrypted_credential=b"ciphertext",
            imap_host="imap.gmail.com",
            smtp_host="smtp.gmail.com",
            status=MailboxStatus.CONNECTED,
        )
    )
    db.commit()
    kb_service.create_document(
        db,
        a["company_id"],
        filename="policy.txt",
        source_uri="data/users/a/raw/policy.txt",
        doc_type=KbDocType.TXT,
    )

    ah, bh = a["headers"], b["headers"]

    # --- Ticket detail: A sees it, B gets 404 ---
    assert (
        await client.get(f"/api/v1/tickets/{ticket.id}", headers=ah)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/tickets/{ticket.id}", headers=bh)
    ).status_code == 404

    # --- Review queue is scoped ---
    a_queue = await client.get("/api/v1/tickets/queue", headers=ah)
    b_queue = await client.get("/api/v1/tickets/queue", headers=bh)
    assert len(a_queue.json()) == 1 and a_queue.json()[0]["ticket_id"] == ticket.id
    assert b_queue.json() == []

    # --- Message action: B cannot act on A's message ---
    assert (
        await client.post(f"/api/v1/messages/{message.id}/approve", headers=bh)
    ).status_code == 404

    # --- Mailbox is scoped ---
    assert (await client.get("/api/v1/mailbox", headers=ah)).status_code == 200
    assert (await client.get("/api/v1/mailbox", headers=bh)).status_code == 404

    # --- KB documents are scoped ---
    a_docs = await client.get("/api/v1/data/documents", headers=ah)
    b_docs = await client.get("/api/v1/data/documents", headers=bh)
    assert len(a_docs.json()) == 1
    assert b_docs.json() == []
