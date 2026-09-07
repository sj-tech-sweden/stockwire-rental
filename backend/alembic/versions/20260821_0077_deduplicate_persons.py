"""Deduplicate persons that were created from companies during migration

Revision ID: 0077
Revises: 0076
Create Date: 2026-08-21

"""

from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove duplicate persons that were created from companies during migration.
    # Keep the person with the lowest id for each (first_name, last_name, company_id) combination.
    op.execute(
        """
        DELETE FROM persons
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                    ROW_NUMBER() OVER (
                        PARTITION BY first_name, last_name, company_id
                        ORDER BY id ASC
                    ) as rn
                FROM persons
            ) t
            WHERE rn > 1
        )
        """
    )

    # Also clear external_reference for persons that don't have a valid Twenty company
    # This ensures they will be recreated in Twenty on next sync
    op.execute(
        """
        UPDATE persons
        SET external_reference = NULL, external_source = NULL
        WHERE external_reference IS NOT NULL
          AND company_id IS NOT NULL
          AND company_id NOT IN (
              SELECT id FROM companies WHERE external_reference IS NOT NULL
          )
        """
    )


def downgrade() -> None:
    # No rollback needed - deduplication is destructive and can't be undone
    pass
