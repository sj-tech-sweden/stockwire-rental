"""Add projects table and project_id + location_in_venue to jobs"""

revision = "20260615_0040"
down_revision = "20260615_0039"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=True, index=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), default="active", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.add_column("jobs", sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True, index=True))
    op.add_column("jobs", sa.Column("location_in_venue", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "location_in_venue")
    op.drop_column("jobs", "project_id")
    op.drop_table("projects")
