"""add rental product metadata columns

Revision ID: 20260521_0013
Revises: 20260520_0012
Create Date: 2026-05-21 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0013"
down_revision = "20260520_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("is_rental_product", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("products", sa.Column("supplier_name", sa.String(length=255), nullable=True))
    op.add_column("products", sa.Column("rental_price", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("external_source", sa.String(length=80), nullable=True))
    op.add_column("products", sa.Column("external_reference", sa.String(length=120), nullable=True))

    op.create_index("ix_products_is_rental_product", "products", ["is_rental_product"])
    op.create_index("ix_products_supplier_name", "products", ["supplier_name"])
    op.create_index("ix_products_external_source", "products", ["external_source"])
    op.create_index("ix_products_external_reference", "products", ["external_reference"])


def downgrade() -> None:
    op.drop_index("ix_products_external_reference", table_name="products")
    op.drop_index("ix_products_external_source", table_name="products")
    op.drop_index("ix_products_supplier_name", table_name="products")
    op.drop_index("ix_products_is_rental_product", table_name="products")

    op.drop_column("products", "external_reference")
    op.drop_column("products", "external_source")
    op.drop_column("products", "rental_price")
    op.drop_column("products", "supplier_name")
    op.drop_column("products", "is_rental_product")
