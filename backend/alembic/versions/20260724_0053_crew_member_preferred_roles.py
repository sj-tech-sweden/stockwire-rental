"""crew member preferred roles association table

Revision ID: 20260724_0053
Revises: 20260724_0052
Create Date: 2026-07-24 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0053"
down_revision = "20260724_0052"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crew_member_preferred_roles",
        sa.Column("crew_member_id", sa.Integer(), sa.ForeignKey("crew_members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("crew_role_id", sa.Integer(), sa.ForeignKey("crew_roles.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade():
    op.drop_table("crew_member_preferred_roles")
