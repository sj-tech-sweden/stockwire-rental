"""Compliance service for crew certification and skill guardrails."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.crew.models import (
    CrewCertification,
    CrewMemberCertification,
    CrewMemberSkill,
    CrewRole,
    JobCrewAssignment,
    JobCrewRequirement,
    JobRequiredSkill,
    JobRoleRequiredCertification,
)
from app.domain.crew.schemas import ComplianceWarning, JobComplianceResult
from app.domain.inventory.models import Product
from app.domain.jobs.models import Job, JobRequirement

EXPIRING_SOON_DAYS = 30


def compute_certification_status(
    expires_at: date | None,
    job_start_date: date | None,
    job_end_date: date | None,
) -> str:
    """Compute the compliance status of a certification relative to job dates.

    Returns:
        "valid"        – cert covers the entire job window
        "expiring_soon" – cert expires within 30 days of job start
        "expired"      – cert expired before job start
    """
    if expires_at is None:
        return "valid"

    reference = job_start_date or date.today()

    if expires_at < reference:
        return "expired"

    if job_start_date and expires_at < job_start_date + timedelta(days=EXPIRING_SOON_DAYS):
        return "expiring_soon"

    return "valid"


def check_job_crew_compliance(db: Session, job_id: int) -> JobComplianceResult:
    """Check all assigned crew against required certifications and skills for a job.

    Evaluates:
    1. Required certifications from the crew member's assigned role (JobRoleRequiredCertification)
    2. Required certifications from equipment on the job (EquipmentRequiredCertification)
    3. Required skills from the crew requirement (JobRequiredSkill)
    """
    job = db.get(Job, job_id)
    if not job:
        return JobComplianceResult(job_id=job_id, is_compliant=False, warnings=[])

    warnings: list[ComplianceWarning] = []

    # Get all crew requirements for this job with their assignments
    reqs = list(db.scalars(
        select(JobCrewRequirement)
        .where(JobCrewRequirement.job_id == job_id)
        .options(
            selectinload(JobCrewRequirement.assignments)
            .selectinload(JobCrewAssignment.crew_member),
            selectinload(JobCrewRequirement.required_skills)
            .selectinload(JobRequiredSkill.skill),
            selectinload(JobCrewRequirement.crew_role)
            .selectinload(CrewRole.required_certifications)
            .selectinload(JobRoleRequiredCertification.certification_type),
        )
    ).all())

    # Collect equipment required certifications for this job
    job_requirements = list(db.scalars(
        select(JobRequirement).where(JobRequirement.job_id == job_id)
    ).all())
    equipment_cert_ids: set[int] = set()
    for jr in job_requirements:
        if jr.product_id:
            product = db.get(Product, jr.product_id)
            if product:
                for eq_cert in product.required_certifications:
                    equipment_cert_ids.add(eq_cert.certification_type_id)

    # Check each assignment
    checked_member_ids: set[int] = set()
    for req in reqs:
        for assignment in req.assignments:
            member = assignment.crew_member
            if not member or member.id in checked_member_ids:
                continue
            checked_member_ids.add(member.id)

            # Load member's certifications and skills
            member_certs = list(db.scalars(
                select(CrewMemberCertification)
                .where(CrewMemberCertification.crew_member_id == member.id)
                .options(selectinload(CrewMemberCertification.certification))
            ).all())
            member_cert_map = {
                c.certification_id: c for c in member_certs
            }

            member_skills = list(db.scalars(
                select(CrewMemberSkill)
                .where(CrewMemberSkill.crew_member_id == member.id)
                .options(selectinload(CrewMemberSkill.skill))
            ).all())
            member_skill_ids = {sk.skill_id for sk in member_skills}

            # Check role required certifications
            if req.crew_role and req.crew_role.required_certifications:
                for role_cert in req.crew_role.required_certifications:
                    cert_id = role_cert.certification_type_id
                    cert_name = role_cert.certification_type.name if role_cert.certification_type else f"Cert #{cert_id}"

                    if cert_id not in member_cert_map:
                        warnings.append(ComplianceWarning(
                            crew_member_id=member.id,
                            crew_member_name=member.name,
                            warning_type="missing_cert",
                            certification_name=cert_name,
                            message=f"{member.name} is missing required certification '{cert_name}' for role {req.crew_role.name}",
                            severity="error",
                        ))
                    else:
                        status = compute_certification_status(
                            member_cert_map[cert_id].expiry_date,
                            job.start_date,
                            job.end_date,
                        )
                        if status == "expired":
                            warnings.append(ComplianceWarning(
                                crew_member_id=member.id,
                                crew_member_name=member.name,
                                warning_type="expired_cert",
                                certification_name=cert_name,
                                message=f"{member.name}'s certification '{cert_name}' is expired (required for role {req.crew_role.name})",
                                severity="error",
                            ))
                        elif status == "expiring_soon":
                            warnings.append(ComplianceWarning(
                                crew_member_id=member.id,
                                crew_member_name=member.name,
                                warning_type="expiring_soon_cert",
                                certification_name=cert_name,
                                message=f"{member.name}'s certification '{cert_name}' expires soon (required for role {req.crew_role.name})",
                                severity="warning",
                            ))

            # Check equipment required certifications
            for cert_id in equipment_cert_ids:
                if cert_id in member_cert_map:
                    continue
                # Check if this cert is already covered by role check
                already_checked = False
                if req.crew_role and req.crew_role.required_certifications:
                    already_checked = any(rc.certification_type_id == cert_id for rc in req.crew_role.required_certifications)
                if already_checked:
                    continue

                cert_type = db.get(CrewCertification, cert_id)
                cert_name = cert_type.name if cert_type else f"Cert #{cert_id}"
                warnings.append(ComplianceWarning(
                    crew_member_id=member.id,
                    crew_member_name=member.name,
                    warning_type="missing_cert",
                    certification_name=cert_name,
                    message=f"{member.name} is missing certification '{cert_name}' required for scheduled equipment",
                    severity="error",
                ))

            # Check required skills
            if req.required_skills:
                for req_skill in req.required_skills:
                    if req_skill.skill_id not in member_skill_ids:
                        skill_name = req_skill.skill.name if req_skill.skill else f"Skill #{req_skill.skill_id}"
                        warnings.append(ComplianceWarning(
                            crew_member_id=member.id,
                            crew_member_name=member.name,
                            warning_type="missing_skill",
                            skill_name=skill_name,
                            message=f"{member.name} is missing required skill '{skill_name}'",
                            severity="warning",
                        ))

    is_compliant = not any(w.severity == "error" for w in warnings)
    return JobComplianceResult(
        job_id=job_id,
        is_compliant=is_compliant,
        warnings=warnings,
    )
