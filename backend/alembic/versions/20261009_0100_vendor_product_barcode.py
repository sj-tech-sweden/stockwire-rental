"""add barcode to vendor_products

Revision ID: 0100
Revises: 0099
Create Date: 2026-10-08

Vendor catalog items (e.g. imported from Thomann) often carry an EAN/GTIN. We
store it on vendor_products so a linked warehouse product can inherit a scannable
barcode for the receiving flow without re-keying it by hand.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0100"
down_revision = "0099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("barcode", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_vendor_products_barcode", "vendor_products", ["barcode"])


def downgrade() -> None:
    op.drop_index("ix_vendor_products_barcode", table_name="vendor_products")
    op.drop_column("vendor_products", "barcode")
