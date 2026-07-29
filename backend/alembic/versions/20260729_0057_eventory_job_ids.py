"""add eventory_job_ids to jobs

Revision ID: 20260729_0057
Revises: 20260727_0056
Create Date: 2026-07-29 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260729_0057"
down_revision = "20260727_0056"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "jobs",
        sa.Column("eventory_job_ids", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("jobs", "eventory_job_ids")
