"""expand company and user; owner per signup

Adds the signup address fields to ``companies``, renames ``users.name`` to
``full_name``, and adds ``phone`` plus timestamps. Uses batch operations so it
also works on SQLite.

Revision ID: 3d3e063b9932
Revises: dd80321d216f
Create Date: 2026-05-21 17:17:46.697243
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d3e063b9932"
down_revision: str | Sequence[str] | None = "dd80321d216f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(sa.Column("address_line", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("city", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("state", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("postal_code", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "name", new_column_name="full_name", existing_type=sa.String()
        )
        batch_op.add_column(sa.Column("phone", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("phone")
        batch_op.alter_column(
            "full_name", new_column_name="name", existing_type=sa.String()
        )

    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("postal_code")
        batch_op.drop_column("country")
        batch_op.drop_column("state")
        batch_op.drop_column("city")
        batch_op.drop_column("address_line")
