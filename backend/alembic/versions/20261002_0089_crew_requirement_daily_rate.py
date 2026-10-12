"""crew requirement daily rate basis

Revision ID: 0089
Revises: 0088
Create Date: 2026-10-02

Adds a daily-rate billing basis to job crew requirements so events can be
priced per day instead of per hour.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "0089"
down_revision = "0088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_crew_requirements",
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "job_crew_requirements",
        sa.Column("rate_basis", sa.String(10), nullable=False, server_default="hourly"),
    )
    op.add_column(
        "job_crew_requirements",
        sa.Column("days", sa.Numeric(10, 2), nullable=True),
    )
    op.alter_column("job_crew_requirements", "rate_basis", server_default=None)


def downgrade() -> None:
    op.drop_column("job_crew_requirements", "days")
    op.drop_column("job_crew_requirements", "rate_basis")
    op.drop_column("job_crew_requirements", "daily_rate")
