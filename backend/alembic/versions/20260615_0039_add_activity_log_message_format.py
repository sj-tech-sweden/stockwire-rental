"""Add message_format and message_params_json to activity_logs"""

revision = "20260615_0039"
down_revision = "20260610_0038"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("activity_logs", sa.Column("message_format", sa.String(80), nullable=True))
    op.add_column("activity_logs", sa.Column("message_params_json", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("activity_logs", "message_params_json")
    op.drop_column("activity_logs", "message_format")
