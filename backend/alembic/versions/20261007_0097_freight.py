"""freight cost for suppliers and purchase orders

Revision ID: 0097
Revises: 0096
Create Date: 2026-10-07

Adds a default shipping/freight cost to suppliers (companies) and stores the
applied freight per purchase order so the suggestion engine and order totals can
account for shipping when comparing single-supplier vs multi-supplier baskets.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0097"
down_revision = "0096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("freight_cost", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("freight_currency", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("freight_cost", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("freight_currency", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("freight_base", sa.Numeric(precision=14, scale=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "freight_base")
    op.drop_column("purchase_orders", "freight_currency")
    op.drop_column("purchase_orders", "freight_cost")
    op.drop_column("companies", "freight_currency")
    op.drop_column("companies", "freight_cost")
