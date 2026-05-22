"""add mailboxes table

Revision ID: 0e9582994b57
Revises: 7d78ba51b1e8
Create Date: 2026-05-22 22:42:56.301076

One support mailbox per Company (Phase 3). The App Password is stored only as
a Fernet-encrypted token in ``encrypted_credential`` (ADR-0002).

Note: autogenerate also proposed ``ix_<table>_id`` indexes on audit_logs,
customers, messages and tickets — pre-existing drift (those models declare a
redundant ``index=True`` on the primary-key column). That is unrelated to this
chunk and intentionally left out; the PK already provides the index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e9582994b57'
down_revision: Union[str, Sequence[str], None] = '7d78ba51b1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'mailboxes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('email_address', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('encrypted_credential', sa.LargeBinary(), nullable=False),
        sa.Column('imap_host', sa.String(), nullable=False),
        sa.Column('smtp_host', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('last_polled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('mailboxes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_mailboxes_company_id'), ['company_id'], unique=True
        )
        batch_op.create_index(
            batch_op.f('ix_mailboxes_id'), ['id'], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('mailboxes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mailboxes_id'))
        batch_op.drop_index(batch_op.f('ix_mailboxes_company_id'))

    op.drop_table('mailboxes')
