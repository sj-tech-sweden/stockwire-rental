"""add source_serial_id to devices

Revision ID: 20260601_0030
Revises: 20260526_0023
Create Date: 2026-06-01 09:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260601_0030"
down_revision = "20260526_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("source_serial_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_devices_source_serial_id"), "devices", ["source_serial_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_devices_source_serial_id"), table_name="devices")
    op.drop_column("devices", "source_serial_id")
