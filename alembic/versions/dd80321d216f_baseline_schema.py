"""baseline schema

Captures the schema as it existed at the start of the production refactor:
the ``companies``, ``users`` and ``emails`` tables created (until Phase 1) by
``Base.metadata.create_all``.

Existing databases are marked as already at this revision with
``alembic stamp head`` — this migration is the starting point for future
migrations and for building fresh databases.

Revision ID: dd80321d216f
Revises:
Create Date: 2026-05-21 17:08:19.348538
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd80321d216f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String()),
    )
    op.create_index("ix_companies_id", "companies", ["id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String()),
        sa.Column("email", sa.String()),
        sa.Column("password_hash", sa.String()),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("role", sa.String()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

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


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("emails")
    op.drop_table("users")
    op.drop_table("companies")
