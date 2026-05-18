"""add role column to users

Revision ID: 20250518_0002
Revises: 20250518_0001
Create Date: 2026-05-18 14:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20250518_0002"
down_revision = "20250518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=50), nullable=False, server_default="viewer"),
    )
    # Update any existing admin users so their role matches is_admin
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = TRUE")


def downgrade() -> None:
    op.drop_column("users", "role")
