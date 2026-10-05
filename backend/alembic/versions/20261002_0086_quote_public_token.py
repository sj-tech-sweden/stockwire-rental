"""quote twenty sync flag and public asset token

Revision ID: 0086
Revises: 0085
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("quote_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "asset_files",
        sa.Column("public_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_asset_files_public_token", "asset_files", ["public_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_asset_files_public_token", table_name="asset_files")
    op.drop_column("asset_files", "public_token")
    op.drop_column("jobs", "quote_synced_at")
