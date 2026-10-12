"""purchase orders for the supplier-comparison / best-purchase workflow

Revision ID: 0096
Revises: 0095
Create Date: 2026-10-05

Creates ``purchase_orders`` and ``purchase_order_lines`` so a recommended
purchase basket (from a draft or a combined set of jobs) can become a real
purchase order, one per supplier, that on receiving creates stock + devices.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0096"
down_revision = "0095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("po_number", sa.String(length=40), nullable=False),
        sa.Column(
            "supplier_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_currency", sa.String(length=10), nullable=False, server_default="EUR"),
        sa.Column("total_base", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("meta_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"], unique=True)
    op.create_index(
        "ix_purchase_orders_supplier_company_id",
        "purchase_orders",
        ["supplier_company_id"],
    )

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "po_id",
            sa.Integer(),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "vendor_product_id",
            sa.Integer(),
            sa.ForeignKey("vendor_products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "requirement_id",
            sa.Integer(),
            sa.ForeignKey("job_requirements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("received_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("converted_unit_cost", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_restock", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_lines_po_id", "purchase_order_lines", ["po_id"])
    op.create_index(
        "ix_purchase_order_lines_vendor_id",
        "purchase_order_lines",
        ["vendor_id"],
    )
    op.create_index(
        "ix_purchase_order_lines_vendor_product_id",
        "purchase_order_lines",
        ["vendor_product_id"],
    )
    op.create_index(
        "ix_purchase_order_lines_product_id",
        "purchase_order_lines",
        ["product_id"],
    )
    op.create_index(
        "ix_purchase_order_lines_requirement_id",
        "purchase_order_lines",
        ["requirement_id"],
    )
    op.create_index(
        "ix_purchase_order_lines_job_id", "purchase_order_lines", ["job_id"]
    )


def downgrade() -> None:
    op.drop_table("purchase_order_lines")
    op.drop_index("ix_purchase_orders_po_number", table_name="purchase_orders")
    op.drop_table("purchase_orders")
