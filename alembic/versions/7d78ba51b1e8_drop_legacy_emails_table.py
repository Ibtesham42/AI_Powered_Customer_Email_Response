"""drop legacy emails table

Phase 2 chunk 3f — the `emails` table is retired now that ingestion, the AI
service, the routes and the dashboard all run on Customer/Ticket/Message.
The table is empty, so there is no data to migrate.

Revision ID: 7d78ba51b1e8
Revises: 76870d572c26
Create Date: 2026-05-22 02:30:21.360900
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d78ba51b1e8"
down_revision: str | Sequence[str] | None = "76870d572c26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("emails")


def downgrade() -> None:
    """Downgrade schema — recreate the legacy emails table (empty)."""
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender", sa.String()),
        sa.Column("subject", sa.String()),
        sa.Column("body", sa.String()),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("thread_id", sa.String(), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("status", sa.String()),
        sa.Column("ai_reply", sa.String(), nullable=True),
        sa.Column("final_reply", sa.String(), nullable=True),
        sa.Column("confidence", sa.Integer()),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
    )
    op.create_index("ix_emails_id", "emails", ["id"])
