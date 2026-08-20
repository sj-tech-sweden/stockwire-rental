"""Company/Person entity split - Phase 1

This migration creates the new companies and persons tables, migrates existing
customer data, and adds new foreign key columns to jobs, crew_members, and
product_suppliers tables.

Revision ID: 0074
Revises: 0073
Create Date: 2026-08-20

"""

from alembic import op
import sqlalchemy as sa

revision = "0074"
down_revision = "f55323ecd157"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create companies table
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Twenty CRM sync fields
        sa.Column("external_source", sa.String(80), nullable=True, index=True),
        sa.Column("external_reference", sa.String(120), nullable=True, index=True),
        sa.Column("external_origin", sa.String(80), nullable=True, index=True),
        # Business classification
        sa.Column("is_customer", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_product_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_rental_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_crew_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Notification preferences
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preferred_language", sa.String(10), nullable=True, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )

    # 2. Create persons table
    op.create_table(
        "persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(150), nullable=False, index=True),
        sa.Column("last_name", sa.String(150), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Foreign key to Company (nullable for B2C standalone persons)
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # Twenty CRM sync fields
        sa.Column("external_source", sa.String(80), nullable=True, index=True),
        sa.Column("external_reference", sa.String(120), nullable=True, index=True),
        sa.Column("external_origin", sa.String(80), nullable=True, index=True),
        # Notification preferences
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preferred_language", sa.String(10), nullable=True, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )

    # 3. Migrate existing customer data to companies
    op.execute(
        """
        INSERT INTO companies (
            name, address, city, postal_code, country, notes,
            external_source, external_reference, external_origin,
            is_customer, is_product_supplier, is_rental_supplier, is_crew_supplier,
            email_notifications_enabled, preferred_language, created_at
        )
        SELECT
            name, address, city, postal_code, country, notes,
            external_source, external_reference, external_origin,
            is_customer, is_product_supplier, is_rental_supplier, is_crew_supplier,
            email_notifications_enabled, preferred_language, created_at
        FROM customers
        """
    )

    # 4. Create default persons from customer names
    # Parse name into first_name/last_name for a default Person linked to the Company
    op.execute(
        """
        INSERT INTO persons (
            first_name, last_name, email, phone, company_id,
            external_source, external_reference, external_origin,
            email_notifications_enabled, preferred_language, created_at
        )
        SELECT
            SPLIT_PART(c.name, ' ', 1) AS first_name,
            CASE
                WHEN ARRAY_LENGTH(STRING_TO_ARRAY(c.name, ' '), 1) > 1
                THEN SUBSTRING(c.name FROM POSITION(' ' IN c.name) + 1)
                ELSE ''
            END AS last_name,
            c.email,
            c.phone,
            comp.id AS company_id,
            c.external_source,
            c.external_reference,
            c.external_origin,
            c.email_notifications_enabled,
            c.preferred_language,
            c.created_at
        FROM customers c
        JOIN companies comp ON comp.name = c.name
        """
    )

    # 5. Add new FK columns to jobs table
    op.add_column(
        "jobs",
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])

    op.add_column(
        "jobs",
        sa.Column(
            "contact_person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_jobs_contact_person_id", "jobs", ["contact_person_id"])

    # 6. Populate company_id from customer_id mapping
    op.execute(
        """
        UPDATE jobs
        SET company_id = comp.id
        FROM companies comp
        WHERE comp.name = (
            SELECT c.name FROM customers c WHERE c.id = jobs.customer_id
        )
        """
    )

    # 7. Populate contact_person_id from the default person for each company
    op.execute(
        """
        UPDATE jobs
        SET contact_person_id = (
            SELECT p.id FROM persons p
            WHERE p.company_id = jobs.company_id
            LIMIT 1
        )
        """
    )

    # 8. Add person_id to crew_members
    op.add_column(
        "crew_members",
        sa.Column(
            "person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_crew_members_person_id", "crew_members", ["person_id"])

    # 9. Add supplier_company_id to product_suppliers
    op.add_column(
        "product_suppliers",
        sa.Column(
            "supplier_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_product_suppliers_supplier_company_id", "product_suppliers", ["supplier_company_id"])

    # 10. Populate supplier_company_id from supplier_id mapping
    op.execute(
        """
        UPDATE product_suppliers
        SET supplier_company_id = comp.id
        FROM companies comp
        WHERE comp.name = (
            SELECT c.name FROM customers c WHERE c.id = product_suppliers.supplier_id
        )
        """
    )

    # 11. Add company_id to projects
    op.add_column(
        "projects",
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_projects_company_id", "projects", ["company_id"])

    # 12. Populate company_id from customer_id mapping
    op.execute(
        """
        UPDATE projects
        SET company_id = comp.id
        FROM companies comp
        WHERE comp.name = (
            SELECT c.name FROM customers c WHERE c.id = projects.customer_id
        )
        """
    )


def downgrade() -> None:
    # Drop new indexes and columns in reverse order
    op.drop_index("ix_projects_company_id", table_name="projects")
    op.drop_column("projects", "company_id")

    op.drop_index("ix_product_suppliers_supplier_company_id", table_name="product_suppliers")
    op.drop_column("product_suppliers", "supplier_company_id")

    op.drop_index("ix_crew_members_person_id", table_name="crew_members")
    op.drop_column("crew_members", "person_id")

    op.drop_index("ix_jobs_contact_person_id", table_name="jobs")
    op.drop_column("jobs", "contact_person_id")
    op.drop_index("ix_jobs_company_id", table_name="jobs")
    op.drop_column("jobs", "company_id")

    op.drop_table("persons")
    op.drop_table("companies")
