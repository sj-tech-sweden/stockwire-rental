"""supplier management: customer supplier flags, product_suppliers, reorder fields, crew fields, device supplier

Revision ID: 20260723_0051
Revises: 20260717_0050
Create Date: 2026-07-23 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0051"
down_revision = "20260717_0050"
branch_labels = None
depends_on = None


def upgrade():
    # --- Customer supplier flags ---
    op.add_column("customers", sa.Column("is_customer", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("customers", sa.Column("is_product_supplier", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("customers", sa.Column("is_rental_supplier", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("customers", sa.Column("is_crew_supplier", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # --- Product supplier join table ---
    op.create_table(
        "product_suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
    )

    # --- Product reorder fields (consumables only) ---
    op.add_column("products", sa.Column("min_stock_level", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("min_order_qty", sa.Integer(), nullable=True))

    # --- Product crew fields ---
    op.add_column("products", sa.Column("crew_skills", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("crew_certifications", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("crew_rate_type", sa.String(20), nullable=True))
    op.add_column("products", sa.Column("crew_hourly_rate", sa.Numeric(10, 2), nullable=True))

    # --- Device supplier FK ---
    op.add_column("devices", sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True))


def downgrade():
    op.drop_column("devices", "supplier_id")
    op.drop_column("products", "crew_hourly_rate")
    op.drop_column("products", "crew_rate_type")
    op.drop_column("products", "crew_certifications")
    op.drop_column("products", "crew_skills")
    op.drop_column("products", "min_order_qty")
    op.drop_column("products", "min_stock_level")
    op.drop_table("product_suppliers")
    op.drop_column("customers", "is_crew_supplier")
    op.drop_column("customers", "is_rental_supplier")
    op.drop_column("customers", "is_product_supplier")
    op.drop_column("customers", "is_customer")
