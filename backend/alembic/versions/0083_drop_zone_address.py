"""Drop the legacy single `address` column on zones (replaced by structured fields).

Revision ID: 0082
Revises: 0081
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("zones") and "address" in [
        c["name"] for c in inspector.get_columns("zones")
    ]:
        with op.batch_alter_table("zones") as batch_op:
            batch_op.drop_column("address")


def downgrade() -> None:
    with op.batch_alter_table("zones") as batch_op:
        batch_op.add_column(sa.Column("address", sa.String(length=255), nullable=True))
