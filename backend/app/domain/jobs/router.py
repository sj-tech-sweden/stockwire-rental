import re
import json
from datetime import date
from urllib.request import Request
from urllib.parse import urljoin
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.pagination import PaginationParams, PaginatedResponse, paginate_query
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
from app.domain.shared_schemas import ProductionPlannerSyncResponse
from app.domain.venues.models import Venue
from app.services.productionplanner import (
    ProductionPlannerClient,
    ProductionPlannerError,
    batch_task_labels,
)
from app.domain.settings.router import (
    _parse_integrations,
    _fetch_eventory_token,
    _eventory_set_headers,
    _open_outbound_integration_request,
    INTEGRATIONS_KEY,
)
from app.config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "jobs", "status": "scaffolded"}


@router.get("", response_model=PaginatedResponse[JobRead])
def list_jobs(
    db: Session = Depends(get_db),
    project_id: int | None = None,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[JobRead]:
    stmt = select(Job).order_by(Job.id)
    if project_id is not None:
        stmt = stmt.where(Job.project_id == project_id)
    items, total = paginate_query(db, stmt, pagination.skip, pagination.limit)
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


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


async def _get_productionplanner_client(db: Session) -> ProductionPlannerClient | None:
    """Get ProductionPlanner client configured from database settings."""
    from app.domain.settings.router import _get_or_create_setting, DEFAULT_INTEGRATIONS
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    parsed = _parse_integrations(setting.value_json)
    pp_config = parsed.get("productionplanner", {}) if isinstance(parsed, dict) else {}
    if not pp_config.get("enabled"):
        return None
    api_key = pp_config.get("api_key") or settings.productionplanner_api_key
    base_url = pp_config.get("base_url") or settings.productionplanner_base_url
    return ProductionPlannerClient(api_key=api_key, base_url=base_url)


async def _sync_job_to_productionplanner(job: Job, db: Session) -> ProductionPlannerSyncResponse:
    """Sync a job to ProductionPlanner as a project."""
    client = await _get_productionplanner_client(db)
    if client is None:
        return ProductionPlannerSyncResponse(
            success=False,
            message="ProductionPlanner integration is disabled",
        )
    if not client.api_key:
        return ProductionPlannerSyncResponse(
            success=False,
            message="ProductionPlanner API key not configured",
        )
    project_name = f"{job.job_code} - {job.customer_name or job.venue_name or 'Job'}"
    description_parts = []
    if job.description:
        description_parts.append(job.description)
    if job.venue_name:
        description_parts.append(f"Venue: {job.venue_name}")
    if job.location_in_venue:
        description_parts.append(f"Location: {job.location_in_venue}")
    if job.project_id:
        linked_project = db.get(Project, job.project_id)
        if linked_project:
            description_parts.append(f"Project: {linked_project.name}")

    description = "\n\n".join(description_parts) if description_parts else ""

    async with client:
        if job.productionplanner_project_id:
            await client.update_project(
                job.productionplanner_project_id,
                name=project_name,
                description=description,
            )
            pp_project_id = job.productionplanner_project_id
            date_entries: list[tuple[str, str]] = []
            if job.start_date:
                date_entries.append((job.start_date.isoformat(), "Job Start"))
            if job.end_date and job.end_date != job.start_date:
                date_entries.append((job.end_date.isoformat(), "Job End"))
            await client.sync_project_dates(pp_project_id, date_entries)
        else:
            pp_project = await client.create_project(
                name=project_name,
                description=description,
                timezone="UTC",
            )
            pp_project_id = pp_project.get("data", {}).get("id")
            if not pp_project_id:
                return ProductionPlannerSyncResponse(
                    success=False,
                    message="Failed to create project in ProductionPlanner",
                )

            if job.start_date:
                await client.add_date(
                    pp_project_id, job.start_date.isoformat(), "Job Start"
                )
            if job.end_date and job.end_date != job.start_date:
                await client.add_date(
                    pp_project_id, job.end_date.isoformat(), "Job End"
                )

            if job.venue_id:
                venue = db.get(Venue, job.venue_id)
                if venue:
                    details = []
                    if venue.address:
                        details.append(venue.address)
                    if venue.city:
                        details.append(venue.city)
                    if venue.country:
                        details.append(venue.country)
                    await client.add_location(
                        pp_project_id, venue.name, "physical", ", ".join(details)
                    )

            task_labels = [
                f"{req.product.name} x{req.quantity_required}"
                for req in job.requirements
                if req.quantity_required > 0 and req.product
            ]
            for task_label in batch_task_labels(task_labels):
                await client.add_task(pp_project_id, task_label)

    job.productionplanner_project_id = pp_project_id
    db.commit()

    return ProductionPlannerSyncResponse(
        success=True,
        message="Successfully synced to ProductionPlanner",
        productionplanner_project_id=pp_project_id,
        productionplanner_url=f"https://app.productionplanner.io/projects/{pp_project_id}",
    )


@router.post("/{job_id}/sync-productionplanner", response_model=ProductionPlannerSyncResponse)
async def sync_job_to_productionplanner(
    job_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)
) -> ProductionPlannerSyncResponse:
    """Create or update a ProductionPlanner project from this job."""
    job = db.scalar(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.requirements).selectinload(JobRequirement.product))
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        result = await _sync_job_to_productionplanner(job, db)
        if result.success:
            record_activity(
                db,
                user_id=current_user.id,
                entity_type="job",
                entity_id=job.id,
                action="sync_productionplanner",
                message_format="job_synced_productionplanner",
                message_params={"jobCode": job.job_code},
                details={"productionplanner_project_id": result.productionplanner_project_id},
            )
        return result
    except ProductionPlannerError as e:
        return ProductionPlannerSyncResponse(success=False, message=e.message)
    except Exception:
        raise


@router.get("/{job_id}/productionplanner", response_model=ProductionPlannerSyncResponse)
async def get_job_productionplanner_info(
    job_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> ProductionPlannerSyncResponse:
    """Get ProductionPlanner project info for this job (overview at a glance)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.productionplanner_project_id:
        return ProductionPlannerSyncResponse(
            success=False,
            message="Job not yet synced to ProductionPlanner",
        )

    pp_project_id = job.productionplanner_project_id
    pp_project_url = f"https://app.productionplanner.io/projects/{pp_project_id}" if pp_project_id else None

    client = await _get_productionplanner_client(db)
    if client is None:
        return ProductionPlannerSyncResponse(
            success=False,
            message="ProductionPlanner integration is disabled",
            productionplanner_project_id=pp_project_id,
            productionplanner_url=pp_project_url,
        )
    if not client.api_key:
        return ProductionPlannerSyncResponse(
            success=False,
            message="ProductionPlanner API key not configured",
            productionplanner_project_id=pp_project_id,
            productionplanner_url=pp_project_url,
        )

    async with client:
        try:
            project = await client.get_project(job.productionplanner_project_id)
            data = project.get("data", {})
            return ProductionPlannerSyncResponse(
                success=True,
                message=f"Project: {data.get('name', 'Unknown')}",
                productionplanner_project_id=pp_project_id,
                productionplanner_url=pp_project_url,
            )
        except ProductionPlannerError as e:
            return ProductionPlannerSyncResponse(
                success=False,
                message=f"Failed to fetch project: {e.message}",
                productionplanner_project_id=pp_project_id,
                productionplanner_url=pp_project_url,
            )


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
                    is_scannable=item.is_scannable,
                    notes=item.notes,
                )
            )
            continue

        existing_req.quantity_required = item.quantity_required
        existing_req.quantity_picked = item.quantity_picked
        existing_req.is_scannable = item.is_scannable
        existing_req.notes = item.notes

    for req in existing:
        if req.product_id not in incoming_by_product:
            db.delete(req)

    db.commit()
    emit_realtime_event("jobs.updated", {"entity": "requirement", "action": "bulk_upsert", "job_id": job_id})
    return list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job_id).order_by(JobRequirement.id)).all())


# ── Eventory Rental Job Creation ─────────────────────────────────────────────


class CreateEventoryRentalsRequest(BaseModel):
    instance_id: str


@router.post("/{job_id}/create-eventory-rentals", response_model=JobRead)
def create_eventory_rentals(
    job_id: int,
    payload: CreateEventoryRentalsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> JobRead:
    job = db.execute(
        select(Job).where(Job.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    integrations = _parse_integrations(_get_integrations_json(db))
    instances = integrations.get("eventory_instances", [])
    instance = next((i for i in instances if i.get("id") == payload.instance_id), None)
    if not instance:
        raise HTTPException(status_code=404, detail="Eventory instance not found")

    if not instance.get("create_jobs"):
        raise HTTPException(status_code=400, detail="Job creation is disabled for this Eventory instance")

    rental_customer_id = str(instance.get("rental_customer_id") or "").strip()
    if not rental_customer_id:
        raise HTTPException(status_code=400, detail="Rental customer ID is not configured for this Eventory instance")

    api_url = str(instance.get("api_url") or "").strip()
    api_key = str(instance.get("api_key") or "").strip()
    username = str(instance.get("username") or "").strip()
    password = str(instance.get("password") or "").strip()
    token_endpoint = str(instance.get("token_endpoint") or "").strip()

    oauth_token = ""
    if username and password:
        oauth_token = _fetch_eventory_token(api_url, token_endpoint, username, password)

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    _eventory_set_headers(headers, oauth_token, api_key)

    requirements = list(db.scalars(
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .options(selectinload(JobRequirement.product))
    ).all())

    instance_id = payload.instance_id
    rental_reqs = [
        r for r in requirements
        if r.product
        and r.product.is_rental_product
        and r.product.external_reference
        and r.product.external_reference.startswith(f"{instance_id}:")
    ]

    if not rental_reqs:
        raise HTTPException(status_code=400, detail="No Eventory rental products found for this instance")

    if not job.start_date or not job.end_date:
        raise HTTPException(
            status_code=400,
            detail="Job must have start and end dates to create an Eventory booking. Please set dates on the job first.",
        )

    eventory_job_id = _create_eventory_job(
        api_url, headers, job, rental_customer_id
    )

    pack_list_id = _create_eventory_pack_list(
        api_url, headers, eventory_job_id, job.job_code
    )

    for req in rental_reqs:
        external_ref = req.product.external_reference or ""
        eventory_rental_id = external_ref.split(":", 1)[1] if ":" in external_ref else ""
        if not eventory_rental_id:
            continue
        _create_eventory_pack_list_rental(
            api_url, headers, pack_list_id, eventory_rental_id, req.quantity_required
        )

    eventory_ids = json.loads(job.eventory_job_ids or "{}") if job.eventory_job_ids else {}
    eventory_ids[instance_id] = eventory_job_id
    job.eventory_job_ids = json.dumps(eventory_ids)
    db.commit()
    db.refresh(job)

    return JobRead.model_validate(job)


@router.post("/{job_id}/update-eventory-rentals", response_model=JobRead)
def update_eventory_rentals(
    job_id: int,
    payload: CreateEventoryRentalsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> JobRead:
    job = db.execute(
        select(Job).where(Job.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.start_date or not job.end_date:
        raise HTTPException(
            status_code=400,
            detail="Job must have start and end dates to update an Eventory booking.",
        )

    eventory_ids = json.loads(job.eventory_job_ids or "{}") if job.eventory_job_ids else {}
    eventory_job_id = eventory_ids.get(payload.instance_id)
    if not eventory_job_id:
        raise HTTPException(status_code=400, detail="No Eventory booking found for this instance. Create one first.")

    integrations = _parse_integrations(_get_integrations_json(db))
    instances = integrations.get("eventory_instances", [])
    instance = next((i for i in instances if i.get("id") == payload.instance_id), None)
    if not instance:
        raise HTTPException(status_code=404, detail="Eventory instance not found")

    api_url = str(instance.get("api_url") or "").strip()
    api_key = str(instance.get("api_key") or "").strip()
    username = str(instance.get("username") or "").strip()
    password = str(instance.get("password") or "").strip()
    token_endpoint = str(instance.get("token_endpoint") or "").strip()

    oauth_token = ""
    if username and password:
        oauth_token = _fetch_eventory_token(api_url, token_endpoint, username, password)

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    _eventory_set_headers(headers, oauth_token, api_key)

    requirements = list(db.scalars(
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .options(selectinload(JobRequirement.product))
    ).all())

    instance_id = payload.instance_id
    rental_reqs = [
        r for r in requirements
        if r.product
        and r.product.is_rental_product
        and r.product.external_reference
        and r.product.external_reference.startswith(f"{instance_id}:")
    ]

    _update_eventory_job(api_url, headers, eventory_job_id, job)

    pack_list_id = _get_or_create_eventory_pack_list(
        api_url, headers, eventory_job_id, job.job_code
    )

    _sync_eventory_pack_list_rentals(
        api_url, headers, pack_list_id, rental_reqs, instance_id
    )

    return JobRead.model_validate(job)


class VerifyEventoryRequest(BaseModel):
    instance_id: str
    eventory_job_id: str


class VerifyEventoryResponse(BaseModel):
    exists: bool


@router.post("/verify-eventory-job", response_model=VerifyEventoryResponse)
def verify_eventory_job(
    payload: VerifyEventoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerifyEventoryResponse:
    integrations = _parse_integrations(_get_integrations_json(db))
    instances = integrations.get("eventory_instances", [])
    instance = next((i for i in instances if i.get("id") == payload.instance_id), None)
    if not instance:
        return VerifyEventoryResponse(exists=False)

    api_url = str(instance.get("api_url") or "").strip()
    api_key = str(instance.get("api_key") or "").strip()
    username = str(instance.get("username") or "").strip()
    password = str(instance.get("password") or "").strip()
    token_endpoint = str(instance.get("token_endpoint") or "").strip()

    oauth_token = ""
    if username and password:
        try:
            oauth_token = _fetch_eventory_token(api_url, token_endpoint, username, password)
        except Exception:
            return VerifyEventoryResponse(exists=False)

    headers = {"Accept": "application/json"}
    _eventory_set_headers(headers, oauth_token, api_key)

    job_url = urljoin(api_url.rstrip("/") + "/", f"jobs/{payload.eventory_job_id}")
    req = Request(job_url, headers=headers, method="GET")
    try:
        with _open_outbound_integration_request(req, timeout=10) as resp:
            status_code = getattr(resp, "status", 200)
            if status_code == 200:
                data = json.loads(resp.read().decode("utf-8") or "{}")
                return VerifyEventoryResponse(exists=bool(data.get("id")))
            return VerifyEventoryResponse(exists=False)
    except Exception:
        # Network or parsing error — treat as not found
        return VerifyEventoryResponse(exists=False)


def _get_integrations_json(db: Session) -> str:
    from app.domain.settings.models import AppSetting
    setting = db.execute(select(AppSetting).where(AppSetting.key == INTEGRATIONS_KEY)).scalar_one_or_none()
    return setting.value_json or "{}" if setting else "{}"


def _create_eventory_job(api_url: str, headers: dict, job: Job, customer_id: str) -> str:
    job_url = urljoin(api_url.rstrip("/") + "/", "jobs")
    body = json.dumps({
        "name": job.job_code,
        "customer_id": customer_id,
        "startDate": job.start_date.isoformat() if job.start_date else None,
        "endDate": job.end_date.isoformat() if job.end_date else None,
        "status": "quotation",
        "note": f"Created from Stockwire job {job.job_code}",
    }).encode("utf-8")
    req = Request(job_url, data=body, headers=headers, method="POST")
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            job_id = str(data.get("id") or "").strip()
            if not job_id:
                raise HTTPException(status_code=502, detail=f"Eventory API returned no job ID: {data}")
            return job_id
    except HTTPException:
        raise
    except HTTPError as exc:
        error_body = ""
        if exc.fp:
            try:
                error_body = exc.fp.read().decode("utf-8", errors="replace")
            except Exception:
                # Response body may be unreadable — use reason phrase instead
                pass
        raise HTTPException(
            status_code=502,
            detail=f"Eventory job creation failed (HTTP {exc.code}): {error_body or str(exc.reason)}"
        )
    except (URLError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create Eventory job: {exc}")


def _create_eventory_pack_list(api_url: str, headers: dict, eventory_job_id: str, job_code: str) -> str:
    pl_url = urljoin(api_url.rstrip("/") + "/", "pack-lists")
    body = json.dumps({
        "name": f"Stockwire - {job_code}",
        "job_id": eventory_job_id,
    }).encode("utf-8")
    req = Request(pl_url, data=body, headers=headers, method="POST")
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            pl_id = str(data.get("id") or "").strip()
            if not pl_id:
                raise HTTPException(status_code=502, detail=f"Eventory API returned no pack list ID: {data}")
            return pl_id
    except HTTPException:
        raise
    except HTTPError as exc:
        error_body = ""
        if exc.fp:
            try:
                error_body = exc.fp.read().decode("utf-8", errors="replace")
            except Exception:
                # Response body may be unreadable
                pass
        raise HTTPException(
            status_code=502,
            detail=f"Eventory pack list creation failed (HTTP {exc.code}): {error_body or str(exc.reason)}"
        )
    except (URLError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create Eventory pack list: {exc}")


def _create_eventory_pack_list_rental(
    api_url: str, headers: dict, pack_list_id: str, rental_id: str, quantity: int
) -> None:
    plr_url = urljoin(api_url.rstrip("/") + "/", "pack-list-rentals")
    body = json.dumps({
        "packList_id": pack_list_id,
        "rental_id": rental_id,
        "quantity": quantity,
    }).encode("utf-8")
    req = Request(plr_url, data=body, headers=headers, method="POST")
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            status_code = getattr(resp, "status", 200)
            if status_code and status_code >= 400:
                error_body = ""
                try:
                    error_body = resp.read().decode("utf-8", errors="replace")
                except Exception:
                    # Response body may be unreadable
                    pass
                raise HTTPException(
                    status_code=502,
                    detail=f"Eventory pack list rental failed (HTTP {status_code}): {error_body}"
                )
    except HTTPException:
        raise
    except HTTPError as exc:
        error_body = ""
        if exc.fp:
            try:
                error_body = exc.fp.read().decode("utf-8", errors="replace")
            except Exception:
                # Response body may be unreadable
                pass
        raise HTTPException(
            status_code=502,
            detail=f"Eventory pack list rental failed (HTTP {exc.code}): {error_body or str(exc.reason)}"
        )
    except (URLError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create Eventory pack list rental: {exc}")


def _update_eventory_job(api_url: str, headers: dict, eventory_job_id: str, job: Job) -> None:
    job_url = urljoin(api_url.rstrip("/") + "/", f"jobs/{eventory_job_id}")
    body = json.dumps({
        "name": job.job_code,
        "startDate": job.start_date.isoformat() if job.start_date else None,
        "endDate": job.end_date.isoformat() if job.end_date else None,
    }).encode("utf-8")
    req = Request(job_url, data=body, headers=headers, method="PUT")
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            pass
    except HTTPException:
        raise
    except HTTPError as exc:
        error_body = ""
        if exc.fp:
            try:
                error_body = exc.fp.read().decode("utf-8", errors="replace")
            except Exception:
                # Response body may be unreadable
                pass
        raise HTTPException(
            status_code=502,
            detail=f"Eventory job update failed (HTTP {exc.code}): {error_body or str(exc.reason)}"
        )
    except (URLError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to update Eventory job: {exc}")


def _get_or_create_eventory_pack_list(api_url: str, headers: dict, eventory_job_id: str, job_code: str) -> str:
    list_url = urljoin(api_url.rstrip("/") + "/", "jobs/list")
    req = Request(list_url, headers=headers, method="GET")
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8") or "[]")
            if isinstance(data, list):
                for item in data:
                    if str(item.get("id") or "") == eventory_job_id:
                        pack_lists = item.get("packLists") or []
                        if pack_lists:
                            return str(pack_lists[0].get("id") or "")
    except Exception:
        # Best-effort: ignore errors from secondary API calls
        pass

    return _create_eventory_pack_list(api_url, headers, eventory_job_id, job_code)


def _sync_eventory_pack_list_rentals(
    api_url: str, headers: dict, pack_list_id: str, rental_reqs: list, instance_id: str
) -> None:
    list_url = urljoin(api_url.rstrip("/") + "/", f"pack-lists/details/{pack_list_id}")
    req = Request(list_url, headers=headers, method="GET")
    existing_rentals = {}
    try:
        with _open_outbound_integration_request(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            for item in data.get("rentals") or []:
                rental_id = str(item.get("rental_id") or item.get("id") or "")
                if rental_id:
                    existing_rentals[rental_id] = str(item.get("id") or "")
    except Exception:
        # Best-effort: ignore errors from secondary API calls
        pass

    desired_rental_ids = set()
    for req in rental_reqs:
        external_ref = req.product.external_reference or ""
        eventory_rental_id = external_ref.split(":", 1)[1] if ":" in external_ref else ""
        if eventory_rental_id:
            desired_rental_ids.add(eventory_rental_id)

    for rental_id, plr_id in existing_rentals.items():
        if rental_id not in desired_rental_ids:
            _delete_eventory_pack_list_rental(api_url, headers, plr_id)

    for req in rental_reqs:
        external_ref = req.product.external_reference or ""
        eventory_rental_id = external_ref.split(":", 1)[1] if ":" in external_ref else ""
        if not eventory_rental_id:
            continue
        if eventory_rental_id in existing_rentals:
            plr_id = existing_rentals[eventory_rental_id]
            _update_eventory_pack_list_rental(api_url, headers, plr_id, req.quantity_required)
        else:
            _create_eventory_pack_list_rental(
                api_url, headers, pack_list_id, eventory_rental_id, req.quantity_required
            )


def _delete_eventory_pack_list_rental(api_url: str, headers: dict, plr_id: str) -> None:
    url = urljoin(api_url.rstrip("/") + "/", f"pack-list-rentals/{plr_id}")
    req = Request(url, headers=headers, method="DELETE")
    try:
        with _open_outbound_integration_request(req, timeout=10) as resp:
            pass
    except Exception:
        # Best-effort: ignore errors from secondary API calls
        pass


def _update_eventory_pack_list_rental(api_url: str, headers: dict, plr_id: str, quantity: int) -> None:
    url = urljoin(api_url.rstrip("/") + "/", f"pack-list-rentals/{plr_id}")
    body = json.dumps({"quantity": quantity}).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="PUT")
    try:
        with _open_outbound_integration_request(req, timeout=10) as resp:
            pass
    except Exception:
        # Best-effort: ignore errors from secondary API calls
        pass
