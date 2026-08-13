"""add webhook_secret and schema_provisioned to twenty_config

Revision ID: 0069
Revises: 0068
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("twenty_config", sa.Column("webhook_secret", sa.Text(), nullable=True))
    op.add_column("twenty_config", sa.Column("schema_provisioned", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("twenty_config", "schema_provisioned")
    op.drop_column("twenty_config", "webhook_secret")
