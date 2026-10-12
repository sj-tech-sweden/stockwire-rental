"""crew role default hourly/daily rates

Revision ID: 0087
Revises: 0086
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crew_roles",
        sa.Column("default_hourly_rate", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "crew_roles",
        sa.Column("default_daily_rate", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crew_roles", "default_daily_rate")
    op.drop_column("crew_roles", "default_hourly_rate")
