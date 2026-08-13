"""add twenty_person_id and twenty_rental_job_id

Revision ID: 0068
Revises: 0067
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("twenty_person_id", sa.String(100), nullable=True))
    op.create_index("ix_customers_twenty_person_id", "customers", ["twenty_person_id"])
    op.add_column("jobs", sa.Column("twenty_rental_job_id", sa.String(100), nullable=True))
    op.create_index("ix_jobs_twenty_rental_job_id", "jobs", ["twenty_rental_job_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_twenty_rental_job_id", table_name="jobs")
    op.drop_column("jobs", "twenty_rental_job_id")
    op.drop_index("ix_customers_twenty_person_id", table_name="customers")
    op.drop_column("customers", "twenty_person_id")
