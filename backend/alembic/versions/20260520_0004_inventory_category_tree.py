"""add inventory category tree and product category_id

Revision ID: 20260520_0004
Revises: 20260518_0003, 20260520_0002
Create Date: 2026-05-20 11:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0004"
down_revision = ("20260518_0003", "20260520_0002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("inventory_categories.id"), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventory_categories_name", "inventory_categories", ["name"], unique=False)
    op.create_index("ix_inventory_categories_parent_id", "inventory_categories", ["parent_id"], unique=False)

    op.add_column("products", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_products_category_id_inventory_categories",
        "products",
        "inventory_categories",
        ["category_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_category_id_inventory_categories", "products", type_="foreignkey")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_column("products", "category_id")

    op.drop_index("ix_inventory_categories_parent_id", table_name="inventory_categories")
    op.drop_index("ix_inventory_categories_name", table_name="inventory_categories")
    op.drop_table("inventory_categories")
