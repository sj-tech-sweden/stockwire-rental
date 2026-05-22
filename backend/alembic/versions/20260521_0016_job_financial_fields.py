"""add job financial fields

Revision ID: 20260521_0016
Revises: 20260521_0015
Create Date: 2026-05-21 19:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0016"
down_revision = "20260521_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("sales_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("jobs", sa.Column("invoice_paid", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("jobs", sa.Column("invoice_paid_at", sa.Date(), nullable=True))
    op.alter_column("jobs", "invoice_paid", server_default=None)


def downgrade() -> None:
    op.drop_column("jobs", "invoice_paid_at")
    op.drop_column("jobs", "invoice_paid")
    op.drop_column("jobs", "sales_price")
