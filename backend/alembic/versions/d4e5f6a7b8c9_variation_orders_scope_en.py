"""variation orders keep the English scope wording

The English paragraph is drafted in the same call as the Arabic one. Orders
issued before this migration have none, so they get an empty string and the
interface shows their Arabic original.

Revision ID: d4e5f6a7b8c9
Revises: a29fe8f8cc65
Create Date: 2026-10-31 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "a29fe8f8cc65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "variation_orders",
        sa.Column("scope_en", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("variation_orders", "scope_en")
