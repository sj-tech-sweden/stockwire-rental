"""crew management: roles, members, skills, certifications, job crew requirements and assignments

Revision ID: 20260724_0052
Revises: 20260723_0051
Create Date: 2026-07-24 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0052"
down_revision = "20260723_0051"
branch_labels = None
depends_on = None


def upgrade():
    # --- Crew Roles ---
    op.create_table(
        "crew_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Crew Members ---
    op.create_table(
        "crew_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True, index=True),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Crew Member Skills ---
    op.create_table(
        "crew_member_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crew_member_id", sa.Integer(), sa.ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("skill", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("crew_member_id", "skill", name="uq_crew_member_skill"),
    )

    # --- Crew Member Certifications ---
    op.create_table(
        "crew_member_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crew_member_id", sa.Integer(), sa.ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("certification", sa.String(120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("crew_member_id", "certification", name="uq_crew_member_cert"),
    )

    # --- Job Crew Requirements ---
    op.create_table(
        "job_crew_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("crew_role_id", sa.Integer(), sa.ForeignKey("crew_roles.id"), nullable=True, index=True),
        sa.Column("custom_role_name", sa.String(120), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("quantity_assigned", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("required_skills", sa.Text(), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Job Crew Assignments ---
    op.create_table(
        "job_crew_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_crew_requirement_id", sa.Integer(), sa.ForeignKey("job_crew_requirements.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("crew_member_id", sa.Integer(), sa.ForeignKey("crew_members.id"), nullable=False, index=True),
        sa.Column("status", sa.String(30), server_default="assigned", nullable=False, index=True),
        sa.Column("hourly_rate_override", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_crew_requirement_id", "crew_member_id", name="uq_job_crew_assignment"),
    )


def downgrade():
    op.drop_table("job_crew_assignments")
    op.drop_table("job_crew_requirements")
    op.drop_table("crew_member_certifications")
    op.drop_table("crew_member_skills")
    op.drop_table("crew_members")
    op.drop_table("crew_roles")
