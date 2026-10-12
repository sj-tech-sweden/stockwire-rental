"""add supplier_name column to purchase_orders

Revision ID: 0102
Revises: 0101
Create Date: 2026-10-09

PurchaseOrderRead exposes supplier_name and the frontend lists POs by supplier,
but the stored PO only kept supplier_company_id. Persisting the supplier name
means created POs show their supplier even before the company is resolved.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '0102'
down_revision = '0101'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("supplier_name", sa.String(length=200), nullable=True),
    )
    # Backfill supplier_name for any POs created before this column existed.
    op.execute(
        text(
            "UPDATE purchase_orders "
            "SET supplier_name = (SELECT c.name FROM companies c "
            "WHERE c.id = purchase_orders.supplier_company_id) "
            "WHERE supplier_name IS NULL AND supplier_company_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "supplier_name")
