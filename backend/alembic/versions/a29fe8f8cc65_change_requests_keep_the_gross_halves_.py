"""change requests keep the gross halves of their cost impact

Nullable, and rows written before this migration keep NULL rather than a
derived guess: a net cost impact cannot be split back into the addition and
the removal that produced it, which is the whole reason these columns exist.
A request analysed before this migration has to be re-analysed to gain them.

Revision ID: a29fe8f8cc65
Revises: c3cce7e8a225
Create Date: 2026-10-31 00:11:47.030436

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a29fe8f8cc65"
down_revision: str | Sequence[str] | None = "c3cce7e8a225"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("change_requests", sa.Column("added_value", sa.Numeric(), nullable=True))
    op.add_column("change_requests", sa.Column("removed_value", sa.Numeric(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("change_requests", "removed_value")
    op.drop_column("change_requests", "added_value")
