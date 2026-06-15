"""Add venue_id to projects"""

revision = "20260615_0041"
down_revision = "20260615_0040"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("projects", sa.Column("venue_id", sa.Integer, sa.ForeignKey("venues.id"), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("projects", "venue_id")
