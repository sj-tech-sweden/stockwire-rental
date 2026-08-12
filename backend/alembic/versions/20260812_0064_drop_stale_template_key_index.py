"""drop stale single-column unique index on notification_templates

Revision ID: 0064
Revises: 0063
Create Date: 2026-08-12

NOTE: The stale single-column unique index `ix_notification_templates_template_key`
is now dropped by migration 0062. This revision is retained only as a placeholder
so the alembic version chain stays consistent for deployments that already applied
it. It must not recreate the index/constraint.
"""

from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
