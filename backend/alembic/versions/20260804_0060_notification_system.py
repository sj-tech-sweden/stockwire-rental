"""notification system

Revision ID: 20260804_0060
Revises: 20260802_0059
Create Date: 2026-08-04 04:50:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260804_0060"
down_revision = "20260802_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "jobs",
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("notification_channel", sa.String(length=20), nullable=False, server_default="both"),
    )
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=1000), nullable=False),
        sa.Column("p256dh_key", sa.String(length=255), nullable=False),
        sa.Column("auth_key", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index(op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"], unique=False)
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("subject_template", sa.String(length=255), nullable=True),
        sa.Column("html_template", sa.Text(), nullable=True),
        sa.Column("text_template", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_templates_template_key"),
        "notification_templates",
        ["template_key"],
        unique=True,
    )
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("recipient_type", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_logs_job_id"), "notification_logs", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_notification_logs_recipient_id"),
        "notification_logs",
        ["recipient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_template_key"),
        "notification_logs",
        ["template_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_logs_template_key"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_recipient_id"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_job_id"), table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_index(op.f("ix_notification_templates_template_key"), table_name="notification_templates")
    op.drop_table("notification_templates")
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_column("users", "notification_channel")
    op.drop_column("jobs", "email_notifications_enabled")
    op.drop_column("customers", "email_notifications_enabled")
