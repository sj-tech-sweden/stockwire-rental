"""add deterministic lookup digest for api keys

Revision ID: 20260525_0021
Revises: 20260522_0020
Create Date: 2026-05-25 19:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260525_0021"
down_revision: str | Sequence[str] | None = "20260522_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("api_key_lookup", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_api_keys_api_key_lookup"), "api_keys", ["api_key_lookup"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_keys_api_key_lookup"), table_name="api_keys")
    op.drop_column("api_keys", "api_key_lookup")
