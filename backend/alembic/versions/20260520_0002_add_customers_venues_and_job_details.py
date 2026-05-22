"""add customers, venues, and richer job fields

Revision ID: 20260520_0002
Revises: 20250518_0001
Create Date: 2026-05-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0002"
down_revision = "20250518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_name", "customers", ["name"], unique=False)
    op.create_index("ix_customers_email", "customers", ["email"], unique=False)

    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_venues_name", "venues", ["name"], unique=False)
    op.create_index("ix_venues_city", "venues", ["city"], unique=False)

    op.add_column("jobs", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("venue_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("venue_name", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("notes", sa.Text(), nullable=True))
    op.alter_column("jobs", "customer_name", existing_type=sa.String(length=255), nullable=True)
    op.create_index("ix_jobs_customer_id", "jobs", ["customer_id"], unique=False)
    op.create_index("ix_jobs_venue_id", "jobs", ["venue_id"], unique=False)
    op.create_index("ix_jobs_venue_name", "jobs", ["venue_name"], unique=False)

    op.create_foreign_key("fk_jobs_customer_id_customers", "jobs", "customers", ["customer_id"], ["id"])
    op.create_foreign_key("fk_jobs_venue_id_venues", "jobs", "venues", ["venue_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_venue_id_venues", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_customer_id_customers", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_venue_name", table_name="jobs")
    op.drop_index("ix_jobs_venue_id", table_name="jobs")
    op.drop_index("ix_jobs_customer_id", table_name="jobs")
    op.alter_column("jobs", "customer_name", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("jobs", "notes")
    op.drop_column("jobs", "description")
    op.drop_column("jobs", "venue_name")
    op.drop_column("jobs", "venue_id")
    op.drop_column("jobs", "customer_id")

    op.drop_index("ix_venues_city", table_name="venues")
    op.drop_index("ix_venues_name", table_name="venues")
    op.drop_table("venues")

    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_table("customers")