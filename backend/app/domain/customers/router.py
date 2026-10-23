import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)

from app.api.pagination import PaginationParams, PaginatedResponse, paginate_query
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.customers.models import Company, Person
from app.domain.customers.schemas import (
    CompanyCreate,
    CompanyCrewMemberSummary,
    CompanyInfoRead,
    CompanyJobSummary,
    CompanyProductSummary,
    CompanyRead,
    CompanyUpdate,
    PersonCreate,
    PersonInfoRead,
    PersonRead,
    PersonSummary,
    PersonUpdate,
)
from app.domain.settings.accessors import get_company_profile_default_language
from app.domain.inventory.models import Device, ProductSupplier
from app.services.metrics import created_total, deleted_total, entities_count
from app.domain.jobs.models import Job
from app.domain.realtime.events import emit_realtime_event
from app.domain.integrations.outbound import push_company_to_twenty, push_person_to_twenty

companies_router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(get_current_user)])


@companies_router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "companies", "status": "scaffolded"}


@companies_router.get("", response_model=PaginatedResponse[CompanyRead])
def list_companies(
    type: str | None = Query(None, description="Filter by type: customer, product_supplier, rental_supplier, crew_supplier"),
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[CompanyRead]:
    stmt = select(Company).order_by(Company.name, Company.id)
    if type == "customer":
        stmt = stmt.where(Company.is_customer.is_(True))
    elif type == "product_supplier":
        stmt = stmt.where(Company.is_product_supplier.is_(True))
    elif type == "rental_supplier":
        stmt = stmt.where(Company.is_rental_supplier.is_(True))
    elif type == "crew_supplier":
        stmt = stmt.where(Company.is_crew_supplier.is_(True))
    items, total = paginate_query(db, stmt, pagination.skip, pagination.limit)
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@companies_router.get("/{company_id}/info", response_model=CompanyInfoRead)
def get_company_info(company_id: int, db: Session = Depends(get_db)) -> CompanyInfoRead:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = CompanyInfoRead(
        id=company.id,
        name=company.name,
        address=company.address,
        city=company.city,
        postal_code=company.postal_code,
        country=company.country,
        notes=company.notes,
        external_source=company.external_source,
        external_reference=company.external_reference,
        external_origin=company.external_origin,
        is_customer=company.is_customer,
        is_product_supplier=company.is_product_supplier,
        is_rental_supplier=company.is_rental_supplier,
        is_crew_supplier=company.is_crew_supplier,
        email_notifications_enabled=company.email_notifications_enabled,
        preferred_language=company.preferred_language,
        created_at=company.created_at,
    )

    # Load persons
    persons = list(db.scalars(
        select(Person).where(Person.company_id == company_id).order_by(Person.last_name, Person.first_name)
    ).all())
    result.persons = [
        PersonSummary(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            email=p.email,
            phone=p.phone,
        )
        for p in persons
    ]

    if company.is_customer:
        jobs = list(db.scalars(
            select(Job).where(Job.company_id == company_id).order_by(Job.id.desc())
        ).all())
        result.jobs = [
            CompanyJobSummary(
                id=j.id,
                job_code=j.job_code,
                status=j.status,
                description=j.description,
                start_date=j.start_date,
                end_date=j.end_date,
                venue_name=j.venue_name,
            )
            for j in jobs
        ]

    if company.is_product_supplier or company.is_rental_supplier:
        ps_rows = list(db.scalars(
            select(ProductSupplier)
            .where(ProductSupplier.supplier_company_id == company_id)
            .options(selectinload(ProductSupplier.product))
        ).all())
        products = [ps.product for ps in ps_rows if ps.product]
        if company.is_rental_supplier and not company.is_product_supplier:
            products = [p for p in products if p.is_rental_product]
        result.supplied_products = [
            CompanyProductSummary(
                id=p.id,
                sku=p.sku,
                name=p.name,
                product_type=p.product_type,
                is_rental_product=p.is_rental_product,
                rental_price=float(p.rental_price or 0),
                daily_rate=float(p.daily_rate or 0),
                category=p.category,
            )
            for p in products
        ]

    if company.is_crew_supplier:
        from app.domain.crew.models import CrewMember

        crew_members = list(db.scalars(
            select(CrewMember)
            .join(Person, CrewMember.person_id == Person.id)
            .where(Person.company_id == company_id)
            .options(
                selectinload(CrewMember.skills),
                selectinload(CrewMember.certifications),
                selectinload(CrewMember.preferred_roles),
            )
            .order_by(Person.last_name, Person.first_name)
        ).all())
        result.crew_members = [
            CompanyCrewMemberSummary(
                id=cm.id,
                name=cm.name,
                email=cm.email,
                phone=cm.phone,
                user_id=cm.user_id,
                supplier_id=cm.supplier_id,
                person_id=cm.person_id,
                hourly_rate=float(cm.hourly_rate) if cm.hourly_rate else None,
                daily_rate=float(cm.daily_rate) if cm.daily_rate else None,
                is_active=cm.is_active,
                skills=[sk.skill.name for sk in cm.skills] if cm.skills else [],
                certifications=[
                    {"certification": c.certification.name if c.certification else None, "expires_at": c.expiry_date.isoformat() if c.expiry_date else None}
                    for c in cm.certifications
                ] if cm.certifications else [],
                preferred_role_ids=[r.id for r in cm.preferred_roles] if cm.preferred_roles else [],
                preferred_role_names=[r.name for r in cm.preferred_roles] if cm.preferred_roles else [],
                notes=cm.notes,
            )
            for cm in crew_members
        ]

    return result


@companies_router.post("", response_model=CompanyRead)
def create_company(payload: CompanyCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Company:
    company = Company(**payload.model_dump())
    if not company.preferred_language:
        company.preferred_language = get_company_profile_default_language(db)
    db.add(company)
    db.flush()
    db.refresh(company)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="company",
        entity_id=company.id,
        action="create",
        message_format="company_created",
        message_params={"name": company.name},
        details={"name": company.name},
    )
    emit_realtime_event("companies.updated", {"entity": "company", "action": "create", "id": company.id})
    created_total.labels(entity="company").inc()
    entities_count.labels(entity="company").inc()
    db.commit()
    background_tasks.add_task(push_company_to_twenty, company.id)
    return company


@companies_router.put("/{company_id}", response_model=CompanyRead)
def update_company(company_id: int, payload: CompanyUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.flush()
    db.refresh(company)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="company",
        entity_id=company.id,
        action="update",
        message_format="company_updated",
        message_params={"name": company.name},
        details={"name": company.name},
    )
    emit_realtime_event("companies.updated", {"entity": "company", "action": "update", "id": company.id})
    db.commit()
    background_tasks.add_task(push_company_to_twenty, company.id)
    return company


@companies_router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> None:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check for linked products
    linked_products = list(db.scalars(
        select(ProductSupplier).where(ProductSupplier.supplier_company_id == company_id)
    ).all())
    if linked_products:
        product_ids = [ps.product_id for ps in linked_products]
        raise HTTPException(
            status_code=409,
            detail={
                "error": "supplier_has_products",
                "message": f"Cannot delete: linked to {len(linked_products)} product(s)",
                "product_ids": product_ids,
            },
        )

    # Check for linked devices
    linked_devices = list(db.scalars(
        select(Device).where(Device.supplier_id == company_id)
    ).all())
    if linked_devices:
        device_ids = [d.id for d in linked_devices]
        raise HTTPException(
            status_code=409,
            detail={
                "error": "supplier_has_devices",
                "message": f"Cannot delete: linked to {len(linked_devices)} device(s)",
                "device_ids": device_ids,
            },
        )

    # Unlink jobs from this company
    company_name = company.name
    company_external_ref = company.external_reference
    jobs = list(db.scalars(select(Job).where(Job.company_id == company_id)).all())
    for job in jobs:
        job.company_id = None
        job.contact_person_id = None

    db.delete(company)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="company",
        entity_id=company_id,
        action="delete",
        message_format="company_deleted",
        message_params={"name": company_name},
        details={"name": company_name},
    )
    emit_realtime_event("companies.updated", {"entity": "company", "action": "delete", "id": company_id})
    deleted_total.labels(entity="company").inc()
    entities_count.labels(entity="company").dec()
    db.commit()

    # Delete from Twenty CRM if it has a Twenty reference
    if company_external_ref:
        try:
            from app.domain.integrations.models import TwentyConfig
            from app.domain.integrations.twenty_client import TwentyClient

            config = db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first()
            if config and config.api_key:
                client = TwentyClient(api_key=config.api_key, base_url=config.base_url)
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(client.delete_object("companies", company_external_ref))
                    logger.info("Deleted company %s from Twenty CRM", company_external_ref)
                except Exception as e:
                    logger.warning("Failed to delete company from Twenty: %s", e)
                finally:
                    loop.close()
        except Exception as e:
            logger.warning("Failed to delete company from Twenty: %s", e)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Person Endpoints
# ============================================================================

persons_router = APIRouter(prefix="/persons", tags=["persons"], dependencies=[Depends(get_current_user)])


@persons_router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "persons", "status": "scaffolded"}


@persons_router.get("", response_model=PaginatedResponse[PersonRead])
def list_persons(
    company_id: int | None = Query(None, description="Filter by company ID"),
    search: str | None = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[PersonRead]:
    stmt = select(Person).order_by(Person.last_name, Person.first_name, Person.id)
    if company_id is not None:
        stmt = stmt.where(Person.company_id == company_id)
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (Person.first_name.ilike(search_filter))
            | (Person.last_name.ilike(search_filter))
            | (Person.email.ilike(search_filter))
        )
    items, total = paginate_query(db, stmt, pagination.skip, pagination.limit)

    result_items = []
    for person in items:
        person_read = PersonRead.model_validate(person)
        if person.company_id:
            company = db.get(Company, person.company_id)
            if company:
                person_read.company_name = company.name
        result_items.append(person_read)

    return PaginatedResponse(
        items=result_items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@persons_router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonRead:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    result = PersonRead.model_validate(person)
    if person.company_id:
        company = db.get(Company, person.company_id)
        if company:
            result.company_name = company.name
    return result


@persons_router.get("/{person_id}/info", response_model=PersonInfoRead)
def get_person_info(person_id: int, db: Session = Depends(get_db)) -> PersonInfoRead:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    result = PersonInfoRead.model_validate(person)
    if person.company_id:
        company = db.get(Company, person.company_id)
        if company:
            result.company_name = company.name
    if person.crew_member:
        cm = person.crew_member
        result.crew_member_id = cm.id
        result.crew_member_name = cm.name
        result.crew_member_email = cm.email
        result.crew_member_phone = cm.phone
        result.crew_member_hourly_rate = float(cm.hourly_rate) if cm.hourly_rate else None
        result.crew_member_daily_rate = float(cm.daily_rate) if cm.daily_rate else None
        result.crew_member_is_active = cm.is_active
        result.crew_member_skills = [sk.skill.name for sk in cm.skills] if cm.skills else []
        result.crew_member_certifications = [c.certification.name for c in cm.certifications] if cm.certifications else []
        result.crew_member_preferred_roles = [r.name for r in cm.preferred_roles] if cm.preferred_roles else []
    return result


@persons_router.post("", response_model=PersonRead)
def create_person(payload: PersonCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Person:
    person = Person(**payload.model_dump())
    if not person.preferred_language:
        person.preferred_language = get_company_profile_default_language(db)
    db.add(person)
    db.flush()
    db.refresh(person)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="person",
        entity_id=person.id,
        action="create",
        message_format="person_created",
        message_params={"name": f"{person.first_name} {person.last_name}"},
        details={"first_name": person.first_name, "last_name": person.last_name},
    )
    emit_realtime_event("persons.updated", {"entity": "person", "action": "create", "id": person.id})
    created_total.labels(entity="person").inc()
    entities_count.labels(entity="person").inc()
    db.commit()
    background_tasks.add_task(push_person_to_twenty, person.id)
    return person


@persons_router.put("/{person_id}", response_model=PersonRead)
def update_person(person_id: int, payload: PersonUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, key, value)
    db.flush()
    db.refresh(person)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="person",
        entity_id=person.id,
        action="update",
        message_format="person_updated",
        message_params={"name": f"{person.first_name} {person.last_name}"},
        details={"first_name": person.first_name, "last_name": person.last_name},
    )
    emit_realtime_event("persons.updated", {"entity": "person", "action": "update", "id": person.id})
    db.commit()
    background_tasks.add_task(push_person_to_twenty, person.id)
    return person


@persons_router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> None:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    # Check if person is linked to a crew member
    if person.crew_member:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "person_has_crew_member",
                "message": "Cannot delete: person is linked to a crew member",
                "crew_member_id": person.crew_member.id,
            },
        )

    person_name = f"{person.first_name} {person.last_name}"
    person_external_ref = person.external_reference
    db.delete(person)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="person",
        entity_id=person_id,
        action="delete",
        message_format="person_deleted",
        message_params={"name": person_name},
        details={"name": person_name},
    )
    emit_realtime_event("persons.updated", {"entity": "person", "action": "delete", "id": person_id})
    deleted_total.labels(entity="person").inc()
    entities_count.labels(entity="person").dec()
    db.commit()

    # Delete from Twenty CRM if it has a Twenty reference
    if person_external_ref:
        try:
            from app.domain.integrations.models import TwentyConfig
            from app.domain.integrations.twenty_client import TwentyClient

            config = db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first()
            if config and config.api_key:
                client = TwentyClient(api_key=config.api_key, base_url=config.base_url)
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(client.delete_object("people", person_external_ref))
                    logger.info("Deleted person %s from Twenty CRM", person_external_ref)
                except Exception as e:
                    logger.warning("Failed to delete person from Twenty: %s", e)
                finally:
                    loop.close()
        except Exception as e:
            logger.warning("Failed to delete person from Twenty: %s", e)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
