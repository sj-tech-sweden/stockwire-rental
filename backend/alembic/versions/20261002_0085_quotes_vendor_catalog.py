"""quotes and vendor catalog model changes

Revision ID: 0085
Revises: 0084
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_crew_requirements",
        sa.Column("hours", sa.Numeric(10, 2), nullable=True),
    )

    op.alter_column(
        "job_requirements",
        "product_id",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_nullable=False,
    )

    # Create the referenced table BEFORE adding the foreign-key column.
    op.create_table(
        "vendor_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(120), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dimensions", sa.String(255), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("source_plugin", sa.String(120), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_vendor_products_sku", "vendor_products", ["sku"])
    op.create_index("ix_vendor_products_name", "vendor_products", ["name"])
    op.create_index("ix_vendor_products_brand", "vendor_products", ["brand"])
    op.create_index("ix_vendor_products_category", "vendor_products", ["category"])
    op.create_index("ix_vendor_products_vendor_id", "vendor_products", ["vendor_id"])
    op.create_index(
        "ix_vendor_products_external_reference", "vendor_products", ["external_reference"]
    )
    op.create_index(
        "ix_vendor_products_source_plugin", "vendor_products", ["source_plugin"]
    )

    op.add_column(
        "job_requirements",
        sa.Column(
            "vendor_product_id",
            sa.Integer(),
            sa.ForeignKey("vendor_products.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_job_requirements_vendor_product_id",
        "job_requirements",
        ["vendor_product_id"],
    )

    op.add_column(
        "job_requirements",
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_requirements", "unit_price")
    op.drop_index("ix_job_requirements_vendor_product_id", table_name="job_requirements")
    op.drop_column("job_requirements", "vendor_product_id")

    op.drop_index("ix_vendor_products_source_plugin", table_name="vendor_products")
    op.drop_index("ix_vendor_products_external_reference", table_name="vendor_products")
    op.drop_index("ix_vendor_products_vendor_id", table_name="vendor_products")
    op.drop_index("ix_vendor_products_category", table_name="vendor_products")
    op.drop_index("ix_vendor_products_brand", table_name="vendor_products")
    op.drop_index("ix_vendor_products_name", table_name="vendor_products")
    op.drop_index("ix_vendor_products_sku", table_name="vendor_products")
    op.drop_table("vendor_products")

    op.alter_column(
        "job_requirements",
        "product_id",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_nullable=True,
    )

    op.drop_column("job_crew_requirements", "hours")
