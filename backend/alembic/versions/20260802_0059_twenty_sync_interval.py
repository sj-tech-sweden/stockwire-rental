"""add sync_interval_minutes to twenty_config

Revision ID: 20260802_0059
Revises: 20260731_0058
Create Date: 2026-08-02 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260802_0059"
down_revision = "20260731_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "twenty_config",
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("twenty_config", "sync_interval_minutes")
