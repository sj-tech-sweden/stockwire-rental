"""add barcode to products for receiving scans

Revision ID: 0099
Revises: 0098
Create Date: 2026-10-08

Products get an optional scannable barcode so the receiving flow can resolve a
product (and its open purchase-order lines) by scanning the item barcode,
falling back to the SKU when no barcode is present.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0099"
down_revision = "0098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("barcode", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_products_barcode", "products", ["barcode"])


def downgrade() -> None:
    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_column("products", "barcode")
