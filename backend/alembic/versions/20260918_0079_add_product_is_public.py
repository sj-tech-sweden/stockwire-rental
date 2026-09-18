"""Add is_public to products.

Revision ID: 0079
Revises: 0078
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products", sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false")
    )
    op.create_index("ix_products_is_public", "products", ["is_public"])


def downgrade() -> None:
    op.drop_index("ix_products_is_public", table_name="products")
    op.drop_column("products", "is_public")
