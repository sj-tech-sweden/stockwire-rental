"""add maintenance comments

Revision ID: 20260602_0035
Revises: 20260602_0034
Create Date: 2026-06-02 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_0035"
down_revision = "20260602_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("maintenance_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["maintenance_id"], ["device_maintenance.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_maintenance_comments_created_at"), "maintenance_comments", ["created_at"], unique=False)
    op.create_index(op.f("ix_maintenance_comments_created_by_user_id"), "maintenance_comments", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_maintenance_comments_maintenance_id"), "maintenance_comments", ["maintenance_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_maintenance_comments_maintenance_id"), table_name="maintenance_comments")
    op.drop_index(op.f("ix_maintenance_comments_created_by_user_id"), table_name="maintenance_comments")
    op.drop_index(op.f("ix_maintenance_comments_created_at"), table_name="maintenance_comments")
    op.drop_table("maintenance_comments")
