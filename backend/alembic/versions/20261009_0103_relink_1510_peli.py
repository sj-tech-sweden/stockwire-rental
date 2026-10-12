"""re-link product 888 (1510) to the priced Peli variant

Revision ID: 0103
Revises: 0102
Create Date: 2026-10-09

Product 888 ("1510") was linked to vendor product 21221 ("Peli 1510 Foam Black")
which has no unit cost in the catalog, so purchase orders built from it had no
price. Point the link at the priced "Peli 1510 LOC Black" variant (19824) so the
unit price/currency resolve. Idempotent: only rewrites the specific bad link.
"""

from alembic import op
from sqlalchemy import text

revision = '0103'
down_revision = '0102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            "UPDATE product_suppliers "
            "SET vendor_product_id = 19824 "
            "WHERE product_id = 888 AND supplier_id = 22 AND vendor_product_id = 21221"
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            "UPDATE product_suppliers "
            "SET vendor_product_id = 21221 "
            "WHERE product_id = 888 AND supplier_id = 22 AND vendor_product_id = 19824"
        )
    )
