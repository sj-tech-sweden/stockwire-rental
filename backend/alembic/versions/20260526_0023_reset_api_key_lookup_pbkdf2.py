"""reset api_key_lookup digests for PBKDF2-1-iteration switch

The lookup digest algorithm changed from HMAC-SHA256 to PBKDF2-HMAC-SHA256
(1 iteration). Existing rows that were backfilled with an HMAC-SHA256 digest
would never match the new PBKDF2-based indexed lookup, so reset them to NULL.
They will be transparently re-backfilled with the PBKDF2 digest on the next
successful authentication.

Revision ID: 20260526_0023
Revises: 20260526_0022
Create Date: 2026-05-26 08:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260526_0023"
down_revision: str | Sequence[str] | None = "20260526_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullify all existing lookup digests so they are recomputed with the new
    # PBKDF2-HMAC-SHA256 (1 iteration) algorithm on the first authentication request.
    op.execute(sa.text("UPDATE api_keys SET api_key_lookup = NULL WHERE api_key_lookup IS NOT NULL"))


def downgrade() -> None:
    # There is no way to reconstruct the original HMAC-SHA256 digests from the DB,
    # so downgrade simply leaves the column NULL (the fallback scan will handle
    # re-backfilling if the old code is rolled back).
    pass
