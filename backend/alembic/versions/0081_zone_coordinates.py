"""Zone coordinates for routing (pickup points).

Revision ID: 0080
Revises: 0079
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("zones", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("zones", "longitude")
    op.drop_column("zones", "latitude")
