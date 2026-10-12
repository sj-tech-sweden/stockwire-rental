"""vendor products incoming stock fields

Revision ID: 0093
Revises: 0092
Create Date: 2026-10-05

Captures inbound/expected stock from supplier feeds (Aurdel's XML exposes a
delivery date and quantity per item): the expected delivery date and the
incoming quantity.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0093"
down_revision = "0092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("incoming_quantity", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendor_products", "incoming_quantity")
    op.drop_column("vendor_products", "expected_delivery_date")
