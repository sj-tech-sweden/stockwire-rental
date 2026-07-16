"""add rotation column to zones

Revision ID: 20260715_0045
Revises: 20260715_0044
Create Date: 2026-07-15 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0045"
down_revision = "20260715_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("rotation", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("zones", "rotation")
