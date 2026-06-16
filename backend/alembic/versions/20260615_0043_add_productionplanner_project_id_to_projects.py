"""Add productionplanner_project_id to projects"""

revision = "20260615_0043"
down_revision = "20260615_0042"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("projects", sa.Column("productionplanner_project_id", sa.String(100), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("projects", "productionplanner_project_id")