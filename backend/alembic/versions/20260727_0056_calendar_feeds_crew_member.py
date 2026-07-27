"""add crew_member_id to calendar_feeds

Revision ID: 20260727_0056
Revises: 20260727_0055
Create Date: 2026-07-27 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0056"
down_revision = "20260727_0055"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "calendar_feeds",
        sa.Column("crew_member_id", sa.Integer(), sa.ForeignKey("crew_members.id"), nullable=True, index=True),
    )


def downgrade():
    op.drop_column("calendar_feeds", "crew_member_id")
