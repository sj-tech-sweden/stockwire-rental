"""add product replace_cost

Revision ID: 20260602_0033
Revises: 20260601_0032
Create Date: 2026-06-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_0033"
down_revision = "20260601_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("replace_cost", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "replace_cost")
