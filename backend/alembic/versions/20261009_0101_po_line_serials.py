"""add serials column to purchase_order_lines

Revision ID: 0101
Revises: 0100
Create Date: 2026-10-09

Sale-article purchase-order lines (no linked warehouse product, or sourced from
a non-scannable job requirement) are received without creating Device records.
Captured serial numbers are still recorded against the line so they stay attached
to the originating job.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0101"
down_revision = "0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_order_lines",
        sa.Column("serials", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_order_lines", "serials")
