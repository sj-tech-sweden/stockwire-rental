"""phase 1 core domain tables

Revision ID: 20250518_0001
Revises: 
Create Date: 2026-05-18 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20250518_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_name", "products", ["name"], unique=False)

    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("zone_type", sa.String(length=50), nullable=False, server_default="rack"),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=True),
    )
    op.create_index("ix_zones_code", "zones", ["code"], unique=True)
    op.create_index("ix_zones_parent_id", "zones", ["parent_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_code", sa.String(length=50), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_job_code", "jobs", ["job_code"], unique=True)
    op.create_index("ix_jobs_customer_name", "jobs", ["customer_name"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_owner_id", "jobs", ["owner_id"], unique=False)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("asset_tag", sa.String(length=64), nullable=False),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="available"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_devices_product_id", "devices", ["product_id"], unique=False)
    op.create_index("ix_devices_asset_tag", "devices", ["asset_tag"], unique=True)
    op.create_index("ix_devices_status", "devices", ["status"], unique=False)

    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity_required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quantity_picked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_job_requirements_job_id", "job_requirements", ["job_id"], unique=False)
    op.create_index("ix_job_requirements_product_id", "job_requirements", ["product_id"], unique=False)

    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("transaction_type", sa.String(length=50), nullable=False, server_default="payment"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="SEK"),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_financial_transactions_job_id", "financial_transactions", ["job_id"], unique=False)
    op.create_index("ix_financial_transactions_transaction_type", "financial_transactions", ["transaction_type"], unique=False)
    op.create_index("ix_financial_transactions_status", "financial_transactions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_financial_transactions_status", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_transaction_type", table_name="financial_transactions")
    op.drop_index("ix_financial_transactions_job_id", table_name="financial_transactions")
    op.drop_table("financial_transactions")

    op.drop_index("ix_job_requirements_product_id", table_name="job_requirements")
    op.drop_index("ix_job_requirements_job_id", table_name="job_requirements")
    op.drop_table("job_requirements")

    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_index("ix_devices_asset_tag", table_name="devices")
    op.drop_index("ix_devices_product_id", table_name="devices")
    op.drop_table("devices")

    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_customer_name", table_name="jobs")
    op.drop_index("ix_jobs_job_code", table_name="jobs")
    op.drop_index("ix_jobs_owner_id", table_name="jobs", if_exists=True)
    op.drop_table("jobs")

    op.drop_index("ix_zones_parent_id", table_name="zones")
    op.drop_index("ix_zones_code", table_name="zones")
    op.drop_table("zones")

    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
