"""add report template translations

Revision ID: 20260817_0072
Revises: 20260813_0071
Create Date: 2026-08-17 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0072"
down_revision: Union[str, None] = "0071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_templates",
        sa.Column("translations_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("report_templates", "translations_json")
