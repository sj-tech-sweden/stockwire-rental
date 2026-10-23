"""Add email and phone columns to the companies table.

The Company model has defined ``email`` and ``phone`` columns since the
company/person split, but no migration ever added them to the ``companies``
table (0074 only added them to ``persons``). The pytest suite hides this
because it builds its schema from the models via ``create_all``; the e2e
suite runs ``alembic upgrade head`` and therefore hits a missing column on
INSERT. Add the two columns to match the model.

Revision ID: 0106
Revises: 0105
Create Date: 2026-10-23

"""

from alembic import op
import sqlalchemy as sa

revision = "0106"
down_revision = "0105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("email", sa.String(255), nullable=True),
    )
    op.create_index("ix_companies_email", "companies", ["email"])
    op.add_column(
        "companies",
        sa.Column("phone", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "phone")
    op.drop_index("ix_companies_email", table_name="companies")
    op.drop_column("companies", "email")
