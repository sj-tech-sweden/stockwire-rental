"""add twenty webhook base url"""

revision = 'f55323ecd157'
down_revision = '0073'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.add_column('twenty_config', sa.Column('webhook_base_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('twenty_config', 'webhook_base_url')
