"""Fix external_origin for persons migrated from legacy customers

Revision ID: 0076
Revises: 0075
Create Date: 2026-08-21

"""

from alembic import op

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Set external_origin to 'stockwire' for all persons that were migrated
    # from legacy customers. This ensures they will be synced to Twenty CRM.
    # Persons that were truly created from Twenty (via inbound sync) will have
    # external_origin set back to 'twenty' when they are synced back.
    op.execute(
        """
        UPDATE persons
        SET external_origin = 'stockwire'
        WHERE external_origin = 'twenty'
          AND external_reference IS NOT NULL
          AND id IN (
              SELECT p.id
              FROM persons p
              JOIN companies c ON c.id = p.company_id
              WHERE c.external_source = 'twenty'
          )
        """
    )


def downgrade() -> None:
    # Revert external_origin back to 'twenty' for persons linked to
    # Twenty-originated companies
    op.execute(
        """
        UPDATE persons
        SET external_origin = 'twenty'
        WHERE external_origin = 'stockwire'
          AND external_reference IS NOT NULL
          AND id IN (
              SELECT p.id
              FROM persons p
              JOIN companies c ON c.id = p.company_id
              WHERE c.external_source = 'twenty'
          )
        """
    )
