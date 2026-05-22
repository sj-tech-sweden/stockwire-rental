"""add missing device maintenance interval columns

Revision ID: 20260520_0009
Revises: 20260520_0008
Create Date: 2026-05-20 14:35:00
"""

from alembic import op


revision = "20260520_0009"
down_revision = "20260520_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some environments already applied 0008 before interval fields were added.
    # Add the new columns idempotently so existing DBs can be upgraded safely.
    op.execute(
        """
        ALTER TABLE device_maintenance
        ADD COLUMN IF NOT EXISTS interval_mode VARCHAR(20) NOT NULL DEFAULT 'calendar'
        """
    )
    op.execute(
        """
        ALTER TABLE device_maintenance
        ADD COLUMN IF NOT EXISTS interval_value INTEGER NULL
        """
    )
    op.execute(
        """
        ALTER TABLE device_maintenance
        ADD COLUMN IF NOT EXISTS due_usage_hours NUMERIC(10, 2) NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE device_maintenance DROP COLUMN IF EXISTS due_usage_hours")
    op.execute("ALTER TABLE device_maintenance DROP COLUMN IF EXISTS interval_value")
    op.execute("ALTER TABLE device_maintenance DROP COLUMN IF EXISTS interval_mode")
