"""add customer, ticket, message, audit_log tables

Phase 2 chunk 1 — the Customer + Ticket + Message domain model, plus
audit_logs. Purely additive: the legacy ``emails`` table is untouched.

Revision ID: 76870d572c26
Revises: fd095f9aa6c3
Create Date: 2026-05-21 21:22:56.416144
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "76870d572c26"
down_revision: str | Sequence[str] | None = "fd095f9aa6c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("company_id", "email", name="uq_customers_company_email"),
    )
    op.create_index("ix_customers_company_id", "customers", ["company_id"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False
        ),
        sa.Column(
            "customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False
        ),
        sa.Column("subject", sa.String()),
        sa.Column("thread_id", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column(
            "escalated", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("escalation_reason", sa.String()),
        sa.Column("intent", sa.String()),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("summary", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "company_id", "thread_id", name="uq_tickets_company_thread"
        ),
    )
    op.create_index("ix_tickets_company_id", "tickets", ["company_id"])
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False
        ),
        sa.Column(
            "ticket_id", sa.Integer(), sa.ForeignKey("tickets.id"), nullable=False
        ),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("sender_email", sa.String()),
        sa.Column("recipient_email", sa.String()),
        sa.Column("subject", sa.String()),
        sa.Column("body", sa.String()),
        sa.Column("message_id", sa.String()),
        sa.Column("in_reply_to", sa.String()),
        sa.Column("review_status", sa.String()),
        sa.Column("intent", sa.String()),
        sa.Column("confidence", sa.SmallInteger()),
        sa.Column("ai_draft", sa.String()),
        sa.Column("final_reply", sa.String()),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_messages_company_id", "messages", ["company_id"])
    op.create_index("ix_messages_ticket_id", "messages", ["ticket_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String()),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("metadata", JSONB()),
        sa.Column("ip_address", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_logs_company_id", "audit_logs", ["company_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("audit_logs")
    op.drop_table("messages")
    op.drop_table("tickets")
    op.drop_table("customers")
