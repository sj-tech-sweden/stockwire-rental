"""purchase drafts for the best-purchase / supplier-comparison feature

Revision ID: 0095
Revises: 0094
Create Date: 2026-10-05

Creates ``purchase_drafts`` and ``purchase_draft_lines`` so the recommended
purchase basket from the best-purchase engine can be persisted and reused as a
purchase-order draft.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0095"
down_revision = "0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("report_currency", sa.String(length=10), nullable=False, server_default="EUR"),
        sa.Column("total_base", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("supplier_count", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("ix_purchase_drafts_job_id", "purchase_drafts", ["job_id"])

    op.create_table(
        "purchase_draft_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("purchase_drafts.id", ondelete="CASCADE"),
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
            "requirement_id",
            sa.Integer(),
            sa.ForeignKey("job_requirements.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("vendor_name", sa.String(length=255), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("converted_unit_cost", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_selected_cheapest", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_draft_lines_draft_id", "purchase_draft_lines", ["draft_id"])
    op.create_index("ix_purchase_draft_lines_vendor_id", "purchase_draft_lines", ["vendor_id"])
    op.create_index(
        "ix_purchase_draft_lines_vendor_product_id",
        "purchase_draft_lines",
        ["vendor_product_id"],
    )
    op.create_index(
        "ix_purchase_draft_lines_requirement_id",
        "purchase_draft_lines",
        ["requirement_id"],
    )
    op.create_index(
        "ix_purchase_draft_lines_product_id", "purchase_draft_lines", ["product_id"]
    )


def downgrade() -> None:
    op.drop_table("purchase_draft_lines")
    op.drop_index("ix_purchase_drafts_job_id", table_name="purchase_drafts")
    op.drop_table("purchase_drafts")
