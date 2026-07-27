"""create calendar_feeds table

Revision ID: 20260727_0054
Revises: 20260724_0053
Create Date: 2026-07-27 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0054"
down_revision = "20260724_0053"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_feeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("feed_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("calendar_feeds")
