"""add notification system and customer language preference

Revision ID: 0062
Revises: 0061
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check and add preferred_language to customers
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='customers' AND column_name='preferred_language'"))
    if not result.fetchone():
        op.add_column("customers", sa.Column("preferred_language", sa.String(10), nullable=True, server_default="en"))

    # Check and add locale to notification_templates
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='notification_templates' AND column_name='locale'"))
    if not result.fetchone():
        op.add_column("notification_templates", sa.Column("locale", sa.String(10), nullable=False, server_default="en"))

    # Check and add is_enabled
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='notification_templates' AND column_name='is_enabled'"))
    if not result.fetchone():
        op.add_column("notification_templates", sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # Check and add recipient_type
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='notification_templates' AND column_name='recipient_type'"))
    if not result.fetchone():
        op.add_column("notification_templates", sa.Column("recipient_type", sa.String(20), nullable=False, server_default="both"))

    # Check and add updated_at
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='notification_templates' AND column_name='updated_at'"))
    if not result.fetchone():
        op.add_column("notification_templates", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    # Drop old single-column unique index if exists (it is an index, not a constraint)
    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname='ix_notification_templates_template_key'"))
    if result.fetchone():
        op.drop_index("ix_notification_templates_template_key", table_name="notification_templates")

    # Create composite unique if not exists
    result = conn.execute(sa.text("SELECT conname FROM pg_constraint WHERE conname='uq_template_key_locale'"))
    if not result.fetchone():
        op.create_unique_constraint("uq_template_key_locale", "notification_templates", ["template_key", "locale"])

    # Add locale to notification_logs
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='notification_logs' AND column_name='locale'"))
    if not result.fetchone():
        op.add_column("notification_logs", sa.Column("locale", sa.String(10), nullable=True))

    # Create notification_preferences table
    result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='notification_preferences')"))
    if not result.fetchone()[0]:
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_type", sa.String(80), nullable=False, unique=True, index=True),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("web_push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Create user_notification_preferences table
    result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='user_notification_preferences')"))
    if not result.fetchone()[0]:
        op.create_table(
            "user_notification_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("event_type", sa.String(80), nullable=False, index=True),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("web_push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "event_type", name="uq_user_notification_event"),
        )


def downgrade() -> None:
    op.drop_table("user_notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_constraint("uq_template_key_locale", "notification_templates", type_="unique")
    op.create_unique_constraint("ix_notification_templates_template_key", "notification_templates", ["template_key"])
    op.drop_column("notification_templates", "updated_at")
    op.drop_column("notification_templates", "recipient_type")
    op.drop_column("notification_templates", "is_enabled")
    op.drop_column("notification_templates", "locale")
    op.drop_column("notification_logs", "locale")
    op.drop_column("customers", "preferred_language")
