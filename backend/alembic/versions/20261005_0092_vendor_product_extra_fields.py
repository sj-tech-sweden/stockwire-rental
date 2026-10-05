"""vendor products weight, origin, intrastat, packaging and product url

Revision ID: 0092
Revises: 0091
Create Date: 2026-10-05

Adds fields captured from rich supplier feeds (e.g. Aurdel's XML price file):
product URL, weight, country of origin, intrastat code and pieces per carton.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0092"
down_revision = "0091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_products",
        sa.Column("product_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("weight", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("country_of_origin", sa.String(8), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("intrastat_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "vendor_products",
        sa.Column("pieces_per_carton", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendor_products", "pieces_per_carton")
    op.drop_column("vendor_products", "intrastat_code")
    op.drop_column("vendor_products", "country_of_origin")
    op.drop_column("vendor_products", "weight")
    op.drop_column("vendor_products", "product_url")
