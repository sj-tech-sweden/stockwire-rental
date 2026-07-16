"""add 3D layout columns to zones

Revision ID: 20260715_0044
Revises: 20260713_0042
Create Date: 2026-07-15 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0044"
down_revision = "20260713_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("pos_z", sa.Integer(), nullable=True))
    op.add_column("zones", sa.Column("map_depth", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("zones", "map_depth")
    op.drop_column("zones", "pos_z")
