"""People-aligned user and crew.

Revision ID: 0078
Revises: 0077
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users: add first_name, last_name columns ──────────────────────────
    op.add_column("users", sa.Column("first_name", sa.String(150), server_default="", nullable=False))
    op.add_column("users", sa.Column("last_name", sa.String(150), server_default="", nullable=False))

    # Backfill first_name and last_name from full_name
    op.execute(
        """
        UPDATE users
        SET
            first_name = CASE
                WHEN position(' ' in full_name) > 0 THEN trim(substring(full_name from 1 for position(' ' in full_name) - 1))
                ELSE trim(full_name)
            END,
            last_name = CASE
                WHEN position(' ' in full_name) > 0 THEN trim(substring(full_name from position(' ' in full_name) + 1))
                ELSE ''
            END
        WHERE first_name = '' AND full_name IS NOT NULL AND full_name != ''
        """
    )

    # ── CrewMembers: drop name, email, phone columns ─────────────────────
    op.drop_index("ix_crew_members_name", table_name="crew_members")
    op.drop_index("ix_crew_members_email", table_name="crew_members")
    op.drop_column("crew_members", "name")
    op.drop_column("crew_members", "email")
    op.drop_column("crew_members", "phone")

    # ── CrewMembers: add check constraint for user_id OR person_id ───────
    op.create_check_constraint(
        "ck_crew_member_user_or_person_required",
        "crew_members",
        "user_id IS NOT NULL OR person_id IS NOT NULL",
    )


def downgrade() -> None:
    # ── CrewMembers: drop check constraint ────────────────────────────────
    op.drop_constraint("ck_crew_member_user_or_person_required", "crew_members", type_="check")

    # ── CrewMembers: re-add name, email, phone columns ───────────────────
    op.add_column("crew_members", sa.Column("name", sa.String(255), nullable=False, server_default=""))
    op.add_column("crew_members", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("crew_members", sa.Column("phone", sa.String(50), nullable=True))
    op.create_index("ix_crew_members_email", "crew_members", ["email"])
    op.create_index("ix_crew_members_name", "crew_members", ["name"])

    # Backfill crew member names from linked person or user
    op.execute(
        """
        UPDATE crew_members cm
        SET name = COALESCE(
            (SELECT p.first_name || ' ' || p.last_name FROM persons p WHERE p.id = cm.person_id),
            (SELECT u.full_name FROM users u WHERE u.id = cm.user_id),
            ''
        )
        WHERE cm.name = ''
        """
    )

    # ── Users: drop first_name, last_name columns ────────────────────────
    op.drop_column("users", "first_name")
    op.drop_column("users", "last_name")
