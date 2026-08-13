"""add is_scannable to job_requirements

Revision ID: 0067
Revises: 0066
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_requirements", sa.Column("is_scannable", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("job_requirements", "is_scannable")
