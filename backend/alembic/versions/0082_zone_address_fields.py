"""Zone structured address fields.

Revision ID: 0081
Revises: 0080
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("address_line1", sa.String(length=255), nullable=True))
    op.add_column("zones", sa.Column("address_line2", sa.String(length=255), nullable=True))
    op.add_column("zones", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("zones", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("zones", sa.Column("country", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("zones", "country")
    op.drop_column("zones", "city")
    op.drop_column("zones", "postal_code")
    op.drop_column("zones", "address_line2")
    op.drop_column("zones", "address_line1")
