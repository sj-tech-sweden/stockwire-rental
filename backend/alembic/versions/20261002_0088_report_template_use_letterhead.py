"""report template use_letterhead flag

Templates now opt in to the system default letterhead via ``use_letterhead``
(default True). The default quote template is explicitly opted out so it never
stamps the company letterhead when configured without one.

Revision ID: 0088
Revises: 0087
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_templates",
        sa.Column("use_letterhead", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    # Existing quote template is configured without a letterhead.
    op.execute(
        "UPDATE report_templates SET use_letterhead = FALSE "
        "WHERE name = 'Quote' AND category = 'custom'"
    )


def downgrade() -> None:
    op.drop_column("report_templates", "use_letterhead")
