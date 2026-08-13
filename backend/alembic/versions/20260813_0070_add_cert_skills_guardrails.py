"""add certification document_url, equipment & role required certifications

Revision ID: 0070
Revises: 0069
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add document_url to crew_member_certifications for uploaded proof files
    op.add_column("crew_member_certifications", sa.Column("document_url", sa.String(500), nullable=True))
    op.add_column("crew_member_certifications", sa.Column("certificate_number", sa.String(120), nullable=True))
    op.add_column("crew_member_certifications", sa.Column("issued_at", sa.Date(), nullable=True))

    # Equipment required certifications join table
    op.create_table(
        "equipment_required_certifications",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "certification_type_id",
            sa.Integer(),
            sa.ForeignKey("crew_certifications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Job role required certifications join table
    op.create_table(
        "job_role_required_certifications",
        sa.Column(
            "job_role_id",
            sa.Integer(),
            sa.ForeignKey("crew_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "certification_type_id",
            sa.Integer(),
            sa.ForeignKey("crew_certifications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("job_role_required_certifications")
    op.drop_table("equipment_required_certifications")
    op.drop_column("crew_member_certifications", "issued_at")
    op.drop_column("crew_member_certifications", "certificate_number")
    op.drop_column("crew_member_certifications", "document_url")
