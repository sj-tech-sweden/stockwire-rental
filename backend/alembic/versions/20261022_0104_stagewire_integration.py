"""Add Stagewire integration fields: job_requirements.label and products.specs

Revision ID: 0104
Revises: 0103
Create Date: 2026-10-22

- job_requirements.label: optional free-form label for a requirement line
  (e.g. the Stagewire gear line label pushed back from a Stagewire job).
- products.specs: JSON blob holding structured product specifications such as
  mixer I/O counts ({inputs, outputs, aux, matrix}) used by Stagewire to
  suggest a mixer model from a channel list.
"""

from alembic import op
import sqlalchemy as sa

revision = '0104'
down_revision = '0103'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'job_requirements',
        sa.Column('label', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'products',
        sa.Column('specs', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('products', 'specs')
    op.drop_column('job_requirements', 'label')
