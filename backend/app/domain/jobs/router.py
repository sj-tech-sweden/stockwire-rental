import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.customers.models import Customer
from app.domain.jobs.models import Job, JobRequirement
from app.domain.inventory.models import Product
from app.domain.realtime.events import emit_realtime_event
from app.services.metrics import created_total, deleted_total, entities_count
from app.domain.jobs.schemas import (
    JobCreate,
    JobRead,
    JobRequirementBulkUpsert,
    JobRequirementCreate,
    JobRequirementRead,
    JobRequirementUpdate,
    JobUpdate,
)
from app.domain.projects.models import Project
from app.domain.venues.models import Venue

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "jobs", "status": "scaffolded"}


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db), project_id: int | None = None) -> list[Job]:
    stmt = select(Job).order_by(Job.id)
    if project_id is not None:
        stmt = stmt.where(Job.project_id == project_id)
    return list(db.scalars(stmt).all())


@router.get("/generate-code")
def generate_job_code(db: Session = Depends(get_db), prefix: str = "JOB-") -> dict[str, str]:
    cleaned_prefix = prefix.strip() or "JOB-"
    if len(cleaned_prefix) > 20:
        raise HTTPException(status_code=400, detail="Prefix is too long")
    return {"job_code": _generate_next_job_code(db, cleaned_prefix)}


@router.post("", response_model=JobRead)
def create_job(payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Job:
    job = Job(**_prepare_job_payload(payload.model_dump(), db))
    db.add(job)
    db.commit()
    db.refresh(job)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="job",
        entity_id=job.id,
        action="create",
        message_format="job_created",
        message_params={"jobCode": job.job_code},
        details={"job_code": job.job_code},
    )
    emit_realtime_event("jobs.updated", {"entity": "job", "action": "create", "id": job.id})
    created_total.labels(entity="job").inc()
    entities_count.labels(entity="job").inc()
    db.commit()
    return job


@router.put("/{job_id}", response_model=JobRead)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    for key, value in _prepare_job_payload(payload.model_dump(exclude_unset=True), db).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="job",
        entity_id=job.id,
        action="update",
        message_format="job_updated",
        message_params={"jobCode": job.job_code},
        details={"job_code": job.job_code},
    )
    emit_realtime_event("jobs.updated", {"entity": "job", "action": "update", "id": job.id})
    db.commit()
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> None:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job_code = job.job_code
    db.delete(job)
    db.commit()
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="job",
        entity_id=job_id,
        action="delete",
        message_format="job_deleted",
        message_params={"jobCode": job_code},
        details={"job_code": job_code},
    )
    emit_realtime_event("jobs.updated", {"entity": "job", "action": "delete", "id": job_id})
    deleted_total.labels(entity="job").inc()
    entities_count.labels(entity="job").dec()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _generate_next_job_code(db: Session, prefix: str = "JOB-") -> str:
    existing_codes = db.scalars(select(Job.job_code).where(Job.job_code.like(f"{prefix}%"))).all()
    max_number = 0
    width = 4

    for code in existing_codes:
        if not code:
            continue
        suffix = code[len(prefix):]
        if not re.fullmatch(r"\d+", suffix):
            continue
        max_number = max(max_number, int(suffix))
        width = max(width, len(suffix))

    return f"{prefix}{max_number + 1:0{width}d}"


def _prepare_job_payload(data: dict, db: Session) -> dict:
    prepared = dict(data)

    if "job_code" in prepared and prepared["job_code"] is not None:
        prepared["job_code"] = prepared["job_code"].strip()
        if not prepared["job_code"]:
            raise HTTPException(status_code=400, detail="Job code is required")

    for field in ("description", "customer_name", "venue_name", "notes"):
        if field in prepared:
            prepared[field] = _clean_text(prepared[field])

    if "invoice_paid" in prepared:
        invoice_paid = bool(prepared.get("invoice_paid"))
        if invoice_paid and not prepared.get("invoice_paid_at"):
            prepared["invoice_paid_at"] = date.today()
        if not invoice_paid and "invoice_paid_at" not in prepared:
            prepared["invoice_paid_at"] = None
    elif prepared.get("invoice_paid_at"):
        prepared["invoice_paid"] = True

    if "customer_id" in prepared:
        customer_id = prepared["customer_id"]
        if customer_id is not None:
            customer = db.get(Customer, customer_id)
            if customer is None:
                raise HTTPException(status_code=404, detail="Customer not found")
            prepared["customer_name"] = customer.name
        elif "customer_name" not in prepared:
            prepared["customer_name"] = None

    if "project_id" in prepared:
        project_id = prepared["project_id"]
        if project_id is not None:
            project = db.get(Project, project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Project not found")

    if "venue_id" in prepared:
        venue_id = prepared["venue_id"]
        if venue_id is not None:
            venue = db.get(Venue, venue_id)
            if venue is None:
                raise HTTPException(status_code=404, detail="Venue not found")
            prepared["venue_name"] = venue.name
        elif "venue_name" not in prepared:
            prepared["venue_name"] = None

    return prepared


@router.get("/requirements", response_model=list[JobRequirementRead])
def list_requirements(db: Session = Depends(get_db)) -> list[JobRequirement]:
    return list(db.scalars(select(JobRequirement).order_by(JobRequirement.id)).all())


@router.post("/requirements", response_model=JobRequirementRead)
def create_requirement(payload: JobRequirementCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> JobRequirement:
    req = JobRequirement(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    emit_realtime_event("jobs.updated", {"entity": "requirement", "action": "create", "id": req.id, "job_id": req.job_id})
    return req


@router.put("/requirements/{requirement_id}", response_model=JobRequirementRead)
def update_requirement(
    requirement_id: int, payload: JobRequirementUpdate, db: Session = Depends(get_db), _: User = Depends(require_editor)
) -> JobRequirement:
    req = db.get(JobRequirement, requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    emit_realtime_event("jobs.updated", {"entity": "requirement", "action": "update", "id": req.id, "job_id": req.job_id})
    return req


@router.put("/{job_id}/requirements/bulk", response_model=list[JobRequirementRead])
def bulk_upsert_requirements(job_id: int, payload: JobRequirementBulkUpsert, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> list[JobRequirement]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    incoming = payload.items or []
    incoming_by_product: dict[int, JobRequirementCreate] = {}
    for item in incoming:
        if item.quantity_required < 0 or item.quantity_picked < 0:
            raise HTTPException(status_code=400, detail="quantities cannot be negative")
        product = db.get(Product, item.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        incoming_by_product[item.product_id] = item

    existing = list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job_id)).all())
    existing_by_product = {req.product_id: req for req in existing}

    for product_id, item in incoming_by_product.items():
        existing_req = existing_by_product.get(product_id)
        if existing_req is None:
            db.add(
                JobRequirement(
                    job_id=job_id,
                    product_id=product_id,
                    quantity_required=item.quantity_required,
                    quantity_picked=item.quantity_picked,
                    notes=item.notes,
                )
            )
            continue

        existing_req.quantity_required = item.quantity_required
        existing_req.quantity_picked = item.quantity_picked
        existing_req.notes = item.notes

    for req in existing:
        if req.product_id not in incoming_by_product:
            db.delete(req)

    db.commit()
    emit_realtime_event("jobs.updated", {"entity": "requirement", "action": "bulk_upsert", "job_id": job_id})
    return list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job_id).order_by(JobRequirement.id)).all())
