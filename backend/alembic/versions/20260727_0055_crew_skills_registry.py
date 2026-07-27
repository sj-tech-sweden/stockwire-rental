"""crew skills and certifications registry with many-to-many relationships

Revision ID: 20260727_0055
Revises: 20260727_0054
Create Date: 2026-07-27 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0055"
down_revision = "20260727_0054"
branch_labels = None
depends_on = None


def upgrade():
    # --- Create Crew Skills Registry ---
    op.create_table(
        "crew_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Create Crew Certifications Registry ---
    op.create_table(
        "crew_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Migrate existing skills to registry and update crew_member_skills ---
    conn = op.get_bind()

    # Insert distinct skill names into crew_skills
    skills_result = conn.execute(
        sa.text("SELECT DISTINCT skill FROM crew_member_skills WHERE skill IS NOT NULL AND skill != ''")
    )
    skill_names = [row[0] for row in skills_result]
    for name in skill_names:
        conn.execute(sa.text("INSERT INTO crew_skills (name) VALUES (:name)"), {"name": name})

    # Add skill_id column to crew_member_skills
    op.add_column("crew_member_skills", sa.Column("skill_id", sa.Integer(), sa.ForeignKey("crew_skills.id", ondelete="CASCADE"), nullable=True, index=True))

    # Populate skill_id from registry using Python loop (SQLite-compatible)
    members_result = conn.execute(sa.text("SELECT id, skill FROM crew_member_skills WHERE skill IS NOT NULL"))
    for member_id, skill_name in members_result:
        skill_row = conn.execute(sa.text("SELECT id FROM crew_skills WHERE name = :name"), {"name": skill_name}).fetchone()
        if skill_row:
            conn.execute(
                sa.text("UPDATE crew_member_skills SET skill_id = :skill_id WHERE id = :id"),
                {"skill_id": skill_row[0], "id": member_id},
            )

    # Drop old skill column and unique constraint, add new one
    op.drop_constraint("uq_crew_member_skill", "crew_member_skills", type_="unique")
    op.drop_column("crew_member_skills", "skill")
    op.alter_column("crew_member_skills", "skill_id", nullable=False)
    op.create_unique_constraint("uq_crew_member_skill", "crew_member_skills", ["crew_member_id", "skill_id"])

    # --- Migrate existing certifications to registry and update crew_member_certifications ---
    certs_result = conn.execute(
        sa.text("SELECT DISTINCT certification FROM crew_member_certifications WHERE certification IS NOT NULL AND certification != ''")
    )
    cert_names = [row[0] for row in certs_result]
    for name in cert_names:
        conn.execute(sa.text("INSERT INTO crew_certifications (name) VALUES (:name)"), {"name": name})

    # Add certification_id column
    op.add_column("crew_member_certifications", sa.Column("certification_id", sa.Integer(), sa.ForeignKey("crew_certifications.id", ondelete="CASCADE"), nullable=True, index=True))

    # Populate certification_id from registry using Python loop (SQLite-compatible)
    cert_links_result = conn.execute(sa.text("SELECT id, certification FROM crew_member_certifications WHERE certification IS NOT NULL"))
    for link_id, cert_name in cert_links_result:
        cert_row = conn.execute(sa.text("SELECT id FROM crew_certifications WHERE name = :name"), {"name": cert_name}).fetchone()
        if cert_row:
            conn.execute(
                sa.text("UPDATE crew_member_certifications SET certification_id = :cert_id WHERE id = :id"),
                {"cert_id": cert_row[0], "id": link_id},
            )

    # Rename expires_at to expiry_date, drop old column and constraint, add new ones
    op.drop_constraint("uq_crew_member_cert", "crew_member_certifications", type_="unique")
    op.alter_column("crew_member_certifications", "expires_at", new_column_name="expiry_date", nullable=True)
    op.drop_column("crew_member_certifications", "certification")
    op.alter_column("crew_member_certifications", "certification_id", nullable=False)
    op.create_unique_constraint("uq_crew_member_cert", "crew_member_certifications", ["crew_member_id", "certification_id"])

    # --- Create Job Required Skills junction table ---
    op.create_table(
        "job_required_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_crew_requirement_id", sa.Integer(), sa.ForeignKey("job_crew_requirements.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("crew_skills.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.UniqueConstraint("job_crew_requirement_id", "skill_id", name="uq_job_required_skill"),
    )

    # --- Migrate existing required_skills text to junction table (SQLite-compatible) ---
    reqs_result = conn.execute(
        sa.text("SELECT id, required_skills FROM job_crew_requirements WHERE required_skills IS NOT NULL AND required_skills != ''")
    )
    for req_id, required_skills_str in reqs_result:
        skill_names = [s.strip().lower() for s in required_skills_str.split(",") if s.strip()]
        for sname in skill_names:
            skill_row = conn.execute(
                sa.text("SELECT id FROM crew_skills WHERE LOWER(name) = :name"), {"name": sname}
            ).fetchone()
            if skill_row:
                conn.execute(
                    sa.text("INSERT INTO job_required_skills (job_crew_requirement_id, skill_id) VALUES (:req_id, :skill_id)"),
                    {"req_id": req_id, "skill_id": skill_row[0]},
                )

    # Drop old required_skills column
    op.drop_column("job_crew_requirements", "required_skills")


def downgrade():
    conn = op.get_bind()

    # Add back required_skills column
    op.add_column("job_crew_requirements", sa.Column("required_skills", sa.Text(), nullable=True))

    # Migrate data back from junction table using Python loop (SQLite-compatible)
    reqs_result = conn.execute(sa.text("SELECT id FROM job_crew_requirements"))
    for (req_id,) in reqs_result:
        skills_result = conn.execute(
            sa.text("""
                SELECT cs.name FROM job_required_skills jrs
                JOIN crew_skills cs ON jrs.skill_id = cs.id
                WHERE jrs.job_crew_requirement_id = :req_id
            """),
            {"req_id": req_id},
        )
        skill_names = [row[0] for row in skills_result]
        if skill_names:
            conn.execute(
                sa.text("UPDATE job_crew_requirements SET required_skills = :skills WHERE id = :id"),
                {"skills": ", ".join(skill_names), "id": req_id},
            )

    op.drop_table("job_required_skills")

    # Restore crew_member_certifications
    op.drop_constraint("uq_crew_member_cert", "crew_member_certifications", type_="unique")
    op.add_column("crew_member_certifications", sa.Column("certification", sa.String(120), nullable=True))

    cert_links = conn.execute(sa.text("SELECT id, certification_id FROM crew_member_certifications"))
    for link_id, cert_id in cert_links:
        cert_row = conn.execute(sa.text("SELECT name FROM crew_certifications WHERE id = :id"), {"id": cert_id}).fetchone()
        if cert_row:
            conn.execute(
                sa.text("UPDATE crew_member_certifications SET certification = :name WHERE id = :id"),
                {"name": cert_row[0], "id": link_id},
            )

    op.alter_column("crew_member_certifications", "certification", nullable=False)
    op.drop_column("crew_member_certifications", "certification_id")
    op.drop_column("crew_member_certifications", "expiry_date")
    op.create_unique_constraint("uq_crew_member_cert", "crew_member_certifications", ["crew_member_id", "certification"])
    op.drop_table("crew_certifications")

    # Restore crew_member_skills
    op.drop_constraint("uq_crew_member_skill", "crew_member_skills", type_="unique")
    op.add_column("crew_member_skills", sa.Column("skill", sa.String(120), nullable=True))

    member_skills = conn.execute(sa.text("SELECT id, skill_id FROM crew_member_skills"))
    for link_id, skill_id in member_skills:
        skill_row = conn.execute(sa.text("SELECT name FROM crew_skills WHERE id = :id"), {"id": skill_id}).fetchone()
        if skill_row:
            conn.execute(
                sa.text("UPDATE crew_member_skills SET skill = :name WHERE id = :id"),
                {"name": skill_row[0], "id": link_id},
            )

    op.alter_column("crew_member_skills", "skill", nullable=False)
    op.drop_column("crew_member_skills", "skill_id")
    op.create_unique_constraint("uq_crew_member_skill", "crew_member_skills", ["crew_member_id", "skill"])
    op.drop_table("crew_skills")
