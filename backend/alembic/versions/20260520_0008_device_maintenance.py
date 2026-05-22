"""add device maintenance table

Revision ID: 20260520_0008
Revises: 20260520_0007
Create Date: 2026-05-20 21:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0008"
down_revision = "20260520_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_maintenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("maintenance_type", sa.String(length=80), nullable=False, server_default="scheduled"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="scheduled"),
        sa.Column("interval_mode", sa.String(length=20), nullable=False, server_default="calendar"),
        sa.Column("interval_value", sa.Integer(), nullable=True),
        sa.Column("due_usage_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name="fk_device_maintenance_device_id_devices"),
    )
    op.create_index("ix_device_maintenance_device_id", "device_maintenance", ["device_id"], unique=False)
    op.create_index("ix_device_maintenance_status", "device_maintenance", ["status"], unique=False)
    op.create_index("ix_device_maintenance_scheduled_date", "device_maintenance", ["scheduled_date"], unique=False)
    op.create_index("ix_device_maintenance_completed_date", "device_maintenance", ["completed_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_device_maintenance_completed_date", table_name="device_maintenance")
    op.drop_index("ix_device_maintenance_scheduled_date", table_name="device_maintenance")
    op.drop_index("ix_device_maintenance_status", table_name="device_maintenance")
    op.drop_index("ix_device_maintenance_device_id", table_name="device_maintenance")
    op.drop_table("device_maintenance")
