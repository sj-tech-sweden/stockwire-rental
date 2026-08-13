from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.customers.models import Customer
from app.domain.auth.models import User
from app.domain.jobs.models import Job
from app.domain.crew.models import (
    CrewMember,
    CrewMemberCertification,
    CrewMemberSkill,
    CrewRole,
    CrewSkill,
    CrewCertification,
    EquipmentRequiredCertification,
    JobCrewAssignment,
    JobCrewRequirement,
    JobRequiredSkill,
    JobRoleRequiredCertification,
)
from app.domain.crew.schemas import (
    CrewCertificationCreate,
    CrewCertificationRead,
    CrewMemberAssignmentRead,
    CrewMemberCertificationRead,
    CrewMemberCreate,
    CrewMemberRead,
    CrewMemberUpdate,
    CrewRoleCreate,
    CrewRoleRead,
    CrewRoleUpdate,
    CrewSkillCreate,
    CrewSkillRead,
    JobCrewAssignmentCreate,
    JobCrewAssignmentRead,
    JobCrewAssignmentUpdate,
    JobCrewRequirementBulkUpsert,
    JobCrewRequirementCreate,
    JobCrewRequirementRead,
    JobCrewRequirementUpdate,
    CrewSuggestion,
    SelfSkillToggle,
    SelfCertificationCreate,
    SelfCertificationUpdate,
    SelfCertificationRead,
    ComplianceWarning,
    JobComplianceResult,
)
from app.services.compliance_service import check_job_crew_compliance, compute_certification_status

router = APIRouter(prefix="/crew", tags=["crew"], dependencies=[Depends(get_current_user)])


def _to_crew_role_read(role: CrewRole) -> CrewRoleRead:
    return CrewRoleRead.model_validate(role)


def _to_crew_skill_read(skill: CrewSkill) -> CrewSkillRead:
    return CrewSkillRead.model_validate(skill)


def _to_crew_certification_read(cert: CrewCertification) -> CrewCertificationRead:
    return CrewCertificationRead.model_validate(cert)


def _to_crew_member_read(db: Session, member: CrewMember) -> CrewMemberRead:
    skills = [_to_crew_skill_read(sk.skill) for sk in member.skills] if member.skills else []
    certs = []
    for cert_link in member.certifications:
        certs.append(CrewMemberCertificationRead(
            id=cert_link.id,
            crew_member_id=cert_link.crew_member_id,
            certification=_to_crew_certification_read(cert_link.certification),
            expiry_date=cert_link.expiry_date,
            created_at=cert_link.created_at,
        ))
    preferred_roles = [_to_crew_role_read(r) for r in member.preferred_roles] if member.preferred_roles else []
    user_name = member.user.full_name if member.user else None
    supplier_name = member.supplier.name if member.supplier else None
    assignments = []
    if member.assignments:
        for a in member.assignments:
            req = a.job_crew_requirement
            job_code = req.job.job_code if req and req.job else None
            role_name = None
            if req:
                if req.crew_role:
                    role_name = req.crew_role.name
                elif req.custom_role_name:
                    role_name = req.custom_role_name
            assignments.append(CrewMemberAssignmentRead(
                id=a.id,
                job_id=req.job_id if req else 0,
                job_code=job_code,
                crew_role_name=role_name,
                status=a.status,
            ))
    return CrewMemberRead(
        id=member.id,
        name=member.name,
        email=member.email,
        phone=member.phone,
        user_id=member.user_id,
        supplier_id=member.supplier_id,
        hourly_rate=member.hourly_rate,
        daily_rate=member.daily_rate,
        notes=member.notes,
        is_active=member.is_active,
        created_at=member.created_at,
        user_name=user_name,
        supplier_name=supplier_name,
        skills=skills,
        certifications=certs,
        preferred_roles=preferred_roles,
        assignments=assignments,
    )


def _to_job_crew_requirement_read(db: Session, req: JobCrewRequirement) -> JobCrewRequirementRead:
    role_name = None
    if req.crew_role_id:
        role = db.get(CrewRole, req.crew_role_id)
        role_name = role.name if role else None
    if not role_name and req.custom_role_name:
        role_name = req.custom_role_name
    skills = [_to_crew_skill_read(link.skill) for link in req.required_skills] if req.required_skills else []
    return JobCrewRequirementRead(
        id=req.id,
        job_id=req.job_id,
        crew_role_id=req.crew_role_id,
        custom_role_name=req.custom_role_name,
        quantity=req.quantity,
        quantity_assigned=req.quantity_assigned,
        skills=skills,
        hourly_rate=req.hourly_rate,
        notes=req.notes,
        created_at=req.created_at,
        crew_role_name=role_name,
    )


def _to_job_crew_assignment_read(db: Session, assignment: JobCrewAssignment) -> JobCrewAssignmentRead:
    member = db.get(CrewMember, assignment.crew_member_id)
    member_name = member.name if member else None
    role_name = None
    req = db.get(JobCrewRequirement, assignment.job_crew_requirement_id)
    if req:
        if req.crew_role_id:
            role = db.get(CrewRole, req.crew_role_id)
            role_name = role.name if role else None
        if not role_name and req.custom_role_name:
            role_name = req.custom_role_name
    return JobCrewAssignmentRead(
        id=assignment.id,
        job_crew_requirement_id=assignment.job_crew_requirement_id,
        crew_member_id=assignment.crew_member_id,
        status=assignment.status,
        hourly_rate_override=assignment.hourly_rate_override,
        notes=assignment.notes,
        created_at=assignment.created_at,
        crew_member_name=member_name,
        crew_role_name=role_name,
    )


def _recalc_quantity_assigned(db: Session, requirement_id: int) -> None:
    req = db.get(JobCrewRequirement, requirement_id)
    if not req:
        return
    count = db.scalar(
        select(func.count()).select_from(JobCrewAssignment).where(
            JobCrewAssignment.job_crew_requirement_id == requirement_id
        )
    ) or 0
    req.quantity_assigned = int(count)


DEFAULT_CREW_ROLES = [
    "Sound Technician",
    "Lighting Engineer",
    "Stage Manager",
    "Video Engineer",
    "Rigger",
    "Stage Hand",
    "Driver",
    "Project Manager",
]


def _ensure_default_roles(db: Session) -> None:
    existing = db.scalars(select(CrewRole.name)).all()
    existing_set = {str(name).lower() for name in existing}
    for index, name in enumerate(DEFAULT_CREW_ROLES):
        if name.lower() not in existing_set:
            db.add(CrewRole(name=name, is_default=True, sort_order=index))
    db.flush()


# ── Crew Roles ──────────────────────────────────────────────────────────────


@router.get("/roles", response_model=list[CrewRoleRead])
def list_crew_roles(db: Session = Depends(get_db)) -> list[CrewRoleRead]:
    _ensure_default_roles(db)
    roles = list(db.scalars(select(CrewRole).order_by(CrewRole.sort_order, CrewRole.id)).all())
    return [_to_crew_role_read(r) for r in roles]


@router.post("/roles", response_model=CrewRoleRead, status_code=status.HTTP_201_CREATED)
def create_crew_role(payload: CrewRoleCreate, db: Session = Depends(get_db)) -> CrewRoleRead:
    existing = db.scalar(select(CrewRole).where(CrewRole.name == payload.name.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="Crew role with this name already exists")
    role = CrewRole(
        name=payload.name.strip(),
        description=payload.description,
        is_default=payload.is_default,
        sort_order=payload.sort_order,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return _to_crew_role_read(role)


@router.put("/roles/{role_id}", response_model=CrewRoleRead)
def update_crew_role(role_id: int, payload: CrewRoleUpdate, db: Session = Depends(get_db)) -> CrewRoleRead:
    role = db.get(CrewRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Crew role not found")
    if payload.name is not None:
        dup = db.scalar(select(CrewRole).where(CrewRole.name == payload.name.strip(), CrewRole.id != role_id))
        if dup:
            raise HTTPException(status_code=409, detail="Crew role with this name already exists")
        role.name = payload.name.strip()
    if payload.description is not None:
        role.description = payload.description
    if payload.is_default is not None:
        role.is_default = payload.is_default
    if payload.sort_order is not None:
        role.sort_order = payload.sort_order
    db.commit()
    db.refresh(role)
    return _to_crew_role_read(role)


@router.delete("/roles/{role_id}")
def delete_crew_role(role_id: int, db: Session = Depends(get_db)) -> dict:
    role = db.get(CrewRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Crew role not found")
    in_use = db.scalar(
        select(func.count()).select_from(JobCrewRequirement).where(JobCrewRequirement.crew_role_id == role_id)
    ) or 0
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Crew role is used in {in_use} job requirement(s). Unlink it first.",
        )
    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Skills Registry ─────────────────────────────────────────────────────────


@router.get("/skills", response_model=list[CrewSkillRead])
def list_skills(
    q: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[CrewSkillRead]:
    query = select(CrewSkill).order_by(CrewSkill.name)
    if q:
        query = query.where(CrewSkill.name.ilike(f"%{q}%"))
    if category:
        query = query.where(CrewSkill.category == category)
    skills = list(db.scalars(query).all())
    return [_to_crew_skill_read(s) for s in skills]


@router.post("/skills", response_model=CrewSkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: CrewSkillCreate, db: Session = Depends(get_db)) -> CrewSkillRead:
    existing = db.scalar(select(CrewSkill).where(CrewSkill.name == payload.name.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="Skill with this name already exists")
    skill = CrewSkill(
        name=payload.name.strip(),
        category=payload.category.strip() if payload.category else None,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _to_crew_skill_read(skill)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)) -> dict:
    skill = db.get(CrewSkill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Certifications Registry ─────────────────────────────────────────────────


@router.get("/certifications", response_model=list[CrewCertificationRead])
def list_certifications(
    q: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[CrewCertificationRead]:
    query = select(CrewCertification).order_by(CrewCertification.name)
    if q:
        query = query.where(CrewCertification.name.ilike(f"%{q}%"))
    if category:
        query = query.where(CrewCertification.category == category)
    certs = list(db.scalars(query).all())
    return [_to_crew_certification_read(c) for c in certs]


@router.post("/certifications", response_model=CrewCertificationRead, status_code=status.HTTP_201_CREATED)
def create_certification(payload: CrewCertificationCreate, db: Session = Depends(get_db)) -> CrewCertificationRead:
    existing = db.scalar(select(CrewCertification).where(CrewCertification.name == payload.name.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="Certification with this name already exists")
    cert = CrewCertification(
        name=payload.name.strip(),
        category=payload.category.strip() if payload.category else None,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return _to_crew_certification_read(cert)


@router.delete("/certifications/{cert_id}")
def delete_certification(cert_id: int, db: Session = Depends(get_db)) -> dict:
    cert = db.get(CrewCertification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(cert)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Crew Members ─────────────────────────────────────────────────────────────


@router.get("/members", response_model=list[CrewMemberRead])
def list_crew_members(
    active_only: bool = False,
    db: Session = Depends(get_db),
) -> list[CrewMemberRead]:
    q = select(CrewMember).order_by(CrewMember.name).options(
        selectinload(CrewMember.user),
        selectinload(CrewMember.supplier),
        selectinload(CrewMember.skills).selectinload(CrewMemberSkill.skill),
        selectinload(CrewMember.certifications).selectinload(CrewMemberCertification.certification),
        selectinload(CrewMember.preferred_roles),
        selectinload(CrewMember.assignments)
        .selectinload(JobCrewAssignment.job_crew_requirement)
        .selectinload(JobCrewRequirement.crew_role),
        selectinload(CrewMember.assignments)
        .selectinload(JobCrewAssignment.job_crew_requirement)
        .selectinload(JobCrewRequirement.job),
    )
    if active_only:
        q = q.where(CrewMember.is_active.is_(True))
    members = list(db.scalars(q).all())
    return [_to_crew_member_read(db, m) for m in members]


@router.get("/members/{member_id}", response_model=CrewMemberRead)
def get_crew_member(member_id: int, db: Session = Depends(get_db)) -> CrewMemberRead:
    member = db.get(CrewMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    member = db.scalars(
        select(CrewMember)
        .where(CrewMember.id == member_id)
        .options(
            selectinload(CrewMember.user),
            selectinload(CrewMember.supplier),
            selectinload(CrewMember.skills).selectinload(CrewMemberSkill.skill),
            selectinload(CrewMember.certifications).selectinload(CrewMemberCertification.certification),
            selectinload(CrewMember.preferred_roles),
            selectinload(CrewMember.assignments)
            .selectinload(JobCrewAssignment.job_crew_requirement)
            .selectinload(JobCrewRequirement.crew_role),
            selectinload(CrewMember.assignments)
            .selectinload(JobCrewAssignment.job_crew_requirement)
            .selectinload(JobCrewRequirement.job),
        )
    ).unique().one()
    return _to_crew_member_read(db, member)


@router.post("/members", response_model=CrewMemberRead, status_code=status.HTTP_201_CREATED)
def create_crew_member(payload: CrewMemberCreate, db: Session = Depends(get_db)) -> CrewMemberRead:
    _ensure_default_roles(db)
    member = CrewMember(
        name=payload.name.strip(),
        email=payload.email,
        phone=payload.phone,
        user_id=payload.user_id,
        supplier_id=payload.supplier_id,
        hourly_rate=payload.hourly_rate,
        daily_rate=payload.daily_rate,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(member)
    db.flush()

    for skill_id in payload.skill_ids:
        skill = db.get(CrewSkill, skill_id)
        if skill:
            db.add(CrewMemberSkill(crew_member_id=member.id, skill_id=skill_id))

    for cert_item in payload.certification_items:
        cert = db.get(CrewCertification, cert_item.certification_id)
        if cert:
            db.add(CrewMemberCertification(
                crew_member_id=member.id,
                certification_id=cert_item.certification_id,
                expiry_date=cert_item.expiry_date,
            ))

    for role_id in payload.preferred_role_ids:
        role = db.get(CrewRole, role_id)
        if role:
            member.preferred_roles.append(role)

    db.commit()
    db.refresh(member)
    return _to_crew_member_read(db, member)


@router.put("/members/{member_id}", response_model=CrewMemberRead)
def update_crew_member(member_id: int, payload: CrewMemberUpdate, db: Session = Depends(get_db)) -> CrewMemberRead:
    member = db.get(CrewMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")

    if payload.name is not None:
        member.name = payload.name.strip()
    if payload.email is not None:
        member.email = payload.email
    if payload.phone is not None:
        member.phone = payload.phone
    if payload.user_id is not None:
        member.user_id = payload.user_id
    if payload.supplier_id is not None:
        member.supplier_id = payload.supplier_id
    if payload.hourly_rate is not None:
        member.hourly_rate = payload.hourly_rate
    if payload.daily_rate is not None:
        member.daily_rate = payload.daily_rate
    if payload.notes is not None:
        member.notes = payload.notes
    if payload.is_active is not None:
        member.is_active = payload.is_active

    if payload.skill_ids is not None:
        db.execute(delete(CrewMemberSkill).where(CrewMemberSkill.crew_member_id == member_id))
        for skill_id in payload.skill_ids:
            skill = db.get(CrewSkill, skill_id)
            if skill:
                db.add(CrewMemberSkill(crew_member_id=member.id, skill_id=skill_id))

    if payload.certification_items is not None:
        db.execute(delete(CrewMemberCertification).where(CrewMemberCertification.crew_member_id == member_id))
        for cert_item in payload.certification_items:
            cert = db.get(CrewCertification, cert_item.certification_id)
            if cert:
                db.add(CrewMemberCertification(
                    crew_member_id=member.id,
                    certification_id=cert_item.certification_id,
                    expiry_date=cert_item.expiry_date,
                ))

    if payload.preferred_role_ids is not None:
        _ensure_default_roles(db)
        member.preferred_roles.clear()
        for role_id in payload.preferred_role_ids:
            role = db.get(CrewRole, role_id)
            if role:
                member.preferred_roles.append(role)

    db.commit()
    db.refresh(member)
    return _to_crew_member_read(db, member)


@router.delete("/members/{member_id}")
def delete_crew_member(member_id: int, db: Session = Depends(get_db)) -> dict:
    member = db.get(CrewMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    in_use = db.scalar(
        select(func.count()).select_from(JobCrewAssignment).where(JobCrewAssignment.crew_member_id == member_id)
    ) or 0
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Crew member is assigned to {in_use} job(s). Remove assignments first.",
        )
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Job Crew Requirements ────────────────────────────────────────────────────


@router.get("/jobs/{job_id}/crew-requirements", response_model=list[JobCrewRequirementRead])
def list_job_crew_requirements(job_id: int, db: Session = Depends(get_db)) -> list[JobCrewRequirementRead]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    reqs = list(db.scalars(
        select(JobCrewRequirement)
        .where(JobCrewRequirement.job_id == job_id)
        .options(
            selectinload(JobCrewRequirement.crew_role),
            selectinload(JobCrewRequirement.required_skills).selectinload(JobRequiredSkill.skill),
        )
        .order_by(JobCrewRequirement.id)
    ).all())
    return [_to_job_crew_requirement_read(db, r) for r in reqs]


@router.post("/jobs/{job_id}/crew-requirements", response_model=JobCrewRequirementRead, status_code=status.HTTP_201_CREATED)
def create_job_crew_requirement(
    job_id: int, payload: JobCrewRequirementCreate, db: Session = Depends(get_db)
) -> JobCrewRequirementRead:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if payload.crew_role_id:
        _ensure_default_roles(db)
        role = db.get(CrewRole, payload.crew_role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Crew role not found")
    req = JobCrewRequirement(
        job_id=job_id,
        crew_role_id=payload.crew_role_id,
        custom_role_name=payload.custom_role_name,
        quantity=payload.quantity,
        hourly_rate=payload.hourly_rate,
        notes=payload.notes,
    )
    db.add(req)
    db.flush()

    for skill_id in payload.skill_ids:
        skill = db.get(CrewSkill, skill_id)
        if skill:
            db.add(JobRequiredSkill(job_crew_requirement_id=req.id, skill_id=skill_id))

    db.commit()
    db.refresh(req)
    return _to_job_crew_requirement_read(db, req)


@router.put("/jobs/{job_id}/crew-requirements/{req_id}", response_model=JobCrewRequirementRead)
def update_job_crew_requirement(
    job_id: int, req_id: int, payload: JobCrewRequirementUpdate, db: Session = Depends(get_db)
) -> JobCrewRequirementRead:
    req = db.get(JobCrewRequirement, req_id)
    if not req or req.job_id != job_id:
        raise HTTPException(status_code=404, detail="Crew requirement not found")
    if payload.crew_role_id is not None:
        req.crew_role_id = payload.crew_role_id
    if payload.custom_role_name is not None:
        req.custom_role_name = payload.custom_role_name
    if payload.quantity is not None:
        req.quantity = payload.quantity
    if payload.skill_ids is not None:
        db.execute(delete(JobRequiredSkill).where(JobRequiredSkill.job_crew_requirement_id == req_id))
        for skill_id in payload.skill_ids:
            skill = db.get(CrewSkill, skill_id)
            if skill:
                db.add(JobRequiredSkill(job_crew_requirement_id=req_id, skill_id=skill_id))
    if payload.hourly_rate is not None:
        req.hourly_rate = payload.hourly_rate
    if payload.notes is not None:
        req.notes = payload.notes
    db.commit()
    db.refresh(req)
    return _to_job_crew_requirement_read(db, req)


@router.delete("/jobs/{job_id}/crew-requirements/{req_id}")
def delete_job_crew_requirement(job_id: int, req_id: int, db: Session = Depends(get_db)) -> dict:
    req = db.get(JobCrewRequirement, req_id)
    if not req or req.job_id != job_id:
        raise HTTPException(status_code=404, detail="Crew requirement not found")
    in_use = db.scalar(
        select(func.count()).select_from(JobCrewAssignment).where(JobCrewAssignment.job_crew_requirement_id == req_id)
    ) or 0
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Crew requirement has {in_use} assignment(s). Remove them first.",
        )
    db.delete(req)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/jobs/{job_id}/crew-requirements/bulk", response_model=list[JobCrewRequirementRead])
def bulk_upsert_job_crew_requirements(
    job_id: int, payload: JobCrewRequirementBulkUpsert, db: Session = Depends(get_db)
) -> list[JobCrewRequirementRead]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    _ensure_default_roles(db)

    existing = list(db.scalars(
        select(JobCrewRequirement).where(JobCrewRequirement.job_id == job_id)
    ).all())
    existing_map = {r.id: r for r in existing}

    incoming_ids: set[int] = set()
    result_rows: list[JobCrewRequirement] = []

    for item in payload.items:
        if item.crew_role_id:
            role = db.get(CrewRole, item.crew_role_id)
            if not role:
                raise HTTPException(status_code=404, detail=f"Crew role {item.crew_role_id} not found")

        req = JobCrewRequirement(
            job_id=job_id,
            crew_role_id=item.crew_role_id,
            custom_role_name=item.custom_role_name,
            quantity=item.quantity,
            hourly_rate=item.hourly_rate,
            notes=item.notes,
        )
        db.add(req)
        db.flush()

        for skill_id in item.skill_ids:
            skill = db.get(CrewSkill, skill_id)
            if skill:
                db.add(JobRequiredSkill(job_crew_requirement_id=req.id, skill_id=skill_id))

        incoming_ids.add(req.id)
        result_rows.append(req)

    for existing_id, existing_row in existing_map.items():
        if existing_id not in incoming_ids:
            db.delete(existing_row)

    db.commit()

    refreshed = list(db.scalars(
        select(JobCrewRequirement)
        .where(JobCrewRequirement.job_id == job_id)
        .options(selectinload(JobCrewRequirement.required_skills).selectinload(JobRequiredSkill.skill))
        .order_by(JobCrewRequirement.id)
    ).all())
    return [_to_job_crew_requirement_read(db, r) for r in refreshed]


# ── Job Crew Assignments ─────────────────────────────────────────────────────


@router.get("/jobs/{job_id}/crew-assignments", response_model=list[JobCrewAssignmentRead])
def list_job_crew_assignments(job_id: int, db: Session = Depends(get_db)) -> list[JobCrewAssignmentRead]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    req_ids = [
        r.id for r in db.scalars(
            select(JobCrewRequirement).where(JobCrewRequirement.job_id == job_id)
        ).all()
    ]
    if not req_ids:
        return []

    assignments = list(db.scalars(
        select(JobCrewAssignment).where(
            JobCrewAssignment.job_crew_requirement_id.in_(req_ids)
        ).options(
            selectinload(JobCrewAssignment.crew_member),
            selectinload(JobCrewAssignment.job_crew_requirement).selectinload(JobCrewRequirement.crew_role),
        ).order_by(JobCrewAssignment.id)
    ).all())
    return [_to_job_crew_assignment_read(db, a) for a in assignments]


@router.post("/assignments", response_model=JobCrewAssignmentRead, status_code=status.HTTP_201_CREATED)
def create_crew_assignment(payload: JobCrewAssignmentCreate, db: Session = Depends(get_db)) -> JobCrewAssignmentRead:
    req = db.get(JobCrewRequirement, payload.job_crew_requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Crew requirement not found")
    member = db.get(CrewMember, payload.crew_member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")

    existing = db.scalar(
        select(JobCrewAssignment).where(
            JobCrewAssignment.job_crew_requirement_id == payload.job_crew_requirement_id,
            JobCrewAssignment.crew_member_id == payload.crew_member_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Crew member is already assigned to this requirement")

    if req.quantity_assigned >= req.quantity:
        raise HTTPException(status_code=409, detail="This crew requirement is fully staffed")

    assignment = JobCrewAssignment(
        job_crew_requirement_id=payload.job_crew_requirement_id,
        crew_member_id=payload.crew_member_id,
        status=payload.status,
        hourly_rate_override=payload.hourly_rate_override,
        notes=payload.notes,
    )
    db.add(assignment)
    db.flush()
    _recalc_quantity_assigned(db, req.id)
    db.commit()
    db.refresh(assignment)
    return _to_job_crew_assignment_read(db, assignment)


@router.put("/assignments/{assignment_id}", response_model=JobCrewAssignmentRead)
def update_crew_assignment(
    assignment_id: int, payload: JobCrewAssignmentUpdate, db: Session = Depends(get_db)
) -> JobCrewAssignmentRead:
    assignment = db.get(JobCrewAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Crew assignment not found")
    if payload.status is not None:
        assignment.status = payload.status
    if payload.hourly_rate_override is not None:
        assignment.hourly_rate_override = payload.hourly_rate_override
    if payload.notes is not None:
        assignment.notes = payload.notes
    db.commit()
    db.refresh(assignment)
    return _to_job_crew_assignment_read(db, assignment)


@router.delete("/assignments/{assignment_id}")
def delete_crew_assignment(assignment_id: int, db: Session = Depends(get_db)) -> dict:
    assignment = db.get(JobCrewAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Crew assignment not found")
    req_id = assignment.job_crew_requirement_id
    db.delete(assignment)
    db.flush()
    _recalc_quantity_assigned(db, req_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Suggestions ──────────────────────────────────────────────────────────────


@router.get("/jobs/{job_id}/crew-suggestions", response_model=list[CrewSuggestion])
def get_crew_suggestions(
    job_id: int,
    requirement_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[CrewSuggestion]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    reqs = list(db.scalars(
        select(JobCrewRequirement)
        .where(JobCrewRequirement.job_id == job_id)
        .options(
            selectinload(JobCrewRequirement.assignments),
            selectinload(JobCrewRequirement.required_skills).selectinload(JobRequiredSkill.skill),
        )
    ).all())

    if requirement_id:
        reqs = [r for r in reqs if r.id == requirement_id]

    if not reqs:
        return []

    all_members = list(db.scalars(
        select(CrewMember).where(CrewMember.is_active.is_(True))
    ).all())

    assigned_member_ids: set[int] = set()
    for req in reqs:
        for assignment in req.assignments:
            assigned_member_ids.add(assignment.crew_member_id)

    suggestions: list[CrewSuggestion] = []

    for member in all_members:
        if member.id in assigned_member_ids:
            continue

        member_skills = {sk.skill.name.lower() for sk in member.skills} if member.skills else set()
        member_role_ids = {r.id for r in member.preferred_roles} if member.preferred_roles else set()
        total_required: set[str] = set()
        total_matching: set[str] = set()
        required_role_ids: set[int] = set()

        for req in reqs:
            required = {link.skill.name.lower() for link in req.required_skills} if req.required_skills else set()
            total_required.update(required)
            total_matching.update(member_skills & required)
            if req.crew_role_id:
                required_role_ids.add(req.crew_role_id)

        if not total_required:
            score = 1.0 if not member_skills else 0.5
            matching = []
            missing = []
        else:
            score = len(total_matching) / len(total_required) if total_required else 0
            matching = sorted(total_matching)
            missing = sorted(total_required - member_skills)

        role_bonus = 0
        if required_role_ids and member_role_ids:
            role_match_count = len(required_role_ids & member_role_ids)
            role_bonus = role_match_count * 0.1

        score = min(score + role_bonus, 1.0)

        if score > 0:
            source = None
            if member.user_id:
                source = "internal"
            elif member.supplier_id:
                source = "supplier"

            suggestions.append(CrewSuggestion(
                crew_member_id=member.id,
                name=member.name,
                match_score=round(score, 3),
                matching_skills=matching,
                missing_skills=missing,
                hourly_rate=member.hourly_rate,
                source=source,
            ))

    suggestions.sort(key=lambda s: (-s.match_score, s.name))
    return suggestions


# ── Self-Service: My Skills & Certifications ────────────────────────────────


def _resolve_crew_member_for_user(db: Session, user: User) -> CrewMember:
    """Find the CrewMember linked to the current user. Raises 404 if not found."""
    member = db.scalars(
        select(CrewMember)
        .where(CrewMember.user_id == user.id)
        .options(
            selectinload(CrewMember.skills).selectinload(CrewMemberSkill.skill),
            selectinload(CrewMember.certifications).selectinload(CrewMemberCertification.certification),
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="No crew member profile is linked to your account")
    return member


@router.get("/users/me/skills", response_model=list[CrewSkillRead])
def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CrewSkillRead]:
    member = _resolve_crew_member_for_user(db, current_user)
    return [_to_crew_skill_read(sk.skill) for sk in member.skills]


@router.post("/users/me/skills", response_model=list[CrewSkillRead], status_code=status.HTTP_200_OK)
def add_my_skill(
    payload: SelfSkillToggle,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CrewSkillRead]:
    member = _resolve_crew_member_for_user(db, current_user)
    skill = db.get(CrewSkill, payload.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    existing = db.scalar(
        select(CrewMemberSkill).where(
            CrewMemberSkill.crew_member_id == member.id,
            CrewMemberSkill.skill_id == payload.skill_id,
        )
    )
    if not existing:
        db.add(CrewMemberSkill(crew_member_id=member.id, skill_id=payload.skill_id))
        db.commit()
    member = _resolve_crew_member_for_user(db, current_user)
    return [_to_crew_skill_read(sk.skill) for sk in member.skills]


@router.delete("/users/me/skills/{skill_id}", response_model=list[CrewSkillRead])
def remove_my_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CrewSkillRead]:
    member = _resolve_crew_member_for_user(db, current_user)
    link = db.scalar(
        select(CrewMemberSkill).where(
            CrewMemberSkill.crew_member_id == member.id,
            CrewMemberSkill.skill_id == skill_id,
        )
    )
    if link:
        db.delete(link)
        db.commit()
    member = _resolve_crew_member_for_user(db, current_user)
    return [_to_crew_skill_read(sk.skill) for sk in member.skills]


@router.get("/users/me/certifications", response_model=list[SelfCertificationRead])
def get_my_certifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SelfCertificationRead]:
    member = _resolve_crew_member_for_user(db, current_user)
    certs = list(db.scalars(
        select(CrewMemberCertification)
        .where(CrewMemberCertification.crew_member_id == member.id)
        .options(selectinload(CrewMemberCertification.certification))
        .order_by(CrewMemberCertification.id)
    ).all())
    result = []
    for c in certs:
        status_val = compute_certification_status(c.expiry_date, None, None)
        result.append(SelfCertificationRead(
            id=c.id,
            certification_type_id=c.certification_id,
            certification_type_name=c.certification.name if c.certification else "",
            certification_type_category=c.certification.category if c.certification else None,
            certificate_number=c.certificate_number,
            issued_at=c.issued_at,
            expiry_date=c.expiry_date,
            document_url=c.document_url,
            status=status_val,
            created_at=c.created_at,
        ))
    return result


@router.post("/users/me/certifications", response_model=SelfCertificationRead, status_code=status.HTTP_201_CREATED)
def add_my_certification(
    payload: SelfCertificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SelfCertificationRead:
    member = _resolve_crew_member_for_user(db, current_user)
    cert_type = db.get(CrewCertification, payload.certification_type_id)
    if not cert_type:
        raise HTTPException(status_code=404, detail="Certification type not found")
    cert = CrewMemberCertification(
        crew_member_id=member.id,
        certification_id=payload.certification_type_id,
        certificate_number=payload.certificate_number,
        issued_at=payload.issued_at,
        expiry_date=payload.expires_at,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    status_val = compute_certification_status(cert.expiry_date, None, None)
    return SelfCertificationRead(
        id=cert.id,
        certification_type_id=cert.certification_id,
        certification_type_name=cert_type.name,
        certification_type_category=cert_type.category,
        certificate_number=cert.certificate_number,
        issued_at=cert.issued_at,
        expiry_date=cert.expiry_date,
        document_url=cert.document_url,
        status=status_val,
        created_at=cert.created_at,
    )


@router.patch("/users/me/certifications/{cert_id}", response_model=SelfCertificationRead)
def update_my_certification(
    cert_id: int,
    payload: SelfCertificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SelfCertificationRead:
    member = _resolve_crew_member_for_user(db, current_user)
    cert = db.get(CrewMemberCertification, cert_id)
    if not cert or cert.crew_member_id != member.id:
        raise HTTPException(status_code=404, detail="Certification not found")
    if payload.document_url is not None:
        cert.document_url = payload.document_url
    if payload.certificate_number is not None:
        cert.certificate_number = payload.certificate_number
    if payload.issued_at is not None:
        cert.issued_at = payload.issued_at
    if payload.expiry_date is not None:
        cert.expiry_date = payload.expiry_date
    db.commit()
    db.refresh(cert)
    status_val = compute_certification_status(cert.expiry_date, None, None)
    cert_type = db.get(CrewCertification, cert.certification_id)
    return SelfCertificationRead(
        id=cert.id,
        certification_type_id=cert.certification_id,
        certification_type_name=cert_type.name if cert_type else "",
        certification_type_category=cert_type.category if cert_type else None,
        certificate_number=cert.certificate_number,
        issued_at=cert.issued_at,
        expiry_date=cert.expiry_date,
        document_url=cert.document_url,
        status=status_val,
        created_at=cert.created_at,
    )


@router.delete("/users/me/certifications/{cert_id}")
def remove_my_certification(
    cert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = _resolve_crew_member_for_user(db, current_user)
    cert = db.get(CrewMemberCertification, cert_id)
    if not cert or cert.crew_member_id != member.id:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(cert)
    db.commit()
    return {"status": "ok"}


# ── Equipment & Role Required Certifications ─────────────────────────────────


@router.get("/equipment/{product_id}/required-certifications", response_model=list[CrewCertificationRead])
def list_equipment_required_certs(
    product_id: int,
    db: Session = Depends(get_db),
) -> list[CrewCertificationRead]:
    links = list(db.scalars(
        select(EquipmentRequiredCertification)
        .where(EquipmentRequiredCertification.product_id == product_id)
        .options(selectinload(EquipmentRequiredCertification.certification_type))
    ).all())
    return [_to_crew_certification_read(link.certification_type) for link in links if link.certification_type]


@router.put("/equipment/{product_id}/required-certifications")
def set_equipment_required_certs(
    product_id: int,
    cert_ids: list[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> list[CrewCertificationRead]:
    db.execute(delete(EquipmentRequiredCertification).where(EquipmentRequiredCertification.product_id == product_id))
    for cert_id in cert_ids:
        cert = db.get(CrewCertification, cert_id)
        if cert:
            db.add(EquipmentRequiredCertification(product_id=product_id, certification_type_id=cert_id))
    db.commit()
    links = list(db.scalars(
        select(EquipmentRequiredCertification)
        .where(EquipmentRequiredCertification.product_id == product_id)
        .options(selectinload(EquipmentRequiredCertification.certification_type))
    ).all())
    return [_to_crew_certification_read(link.certification_type) for link in links if link.certification_type]


@router.get("/roles/{role_id}/required-certifications", response_model=list[CrewCertificationRead])
def list_role_required_certs(
    role_id: int,
    db: Session = Depends(get_db),
) -> list[CrewCertificationRead]:
    links = list(db.scalars(
        select(JobRoleRequiredCertification)
        .where(JobRoleRequiredCertification.job_role_id == role_id)
        .options(selectinload(JobRoleRequiredCertification.certification_type))
    ).all())
    return [_to_crew_certification_read(link.certification_type) for link in links if link.certification_type]


@router.put("/roles/{role_id}/required-certifications")
def set_role_required_certs(
    role_id: int,
    cert_ids: list[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> list[CrewCertificationRead]:
    db.execute(delete(JobRoleRequiredCertification).where(JobRoleRequiredCertification.job_role_id == role_id))
    for cert_id in cert_ids:
        cert = db.get(CrewCertification, cert_id)
        if cert:
            db.add(JobRoleRequiredCertification(job_role_id=role_id, certification_type_id=cert_id))
    db.commit()
    links = list(db.scalars(
        select(JobRoleRequiredCertification)
        .where(JobRoleRequiredCertification.job_role_id == role_id)
        .options(selectinload(JobRoleRequiredCertification.certification_type))
    ).all())
    return [_to_crew_certification_read(link.certification_type) for link in links if link.certification_type]


# ── Job Compliance Guardrails ────────────────────────────────────────────────


@router.get("/jobs/{job_id}/compliance", response_model=JobComplianceResult)
def get_job_compliance(
    job_id: int,
    db: Session = Depends(get_db),
) -> JobComplianceResult:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return check_job_crew_compliance(db, job_id)
