from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.jobs.models import Job, JobRequirement
from app.domain.jobs.schemas import (
    JobCreate,
    JobRead,
    JobRequirementCreate,
    JobRequirementRead,
    JobRequirementUpdate,
    JobUpdate,
)

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "jobs", "status": "scaffolded"}


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.id)).all())


@router.post("", response_model=JobRead)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=JobRead)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job


@router.get("/requirements", response_model=list[JobRequirementRead])
def list_requirements(db: Session = Depends(get_db)) -> list[JobRequirement]:
    return list(db.scalars(select(JobRequirement).order_by(JobRequirement.id)).all())


@router.post("/requirements", response_model=JobRequirementRead)
def create_requirement(payload: JobRequirementCreate, db: Session = Depends(get_db)) -> JobRequirement:
    req = JobRequirement(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.put("/requirements/{requirement_id}", response_model=JobRequirementRead)
def update_requirement(
    requirement_id: int, payload: JobRequirementUpdate, db: Session = Depends(get_db)
) -> JobRequirement:
    req = db.get(JobRequirement, requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    return req
