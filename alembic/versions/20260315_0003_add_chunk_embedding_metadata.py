"""add chunk embedding metadata

Revision ID: 20260315_0003
Revises: 20260315_0002
Create Date: 2026-03-15 22:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0003"
down_revision: str | None = "20260315_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE chunks "
        "SET embedding_dimensions = vector_dims(embedding) "
        "WHERE embedding IS NOT NULL AND embedding_dimensions IS NULL"
    )


def downgrade() -> None:
    op.drop_column("chunks", "embedding_dimensions")
    op.drop_column("chunks", "embedding_model")
