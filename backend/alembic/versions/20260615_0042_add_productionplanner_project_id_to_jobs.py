"""Add productionplanner_project_id to jobs"""

revision = "20260615_0042"
down_revision = "20260615_0041"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("jobs", sa.Column("productionplanner_project_id", sa.String(100), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("jobs", "productionplanner_project_id")