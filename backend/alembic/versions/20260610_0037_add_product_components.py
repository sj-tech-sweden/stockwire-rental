"""add product_components table

Revision ID: 20260610_0037
Revises: 20260610_0036
Create Date: 2026-06-10 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0037"
down_revision = "20260610_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_components_parent_product_id", "product_components", ["parent_product_id"])
    op.create_index("ix_product_components_component_product_id", "product_components", ["component_product_id"])
    op.create_unique_constraint(
        "uq_product_components_parent_component",
        "product_components",
        ["parent_product_id", "component_product_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_product_components_parent_component", "product_components", type_="unique")
    op.drop_index("ix_product_components_parent_product_id", table_name="product_components")
    op.drop_index("ix_product_components_component_product_id", table_name="product_components")
    op.drop_table("product_components")
