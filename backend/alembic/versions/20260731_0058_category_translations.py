"""create category_translations table

Revision ID: 20260731_0058
Revises: 20260729_0057
Create Date: 2026-07-31 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0058"
down_revision = "20260729_0057"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "category_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("inventory_categories.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("category_id", "locale", name="uq_category_locale"),
    )


def downgrade():
    op.drop_table("category_translations")
