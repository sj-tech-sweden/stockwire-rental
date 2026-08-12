"""create user_notification_preferences table

Revision ID: 0065
Revises: 0064
Create Date: 2026-08-12

"""

from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.exec_driver_sql(
        "SELECT 1 FROM pg_tables WHERE schemaname='public' "
        "AND tablename='user_notification_preferences'"
    )
    if not result.fetchone():
        conn.exec_driver_sql(
            """
            CREATE TABLE user_notification_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                event_type VARCHAR(80) NOT NULL,
                email_enabled BOOLEAN NOT NULL DEFAULT true,
                web_push_enabled BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, event_type)
            )
            """
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS user_notification_preferences")
