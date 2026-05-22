"""add product accessories and device case containment

Revision ID: 20260520_0012
Revises: 20260520_0011
Create Date: 2026-05-20 20:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0012"
down_revision = "20260520_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("case_device_id", sa.Integer(), nullable=True))
    op.create_index("ix_devices_case_device_id", "devices", ["case_device_id"])
    op.create_foreign_key(
        "fk_devices_case_device_id",
        "devices",
        "devices",
        ["case_device_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "product_accessories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accessory_product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_accessories_parent_product_id", "product_accessories", ["parent_product_id"])
    op.create_index("ix_product_accessories_accessory_product_id", "product_accessories", ["accessory_product_id"])
    op.create_unique_constraint(
        "uq_product_accessories_parent_accessory",
        "product_accessories",
        ["parent_product_id", "accessory_product_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_product_accessories_parent_accessory", "product_accessories", type_="unique")
    op.drop_index("ix_product_accessories_accessory_product_id", table_name="product_accessories")
    op.drop_index("ix_product_accessories_parent_product_id", table_name="product_accessories")
    op.drop_table("product_accessories")

    op.drop_constraint("fk_devices_case_device_id", "devices", type_="foreignkey")
    op.drop_index("ix_devices_case_device_id", table_name="devices")
    op.drop_column("devices", "case_device_id")
