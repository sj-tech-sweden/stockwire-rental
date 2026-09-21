"""Venue coordinates for routing.

Revision ID: 0079
Revises: 0078
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("venues", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("venues", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("venues", "longitude")
    op.drop_column("venues", "latitude")
