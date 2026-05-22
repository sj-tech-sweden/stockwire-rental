"""add external identity columns for sso

Revision ID: 20260521_0017
Revises: 20260521_0016
Create Date: 2026-05-21 22:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0017"
down_revision = "20260521_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_source", sa.String(length=50), nullable=False, server_default="local"))
    op.add_column("users", sa.Column("external_provider", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("external_subject", sa.String(length=255), nullable=True))
    op.create_index("ix_users_external_provider", "users", ["external_provider"], unique=False)
    op.create_index("ix_users_external_subject", "users", ["external_subject"], unique=False)
    op.create_unique_constraint("uq_users_external_identity", "users", ["external_provider", "external_subject"])
    op.alter_column("users", "auth_source", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_users_external_identity", "users", type_="unique")
    op.drop_index("ix_users_external_subject", table_name="users")
    op.drop_index("ix_users_external_provider", table_name="users")
    op.drop_column("users", "external_subject")
    op.drop_column("users", "external_provider")
    op.drop_column("users", "auth_source")
