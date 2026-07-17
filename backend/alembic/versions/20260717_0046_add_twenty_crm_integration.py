"""add twenty crm integration tables and external ids

Revision ID: 20260717_0046
Revises: 20260715_0045
Create Date: 2026-07-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0046"
down_revision = "20260715_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "twenty_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(500), server_default="https://api.twenty.com"),
        sa.Column("workspace_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "twenty_sync_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("direction", sa.String(20), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("entity_id", sa.Integer(), nullable=True, index=True),
        sa.Column("twenty_id", sa.String(100), nullable=True, index=True),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("customers", sa.Column("external_source", sa.String(80), nullable=True, index=True))
    op.add_column("customers", sa.Column("external_reference", sa.String(120), nullable=True, index=True))
    op.add_column("jobs", sa.Column("external_source", sa.String(80), nullable=True, index=True))
    op.add_column("jobs", sa.Column("external_reference", sa.String(120), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("jobs", "external_reference")
    op.drop_column("jobs", "external_source")
    op.drop_column("customers", "external_reference")
    op.drop_column("customers", "external_source")
    op.drop_table("twenty_sync_log")
    op.drop_table("twenty_config")
