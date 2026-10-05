"""vendor products full incoming-deliveries list

Revision ID: 0094
Revises: 0093
Create Date: 2026-10-05

Stores every upcoming delivery advertised by the supplier feed (Aurdel's XML
may carry several ``<date quantity=..>`` entries per item) as a JSON list of
``{expected_delivery_date, incoming_quantity}`` objects, complementing the
single next-delivery columns.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0094"
down_revision = "0093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("incoming_deliveries", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendor_products", "incoming_deliveries")
