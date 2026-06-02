"""add device purchase price

Revision ID: 20260601_0031
Revises: 20260601_0030
Create Date: 2026-06-01 05:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0031"
down_revision = "20260601_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("purchase_price", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "purchase_price")