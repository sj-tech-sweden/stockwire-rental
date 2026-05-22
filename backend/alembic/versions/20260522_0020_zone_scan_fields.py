"""add scan identifier fields to zones

Revision ID: 20260522_0020
Revises: 20260522_0019
Create Date: 2026-05-22 18:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260522_0020"
down_revision: str | Sequence[str] | None = "20260522_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("barcode", sa.String(length=255), nullable=True))
    op.add_column("zones", sa.Column("qr_code", sa.String(length=255), nullable=True))
    op.add_column("zones", sa.Column("rfid", sa.String(length=255), nullable=True))

    op.create_index(op.f("ix_zones_barcode"), "zones", ["barcode"], unique=False)
    op.create_index(op.f("ix_zones_qr_code"), "zones", ["qr_code"], unique=False)
    op.create_index(op.f("ix_zones_rfid"), "zones", ["rfid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_zones_rfid"), table_name="zones")
    op.drop_index(op.f("ix_zones_qr_code"), table_name="zones")
    op.drop_index(op.f("ix_zones_barcode"), table_name="zones")

    op.drop_column("zones", "rfid")
    op.drop_column("zones", "qr_code")
    op.drop_column("zones", "barcode")
