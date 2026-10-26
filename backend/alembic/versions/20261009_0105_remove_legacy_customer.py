"""Remove the legacy customers table and its foreign keys.

This completes the Company/Person migration that began in 0074/0075. The new
``companies``-based columns (jobs.company_id, projects.company_id,
product_suppliers.supplier_company_id, crew_members.supplier_id) were already
populated by 0074/0075, so this migration:

  * remaps product_suppliers.supplier_id from the already-correct
    supplier_company_id (no ambiguous name matching), then drops the redundant
    supplier_company_id column,
  * adds devices.supplier_company_id, backfills it by customer->company name
    matching (the same approach used in 0074/0075), drops the legacy
    devices.supplier_id column and renames supplier_company_id -> supplier_id,
    keeping supplier_id as the (companies) FK column,
  * drops the leftover jobs.customer_id and projects.customer_id columns,
  * drops the now-unused customers table.

Revision ID: 0105
Revises: 0104
Create Date: 2026-10-22

"""

from alembic import op
import sqlalchemy as sa


revision = "0105"
down_revision = "0104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. product_suppliers: supplier_id keeps its column name but must point at
    #    companies. supplier_company_id was already populated by 0074, so copy it
    #    across (exact, no name matching) and drop the redundant column. Remove
    #    the old customers FK before copying company IDs into supplier_id.
    op.drop_constraint("product_suppliers_supplier_id_fkey", "product_suppliers", type_="foreignkey")
    op.execute(
        """
        UPDATE product_suppliers
        SET supplier_id = supplier_company_id
        WHERE supplier_company_id IS NOT NULL
        """
    )
    op.drop_constraint(
        "product_suppliers_supplier_company_id_fkey", "product_suppliers", type_="foreignkey"
    )
    op.drop_index("ix_product_suppliers_supplier_company_id", table_name="product_suppliers")
    op.drop_column("product_suppliers", "supplier_company_id")

    op.create_foreign_key(
        "product_suppliers_supplier_id_fkey",
        "product_suppliers",
        "companies",
        ["supplier_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. devices: add supplier_company_id, backfill by name, then swap the column
    #    name so supplier_id remains the (companies) FK column.
    op.add_column(
        "devices",
        sa.Column(
            "supplier_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_devices_supplier_company_id", "devices", ["supplier_company_id"])

    op.execute(
        """
        UPDATE devices
        SET supplier_company_id = comp.id
        FROM companies comp
        WHERE comp.name = (
            SELECT c.name FROM customers c WHERE c.id = devices.supplier_id
        )
        """
    )

    op.drop_index("ix_devices_supplier_id", table_name="devices")
    op.drop_constraint("devices_supplier_id_fkey", "devices", type_="foreignkey")
    op.drop_column("devices", "supplier_id")

    op.alter_column("devices", "supplier_company_id", new_column_name="supplier_id")
    op.drop_index("ix_devices_supplier_company_id", table_name="devices")
    op.create_index("ix_devices_supplier_id", "devices", ["supplier_id"])

    # 3. Drop the leftover legacy customer_id columns on jobs and projects. Their
    #    companies-based replacements (company_id) were populated by 0074.
    op.drop_constraint("jobs_customer_id_fkey", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_customer_id", table_name="jobs")
    op.drop_column("jobs", "customer_id")

    op.drop_constraint("projects_customer_id_fkey", "projects", type_="foreignkey")
    op.drop_index("ix_projects_customer_id", table_name="projects")
    op.drop_column("projects", "customer_id")

    # 4. The customers table is no longer referenced by any model.
    op.drop_table("customers")


def downgrade() -> None:
    # Recreate the customers table (minimal shape; historical migrations are the
    # source of truth for full fidelity).
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_source", sa.String(80), nullable=True, index=True),
        sa.Column("external_reference", sa.String(120), nullable=True, index=True),
        sa.Column("external_origin", sa.String(80), nullable=True, index=True),
        sa.Column("twenty_person_id", sa.String(100), nullable=True, index=True),
        sa.Column("is_customer", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_product_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_rental_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_crew_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preferred_language", sa.String(10), nullable=True, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Restore the legacy columns and FKs.
    op.add_column("jobs", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_index("ix_jobs_customer_id", "jobs", ["customer_id"])
    op.create_foreign_key("jobs_customer_id_fkey", "jobs", "customers", ["customer_id"], ["id"], ondelete="SET NULL")

    op.add_column("projects", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_index("ix_projects_customer_id", "projects", ["customer_id"])
    op.create_foreign_key("projects_customer_id_fkey", "projects", "customers", ["customer_id"], ["id"], ondelete="SET NULL")

    # devices: rename supplier_id back to supplier_company_id, restore old supplier_id.
    op.drop_index("ix_devices_supplier_id", table_name="devices")
    op.alter_column("devices", "supplier_id", new_column_name="supplier_company_id")
    op.create_index("ix_devices_supplier_company_id", "devices", ["supplier_company_id"])

    op.add_column("devices", sa.Column("supplier_id", sa.Integer(), nullable=True))
    op.create_index("ix_devices_supplier_id", "devices", ["supplier_id"])
    op.create_foreign_key("devices_supplier_id_fkey", "devices", "customers", ["supplier_id"], ["id"], ondelete="SET NULL")
    op.execute(
        """
        UPDATE devices
        SET supplier_id = c.id
        FROM customers c
        WHERE c.name = (
            SELECT comp.name FROM companies comp WHERE comp.id = devices.supplier_company_id
        )
        """
    )
    op.drop_index("ix_devices_supplier_company_id", table_name="devices")
    op.drop_column("devices", "supplier_company_id")

    # product_suppliers: restore supplier_company_id and repoint supplier_id to customers.
    op.drop_constraint("product_suppliers_supplier_id_fkey", "product_suppliers", type_="foreignkey")
    op.add_column(
        "product_suppliers",
        sa.Column("supplier_company_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_product_suppliers_supplier_company_id", "product_suppliers", ["supplier_company_id"])
    op.create_foreign_key(
        "product_suppliers_supplier_company_id_fkey",
        "product_suppliers",
        "companies",
        ["supplier_company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE product_suppliers
        SET supplier_company_id = supplier_id
        WHERE supplier_id IS NOT NULL
        """
    )
    op.create_foreign_key(
        "product_suppliers_supplier_id_fkey",
        "product_suppliers",
        "customers",
        ["supplier_id"],
        ["id"],
        ondelete="CASCADE",
    )
