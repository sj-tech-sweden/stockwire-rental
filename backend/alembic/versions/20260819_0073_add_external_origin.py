"""add external_origin to customers and jobs

Revision ID: 0073
Revises: 0072
Create Date: 2026-08-19

"""

from alembic import op
import sqlalchemy as sa

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("external_origin", sa.String(80), nullable=True))
    op.create_index("ix_customers_external_origin", "customers", ["external_origin"])
    op.add_column("jobs", sa.Column("external_origin", sa.String(80), nullable=True))
    op.create_index("ix_jobs_external_origin", "jobs", ["external_origin"])

    # Records that were first successfully created via an inbound sync are
    # considered Twenty-originated so future outbound syncs don't overwrite
    # data in Twenty.
    op.execute(
        """
        UPDATE customers
        SET external_origin = 'twenty'
        WHERE external_source = 'twenty'
          AND external_origin IS NULL
          AND id IN (
              SELECT DISTINCT ON (entity_id) entity_id
              FROM twenty_sync_log
              WHERE entity_type = 'customer'
                AND direction = 'inbound'
                AND operation = 'create'
                AND status = 'success'
              ORDER BY entity_id, created_at ASC
          )
        """
    )
    op.execute(
        """
        UPDATE jobs
        SET external_origin = 'twenty'
        WHERE external_source = 'twenty'
          AND external_origin IS NULL
          AND id IN (
              SELECT DISTINCT ON (entity_id) entity_id
              FROM twenty_sync_log
              WHERE entity_type = 'job'
                AND direction = 'inbound'
                AND operation = 'create'
                AND status = 'success'
              ORDER BY entity_id, created_at ASC
          )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_external_origin", table_name="jobs")
    op.drop_column("jobs", "external_origin")
    op.drop_index("ix_customers_external_origin", table_name="customers")
    op.drop_column("customers", "external_origin")
