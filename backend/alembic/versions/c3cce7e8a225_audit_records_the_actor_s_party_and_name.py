"""audit records the actor's party and name

Both columns are nullable, and rows written before this migration keep a NULL
party rather than a guessed one. The audit log is append-only (FR-13): a
backfill would be inventing a fact about an event that has already happened.

Revision ID: c3cce7e8a225
Revises: 512ebfb2a1e8
Create Date: 2026-10-30 23:08:44.366986

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3cce7e8a225"
down_revision: str | Sequence[str] | None = "512ebfb2a1e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("audit_log", sa.Column("actor_party", sa.String(length=32), nullable=True))
    op.add_column("audit_log", sa.Column("actor_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("audit_log", "actor_name")
    op.drop_column("audit_log", "actor_party")
