"""vendor products vendor/supplier item numbers

Revision ID: 0091
Revises: 0090
Create Date: 2026-10-05

Splits the overloaded article number into a vendor (manufacturer) item number
and a supplier (e.g. Aurdel) item number so imports can capture both identities
from their respective source fields.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("vendor_item_number", sa.String(120), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("supplier_item_number", sa.String(120), nullable=True),
    )
    op.create_index(
        "ix_vendor_products_vendor_item_number",
        "vendor_products",
        ["vendor_item_number"],
    )
    op.create_index(
        "ix_vendor_products_supplier_item_number",
        "vendor_products",
        ["supplier_item_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_vendor_products_supplier_item_number", table_name="vendor_products")
    op.drop_index("ix_vendor_products_vendor_item_number", table_name="vendor_products")
    op.drop_column("vendor_products", "supplier_item_number")
    op.drop_column("vendor_products", "vendor_item_number")
