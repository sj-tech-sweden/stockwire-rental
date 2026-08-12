"""drop stale single-column unique index on notification_templates

Revision ID: 0064
Revises: 0063
Create Date: 2026-08-12

"""

from alembic import op
import sqlalchemy as sa

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname='ix_notification_templates_template_key'")
    )
    if result.fetchone():
        op.drop_index("ix_notification_templates_template_key", table_name="notification_templates")


def downgrade() -> None:
    op.create_unique_constraint(
        "ix_notification_templates_template_key",
        "notification_templates",
        ["template_key"],
    )
