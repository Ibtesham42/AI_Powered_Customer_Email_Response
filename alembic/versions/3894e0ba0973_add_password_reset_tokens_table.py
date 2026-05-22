"""add password_reset_tokens table

Revision ID: 3894e0ba0973
Revises: 0e9582994b57
Create Date: 2026-05-23 00:45:31.584477

Single-use, short-lived password-reset tokens (Phase 3 chunk 5). Only the
SHA-256 hash of each token is stored.

Note: autogenerate also proposed redundant ``ix_<table>_id`` indexes on
audit_logs, customers, messages and tickets — pre-existing drift unrelated to
this chunk, intentionally left out (the PK already provides the index).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3894e0ba0973'
down_revision: Union[str, Sequence[str], None] = '0e9582994b57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_password_reset_tokens_id'), ['id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_password_reset_tokens_token_hash'),
            ['token_hash'],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f('ix_password_reset_tokens_user_id'),
            ['user_id'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_token_hash'))
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_id'))

    op.drop_table('password_reset_tokens')
