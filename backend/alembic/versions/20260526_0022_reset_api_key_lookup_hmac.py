"""reset api_key_lookup digests for HMAC-SHA256 switch

The lookup digest algorithm changed from BLAKE2b to HMAC-SHA256.  Existing
rows that were backfilled with a BLAKE2b digest would never match the new
HMAC-based indexed lookup, so reset them to NULL.  They will be transparently
re-backfilled with the HMAC digest on the next successful authentication.

Revision ID: 20260526_0022
Revises: 20260525_0021
Create Date: 2026-05-26 06:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260526_0022"
down_revision: str | Sequence[str] | None = "20260525_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullify all existing lookup digests so they are recomputed with the new
    # HMAC-SHA256 algorithm on the first authentication request.
    op.execute(sa.text("UPDATE api_keys SET api_key_lookup = NULL WHERE api_key_lookup IS NOT NULL"))


def downgrade() -> None:
    # There is no way to reconstruct the original BLAKE2b digests from the DB,
    # so downgrade simply leaves the column NULL (the fallback scan will handle
    # re-backfilling if the old code is rolled back).
    pass
