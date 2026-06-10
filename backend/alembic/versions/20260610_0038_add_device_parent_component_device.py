"""add parent_component_device_id to devices

Revision ID: 20260610_0038
Revises: 20260610_0037
Create Date: 2026-06-10 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0038"
down_revision = "20260610_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("parent_component_device_id", sa.Integer(), nullable=True))
    op.create_index("ix_devices_parent_component_device_id", "devices", ["parent_component_device_id"])
    op.create_foreign_key(
        "fk_devices_parent_component_device_id",
        "devices",
        "devices",
        ["parent_component_device_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_devices_parent_component_device_id", "devices", type_="foreignkey")
    op.drop_index("ix_devices_parent_component_device_id", table_name="devices")
    op.drop_column("devices", "parent_component_device_id")
