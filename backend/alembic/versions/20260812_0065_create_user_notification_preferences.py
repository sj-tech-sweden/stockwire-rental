"""create user_notification_preferences table

Revision ID: 0065
Revises: 0064
Create Date: 2026-08-12

NOTE: The `user_notification_preferences` table is now created by migration 0062.
This revision is retained only as a placeholder so the alembic version chain stays
consistent for deployments that already applied it. It must not create or drop the
table.
"""

from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
