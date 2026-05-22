"""add rbac, sessions and api_keys

Revision ID: 20260518_0003
Revises: 20250518_0002
Create Date: 2026-05-18 14:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_0003"
down_revision = "20250518_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # User roles mapping
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Sessions table for server-side sessions
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # API keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Insert default roles and migrate existing users.role values into user_roles
    conn = op.get_bind()
    # Create default roles
    conn.execute(sa.text("INSERT INTO roles (name, display_name, permissions) VALUES ('admin','Administrator','[]') ON CONFLICT DO NOTHING;"))
    conn.execute(sa.text("INSERT INTO roles (name, display_name, permissions) VALUES ('manager','Manager','[]') ON CONFLICT DO NOTHING;"))
    conn.execute(sa.text("INSERT INTO roles (name, display_name, permissions) VALUES ('viewer','Viewer','[]') ON CONFLICT DO NOTHING;"))

    # Migrate existing users.role into user_roles (best-effort; users.role may be absent on very old schemas)
    try:
        conn.execute(sa.text(
            "INSERT INTO user_roles (user_id, role_id, is_active, created_at) "
            "SELECT u.id, r.id, true, now() FROM users u JOIN roles r ON r.name = u.role WHERE u.role IS NOT NULL;"
        ))
    except Exception:
        # If users.role doesn't exist or migration fails, continue without failing upgrade
        pass


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("sessions")
    op.drop_table("user_roles")
    op.drop_table("roles")
