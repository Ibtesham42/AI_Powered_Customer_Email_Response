"""add users.token_version for access-token revocation

Adds ``users.token_version`` (default 1). The access-token JWT carries this
value; bumping it (on "sign out everywhere" or a password reset) invalidates
every outstanding access token for that user — closing the long-lived,
non-revocable access-token gap (audit H2). Existing rows default to 1 via the
server default. Uses batch operations so it also works on SQLite.

Revision ID: a1b2c3d4e5f6
Revises: 4da268d4e51a
Create Date: 2026-05-31 22:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "4da268d4e51a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
