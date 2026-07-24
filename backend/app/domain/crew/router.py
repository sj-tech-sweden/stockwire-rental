from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.customers.models import Customer
from app.domain.auth.models import User
from app.domain.jobs.models import Job
from app.domain.crew.models import CrewMember, CrewMemberCertification, CrewMemberSkill, CrewRole, JobCrewAssignment, JobCrewRequirement
from app.domain.crew.schemas import (
    CrewMemberCreate,
    CrewMemberRead,
    CrewMemberUpdate,
    CrewRoleCreate,
    CrewRoleRead,
    CrewRoleUpdate,
    JobCrewAssignmentCreate,
    JobCrewAssignmentRead,
    JobCrewAssignmentUpdate,
    JobCrewRequirementBulkUpsert,
    JobCrewRequirementCreate,
    JobCrewRequirementRead,
    JobCrewRequirementUpdate,
    CrewSuggestion,
)

router = APIRouter(prefix="/crew", tags=["crew"], dependencies=[Depends(get_current_user)])


def _to_crew_role_read(role: CrewRole) -> CrewRoleRead:
    return CrewRoleRead.model_validate(role)


def _parse_skills(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def _to_crew_member_read(db: Session, member: CrewMember) -> CrewMemberRead:
    skills = [sk.skill for sk in member.skills] if member.skills else []
    certs = list(member.certifications) if member.certifications else []
    preferred_roles = [_to_crew_role_read(r) for r in member.preferred_roles] if member.preferred_roles else []
    user_name = None
    if member.user_id:
        user = db.get(User, member.user_id)
        user_name = user.full_name if user else None
    supplier_name = None
    if member.supplier_id:
        supplier = db.get(Customer, member.supplier_id)
        supplier_name = supplier.name if supplier else None
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
    )


def _to_job_crew_requirement_read(db: Session, req: JobCrewRequirement) -> JobCrewRequirementRead:
    role_name = None
    if req.crew_role_id:
        role = db.get(CrewRole, req.crew_role_id)
        role_name = role.name if role else None
    if not role_name and req.custom_role_name:
        role_name = req.custom_role_name
    return JobCrewRequirementRead(
        id=req.id,
        job_id=req.job_id,
        crew_role_id=req.crew_role_id,
        custom_role_name=req.custom_role_name,
        quantity=req.quantity,
        quantity_assigned=req.quantity_assigned,
        required_skills=req.required_skills,
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
    return {"ok": True}


# ── Crew Members ─────────────────────────────────────────────────────────────


@router.get("/members", response_model=list[CrewMemberRead])
def list_crew_members(
    active_only: bool = False,
    db: Session = Depends(get_db),
) -> list[CrewMemberRead]:
    q = select(CrewMember).order_by(CrewMember.name).options(
        selectinload(CrewMember.skills),
        selectinload(CrewMember.certifications),
        selectinload(CrewMember.preferred_roles),
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

    for skill_name in payload.skills:
        skill_name = skill_name.strip()
        if skill_name:
            db.add(CrewMemberSkill(crew_member_id=member.id, skill=skill_name))

    for cert in payload.certifications:
        cert_name = cert.certification.strip()
        if cert_name:
            db.add(CrewMemberCertification(
                crew_member_id=member.id,
                certification=cert_name,
                expires_at=cert.expires_at,
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

    if payload.skills is not None:
        db.query(CrewMemberSkill).filter(CrewMemberSkill.crew_member_id == member_id).delete()
        for skill_name in payload.skills:
            skill_name = skill_name.strip()
            if skill_name:
                db.add(CrewMemberSkill(crew_member_id=member.id, skill=skill_name))

    if payload.certifications is not None:
        db.query(CrewMemberCertification).filter(
            CrewMemberCertification.crew_member_id == member_id
        ).delete()
        for cert in payload.certifications:
            cert_name = cert.certification.strip()
            if cert_name:
                db.add(CrewMemberCertification(
                    crew_member_id=member.id,
                    certification=cert_name,
                    expires_at=cert.expires_at,
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
    return {"ok": True}


# ── Job Crew Requirements ────────────────────────────────────────────────────


@router.get("/jobs/{job_id}/crew-requirements", response_model=list[JobCrewRequirementRead])
def list_job_crew_requirements(job_id: int, db: Session = Depends(get_db)) -> list[JobCrewRequirementRead]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    reqs = list(db.scalars(
        select(JobCrewRequirement)
        .where(JobCrewRequirement.job_id == job_id)
        .options(selectinload(JobCrewRequirement.crew_role))
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
        required_skills=payload.required_skills,
        hourly_rate=payload.hourly_rate,
        notes=payload.notes,
    )
    db.add(req)
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
    if payload.required_skills is not None:
        req.required_skills = payload.required_skills
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
    return {"ok": True}


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
            required_skills=item.required_skills,
            hourly_rate=item.hourly_rate,
            notes=item.notes,
        )
        db.add(req)
        db.flush()
        incoming_ids.add(req.id)
        result_rows.append(req)

    for existing_id, existing_row in existing_map.items():
        if existing_id not in incoming_ids:
            db.delete(existing_row)

    db.commit()

    refreshed = list(db.scalars(
        select(JobCrewRequirement).where(JobCrewRequirement.job_id == job_id).order_by(JobCrewRequirement.id)
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
    return {"ok": True}


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
        .options(selectinload(JobCrewRequirement.assignments))
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

        member_skills = {sk.skill.lower() for sk in member.skills}
        member_role_ids = {r.id for r in member.preferred_roles} if member.preferred_roles else set()
        total_required: set[str] = set()
        total_matching: set[str] = set()
        required_role_ids: set[int] = set()

        for req in reqs:
            required = {_parse_skill.lower() for _parse_skill in _parse_skills(req.required_skills)}
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
