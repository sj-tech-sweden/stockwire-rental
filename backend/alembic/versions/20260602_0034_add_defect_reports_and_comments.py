"""add defect reports and comments

Revision ID: 20260602_0034
Revises: 20260602_0033
Create Date: 2026-06-02 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_0034"
down_revision = "20260602_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "defect_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("maintenance_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maintenance_id"], ["device_maintenance.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_defect_reports_created_at"), "defect_reports", ["created_at"], unique=False)
    op.create_index(op.f("ix_defect_reports_created_by_user_id"), "defect_reports", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_defect_reports_device_id"), "defect_reports", ["device_id"], unique=False)
    op.create_index(op.f("ix_defect_reports_maintenance_id"), "defect_reports", ["maintenance_id"], unique=False)
    op.create_index(op.f("ix_defect_reports_severity"), "defect_reports", ["severity"], unique=False)
    op.create_index(op.f("ix_defect_reports_status"), "defect_reports", ["status"], unique=False)

    op.create_table(
        "defect_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defect_report_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["defect_report_id"], ["defect_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_defect_comments_created_at"), "defect_comments", ["created_at"], unique=False)
    op.create_index(op.f("ix_defect_comments_created_by_user_id"), "defect_comments", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_defect_comments_defect_report_id"), "defect_comments", ["defect_report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_defect_comments_defect_report_id"), table_name="defect_comments")
    op.drop_index(op.f("ix_defect_comments_created_by_user_id"), table_name="defect_comments")
    op.drop_index(op.f("ix_defect_comments_created_at"), table_name="defect_comments")
    op.drop_table("defect_comments")

    op.drop_index(op.f("ix_defect_reports_status"), table_name="defect_reports")
    op.drop_index(op.f("ix_defect_reports_severity"), table_name="defect_reports")
    op.drop_index(op.f("ix_defect_reports_maintenance_id"), table_name="defect_reports")
    op.drop_index(op.f("ix_defect_reports_device_id"), table_name="defect_reports")
    op.drop_index(op.f("ix_defect_reports_created_by_user_id"), table_name="defect_reports")
    op.drop_index(op.f("ix_defect_reports_created_at"), table_name="defect_reports")
    op.drop_table("defect_reports")
