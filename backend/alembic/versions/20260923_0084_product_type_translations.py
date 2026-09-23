"""Product type translations.

Revision ID: 0084
Revises: 0083
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import column, table

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None

PRODUCT_TYPE_LABELS = [
    ("equipment", "en", "Equipment"),
    ("equipment", "sv", "Utrustning"),
    ("accessory", "en", "Accessory"),
    ("accessory", "sv", "Tillbehor"),
    ("consumable", "en", "Consumable"),
    ("consumable", "sv", "Forbrukningsvara"),
    ("case", "en", "Case"),
    ("case", "sv", "Lada"),
    ("rental", "en", "Rental"),
    ("rental", "sv", "Uthyrning"),
    ("bundle", "en", "Bundle"),
    ("bundle", "sv", "Paket"),
    ("crew", "en", "Crew"),
    ("crew", "sv", "Personal"),
]


def upgrade() -> None:
    op.create_table(
        "product_type_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_type", sa.String(length=50), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_type", "locale", name="uq_product_type_locale"),
    )
    op.create_index(
        "ix_product_type_translations_product_type",
        "product_type_translations",
        ["product_type"],
    )

    translations = table(
        "product_type_translations",
        column("product_type", sa.String),
        column("locale", sa.String),
        column("label", sa.String),
    )
    op.bulk_insert(
        translations,
        [{"product_type": t, "locale": l, "label": label} for (t, l, label) in PRODUCT_TYPE_LABELS],
    )


def downgrade() -> None:
    op.drop_table("product_type_translations")
