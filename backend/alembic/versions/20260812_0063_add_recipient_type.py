"""add recipient_type to notification_templates

Revision ID: 0063
Revises: 0062
Create Date: 2026-08-12

NOTE: This revision previously added the `recipient_type` column, but that column
is now created by migration 0062. It is retained only as a placeholder so the
alembic version chain stays consistent for deployments that already applied it.
It must not re-create or drop the column.
"""

from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
