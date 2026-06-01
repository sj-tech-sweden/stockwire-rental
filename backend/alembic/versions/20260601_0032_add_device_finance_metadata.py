"""add device finance metadata

Revision ID: 20260601_0032
Revises: 20260601_0031
Create Date: 2026-06-01 05:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0032"
down_revision = "20260601_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("purchased_from", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("sold_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("devices", sa.Column("finance_upto", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("finance_company", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("finance_ref", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("pre_prep", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "pre_prep")
    op.drop_column("devices", "finance_ref")
    op.drop_column("devices", "finance_company")
    op.drop_column("devices", "finance_upto")
    op.drop_column("devices", "sold_price")
    op.drop_column("devices", "purchased_from")