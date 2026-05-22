"""Add asset files table for storage backends.

Revision ID: 20260521_0018
Revises: 20260521_0017
Create Date: 2026-05-21 19:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260521_0018"
down_revision: str | Sequence[str] | None = "20260521_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_backend", sa.String(length=20), nullable=False, server_default="local"),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_asset_files_entity_type"), "asset_files", ["entity_type"], unique=False)
    op.create_index(op.f("ix_asset_files_entity_id"), "asset_files", ["entity_id"], unique=False)
    op.create_index(op.f("ix_asset_files_category"), "asset_files", ["category"], unique=False)
    op.create_index(op.f("ix_asset_files_storage_key"), "asset_files", ["storage_key"], unique=True)
    op.create_index(op.f("ix_asset_files_created_by_user_id"), "asset_files", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_asset_files_is_deleted"), "asset_files", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_files_is_deleted"), table_name="asset_files")
    op.drop_index(op.f("ix_asset_files_created_by_user_id"), table_name="asset_files")
    op.drop_index(op.f("ix_asset_files_storage_key"), table_name="asset_files")
    op.drop_index(op.f("ix_asset_files_category"), table_name="asset_files")
    op.drop_index(op.f("ix_asset_files_entity_id"), table_name="asset_files")
    op.drop_index(op.f("ix_asset_files_entity_type"), table_name="asset_files")
    op.drop_table("asset_files")
