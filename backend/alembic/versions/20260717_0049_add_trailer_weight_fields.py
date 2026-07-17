"""Add trailer curb weight and payload capacity

Revision ID: 20260717_0049
Revises: 20260717_0048
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260717_0049"
down_revision = "20260717_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("curb_weight_kg", sa.Numeric(10, 2), nullable=True))
    op.add_column("vehicles", sa.Column("max_payload_kg", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicles", "max_payload_kg")
    op.drop_column("vehicles", "curb_weight_kg")
