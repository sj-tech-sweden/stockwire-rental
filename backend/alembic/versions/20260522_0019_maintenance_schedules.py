"""add maintenance schedules and task schedule linkage

Revision ID: 20260522_0019
Revises: 20260521_0018
Create Date: 2026-05-22 12:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260522_0019"
down_revision: str | Sequence[str] | None = "20260521_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_maintenance_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("maintenance_type", sa.String(length=80), nullable=False, server_default="inspection"),
        sa.Column("interval_mode", sa.String(length=20), nullable=False, server_default="calendar"),
        sa.Column("interval_value", sa.Integer(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_device_maintenance_schedules_scheduled_date"),
        "device_maintenance_schedules",
        ["scheduled_date"],
        unique=False,
    )

    op.add_column("device_maintenance", sa.Column("schedule_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_device_maintenance_schedule_id"), "device_maintenance", ["schedule_id"], unique=False)
    op.create_foreign_key(
        "fk_device_maintenance_schedule_id_device_maintenance_schedules",
        "device_maintenance",
        "device_maintenance_schedules",
        ["schedule_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_device_maintenance_schedule_id_device_maintenance_schedules", "device_maintenance", type_="foreignkey")
    op.drop_index(op.f("ix_device_maintenance_schedule_id"), table_name="device_maintenance")
    op.drop_column("device_maintenance", "schedule_id")

    op.drop_index(op.f("ix_device_maintenance_schedules_scheduled_date"), table_name="device_maintenance_schedules")
    op.drop_table("device_maintenance_schedules")
