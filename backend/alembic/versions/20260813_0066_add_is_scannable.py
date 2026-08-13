"""add is_scannable to product_accessories and product_components

Revision ID: 0066
Revises: 0065
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_accessories", sa.Column("is_scannable", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("product_components", sa.Column("is_scannable", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("product_components", "is_scannable")
    op.drop_column("product_accessories", "is_scannable")
