"""link product suppliers to vendor catalog items

Revision ID: 0098
Revises: 0097
Create Date: 2026-10-08

A product's supplier links (product_suppliers) can now point at a specific
imported vendor catalog item (vendor_products.id) so the warehouse product is
tied to the exact item it can be reordered from, including its live price,
stock and product URL.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0098"
down_revision = "0097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_suppliers",
        sa.Column(
            "vendor_product_id",
            sa.Integer(),
            sa.ForeignKey("vendor_products.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_product_suppliers_vendor_product_id",
        "product_suppliers",
        ["vendor_product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_suppliers_vendor_product_id", table_name="product_suppliers")
    op.drop_column("product_suppliers", "vendor_product_id")
