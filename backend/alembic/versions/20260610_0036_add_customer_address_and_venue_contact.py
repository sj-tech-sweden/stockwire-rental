"""add customer address and venue contact fields

Revision ID: 20260610_0036
Revises: 20260602_0035
Create Date: 2026-06-10 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0036"
down_revision = "20260602_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("address", sa.String(255), nullable=True))
    op.add_column("customers", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("customers", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("customers", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("venues", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("venues", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("venues", sa.Column("contact_person", sa.String(255), nullable=True))
    op.add_column("venues", sa.Column("country", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "address")
    op.drop_column("customers", "city")
    op.drop_column("customers", "postal_code")
    op.drop_column("customers", "country")
    op.drop_column("venues", "phone")
    op.drop_column("venues", "email")
    op.drop_column("venues", "contact_person")
    op.drop_column("venues", "country")
