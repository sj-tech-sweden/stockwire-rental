"""vendor products currency, stock and availability

Revision ID: 0090
Revises: 0089
Create Date: 2026-10-02

Adds currency, stock_quantity and availability to the vendor_products table so
imports can capture per-supplier price currency and stock/availability for
supplier comparison.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0090"
down_revision = "0089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("currency", sa.String(10), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("stock_quantity", sa.Integer, nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("availability", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendor_products", "availability")
    op.drop_column("vendor_products", "stock_quantity")
    op.drop_column("vendor_products", "currency")
