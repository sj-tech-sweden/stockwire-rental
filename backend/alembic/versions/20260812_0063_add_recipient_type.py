"""add recipient_type to notification_templates

Revision ID: 0063
Revises: 0062
Create Date: 2026-08-12

"""

from alembic import op
import sqlalchemy as sa

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='notification_templates' AND column_name='recipient_type'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "notification_templates",
            sa.Column("recipient_type", sa.String(20), nullable=False, server_default="both"),
        )


def downgrade() -> None:
    op.drop_column("notification_templates", "recipient_type")
