"""add extracted text to documents

Revision ID: 20260315_0002
Revises: 20260315_0001
Create Date: 2026-03-15 16:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0002"
down_revision: str | None = "20260315_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "extracted_text")
