"""add zone layout columns for warehouse map

Revision ID: 20260713_0042
Revises: 20260615_0041
Create Date: 2026-07-13 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_0042"
down_revision = "20260615_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("pos_x", sa.Integer(), nullable=True))
    op.add_column("zones", sa.Column("pos_y", sa.Integer(), nullable=True))
    op.add_column("zones", sa.Column("map_width", sa.Integer(), nullable=True))
    op.add_column("zones", sa.Column("map_height", sa.Integer(), nullable=True))
    op.add_column("zones", sa.Column("color", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("zones", "color")
    op.drop_column("zones", "map_height")
    op.drop_column("zones", "map_width")
    op.drop_column("zones", "pos_y")
    op.drop_column("zones", "pos_x")
