"""Migrate crew_members.supplier_id from customers to companies

Revision ID: 0075
Revises: 0074
Create Date: 2026-08-21

"""

from alembic import op
import sqlalchemy as sa

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new supplier_company_id column
    op.add_column(
        "crew_members",
        sa.Column(
            "supplier_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_crew_members_supplier_company_id", "crew_members", ["supplier_company_id"])

    # Migrate data from supplier_id (customers) to supplier_company_id (companies)
    # Match by customer name = company name
    op.execute(
        """
        UPDATE crew_members
        SET supplier_company_id = comp.id
        FROM companies comp
        WHERE comp.name = (
            SELECT c.name FROM customers c WHERE c.id = crew_members.supplier_id
        )
        """
    )

    # Drop old supplier_id column and its index
    op.drop_index("ix_crew_members_supplier_id", table_name="crew_members")
    op.drop_constraint("crew_members_supplier_id_fkey", "crew_members", type_="foreignkey")
    op.drop_column("crew_members", "supplier_id")

    # Rename supplier_company_id to supplier_id
    op.alter_column("crew_members", "supplier_company_id", new_column_name="supplier_id")
    op.drop_index("ix_crew_members_supplier_company_id", table_name="crew_members")
    op.create_index("ix_crew_members_supplier_id", "crew_members", ["supplier_id"])


def downgrade() -> None:
    # Reverse: rename supplier_id back to supplier_company_id
    op.drop_index("ix_crew_members_supplier_id", table_name="crew_members")
    op.alter_column("crew_members", "supplier_id", new_column_name="supplier_company_id")
    op.create_index("ix_crew_members_supplier_company_id", "crew_members", ["supplier_company_id"])

    # Add back old supplier_id column pointing to customers
    op.add_column(
        "crew_members",
        sa.Column(
            "supplier_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_crew_members_supplier_id", "crew_members", ["supplier_id"])

    # Migrate data back (best effort by name matching)
    op.execute(
        """
        UPDATE crew_members
        SET supplier_id = c.id
        FROM customers c
        WHERE c.name = (
            SELECT comp.name FROM companies comp WHERE comp.id = crew_members.supplier_company_id
        )
        """
    )

    op.drop_index("ix_crew_members_supplier_company_id", table_name="crew_members")
    op.drop_column("crew_members", "supplier_company_id")
