"""add eventory packlists json to products

Revision ID: 20260521_0015
Revises: 20260521_0014
Create Date: 2026-05-21 16:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0015"
down_revision = "20260521_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("eventory_packlists_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "eventory_packlists_json")
