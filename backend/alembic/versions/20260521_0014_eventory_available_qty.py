"""add eventory available quantity to products

Revision ID: 20260521_0014
Revises: 20260521_0013
Create Date: 2026-05-21 16:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0014"
down_revision = "20260521_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("eventory_available_qty", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("products", "eventory_available_qty")
