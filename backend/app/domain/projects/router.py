from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain.audit.service import record_activity
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.customers.models import Customer
from app.domain.jobs.models import Job, JobRequirement
from app.domain.projects.models import Project
from app.domain.shared_schemas import ProductionPlannerSyncResponse
from app.domain.venues.models import Venue
from app.domain.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.domain.realtime.events import emit_realtime_event
from app.services.metrics import created_total, deleted_total, entities_count
from app.services.productionplanner import (
    ProductionPlannerClient,
    ProductionPlannerError,
    batch_task_labels,
)
from app.domain.settings.router import _parse_integrations, INTEGRATIONS_KEY
from app.domain.settings.router import _get_or_create_setting, DEFAULT_INTEGRATIONS
from app.config import settings

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "projects", "status": "scaffolded"}


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> Project:
    data = payload.model_dump()
    if data.get("customer_id") is not None:
        customer = db.get(Customer, data["customer_id"])
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    if data.get("venue_id") is not None:
        venue = db.get(Venue, data["venue_id"])
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")

    project = Project(**data)
    db.add(project)
    db.commit()
    db.refresh(project)
    emit_realtime_event("projects.updated", {"entity": "project", "action": "create", "id": project.id})
    created_total.labels(entity="project").inc()
    entities_count.labels(entity="project").inc()
    db.commit()
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    data = payload.model_dump(exclude_unset=True)
    if "customer_id" in data and data["customer_id"] is not None:
        customer = db.get(Customer, data["customer_id"])
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    if "venue_id" in data and data["venue_id"] is not None:
        venue = db.get(Venue, data["venue_id"])
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")

    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    emit_realtime_event("projects.updated", {"entity": "project", "action": "update", "id": project.id})
    db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    jobs = list(db.scalars(select(Job).where(Job.project_id == project_id)).all())
    for job in jobs:
        job.project_id = None

    db.delete(project)
    db.commit()
    emit_realtime_event("projects.updated", {"entity": "project", "action": "delete", "id": project_id})
    deleted_total.labels(entity="project").inc()
    entities_count.labels(entity="project").dec()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _get_productionplanner_client(db: Session) -> ProductionPlannerClient | None:
    """Get ProductionPlanner client configured from database settings."""
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    parsed = _parse_integrations(setting.value_json)
    pp_config = parsed.get("productionplanner", {}) if isinstance(parsed, dict) else {}
    if not pp_config.get("enabled"):
        return None
    api_key = pp_config.get("api_key") or settings.productionplanner_api_key
    base_url = pp_config.get("base_url") or settings.productionplanner_base_url
    return ProductionPlannerClient(api_key=api_key, base_url=base_url)


async def _sync_project_to_productionplanner(project: Project, db: Session) -> ProductionPlannerSyncResponse:
    """Sync a project to ProductionPlanner as a project."""
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

    project_name = project.name
    description_parts = []
    if project.description:
        description_parts.append(project.description)
    if project.start_date:
        description_parts.append(f"Project dates: {project.start_date} to {project.end_date or project.start_date}")
    if project.customer_id:
        customer = db.get(Customer, project.customer_id)
        if customer:
            description_parts.append(f"Customer: {customer.name}")
    if project.venue_id:
        venue = db.get(Venue, project.venue_id)
        if venue:
            description_parts.append(f"Venue: {venue.name}")

    description = "\n\n".join(description_parts) if description_parts else ""

    async with client:
        if project.productionplanner_project_id:
            await client.update_project(
                project.productionplanner_project_id,
                name=project_name,
                description=description,
            )
            pp_project_id = project.productionplanner_project_id
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

            if project.start_date:
                await client.add_date(
                    pp_project_id, project.start_date.isoformat(), "Project Start"
                )
            if project.end_date and project.end_date != project.start_date:
                await client.add_date(
                    pp_project_id, project.end_date.isoformat(), "Project End"
                )

            if project.venue_id:
                venue = db.get(Venue, project.venue_id)
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

            jobs = list(
                db.scalars(
                    select(Job)
                    .where(Job.project_id == project.id)
                    .options(selectinload(Job.requirements).selectinload(JobRequirement.product))
                ).all()
            )
            task_labels = [
                f"[{job.job_code}] {req.product.name} x{req.quantity_required}"
                for job in jobs
                for req in job.requirements
                if req.quantity_required > 0 and req.product
            ]
            for task_label in batch_task_labels(task_labels):
                await client.add_task(pp_project_id, task_label)

    project.productionplanner_project_id = pp_project_id
    db.commit()

    return ProductionPlannerSyncResponse(
        success=True,
        message="Successfully synced to ProductionPlanner",
        productionplanner_project_id=pp_project_id,
        productionplanner_url=f"https://app.productionplanner.io/projects/{pp_project_id}",
    )


@router.post("/{project_id}/sync-productionplanner", response_model=ProductionPlannerSyncResponse)
async def sync_project_to_productionplanner(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)
) -> ProductionPlannerSyncResponse:
    """Create or update a ProductionPlanner project from this project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = await _sync_project_to_productionplanner(project, db)
        if result.success:
            record_activity(
                db,
                user_id=current_user.id,
                entity_type="project",
                entity_id=project.id,
                action="sync_productionplanner",
                message_format="project_synced_productionplanner",
                message_params={"projectName": project.name},
                details={"productionplanner_project_id": result.productionplanner_project_id},
            )
        return result
    except ProductionPlannerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{project_id}/productionplanner", response_model=ProductionPlannerSyncResponse)
async def get_project_productionplanner_info(
    project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> ProductionPlannerSyncResponse:
    """Get ProductionPlanner project info for this project (overview at a glance)."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.productionplanner_project_id:
        return ProductionPlannerSyncResponse(
            success=False,
            message="Project not yet synced to ProductionPlanner",
        )

    pp_project_id = project.productionplanner_project_id
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
            pp_project = await client.get_project(project.productionplanner_project_id)
            data = pp_project.get("data", {})
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