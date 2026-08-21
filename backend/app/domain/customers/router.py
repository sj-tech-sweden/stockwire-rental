from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.pagination import PaginationParams, PaginatedResponse, paginate_query
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.customers.models import Company, Customer, Person
from app.domain.customers.schemas import (
    CompanyCreate,
    CompanyCrewMemberSummary,
    CompanyInfoRead,
    CompanyJobSummary,
    CompanyProductSummary,
    CompanyRead,
    CompanyUpdate,
    CustomerCreate,
    CustomerCrewMemberSummary,
    CustomerInfoRead,
    CustomerJobSummary,
    CustomerProductSummary,
    CustomerRead,
    CustomerUpdate,
    PersonCreate,
    PersonInfoRead,
    PersonRead,
    PersonSummary,
    PersonUpdate,
)
from app.domain.inventory.models import Device, ProductSupplier
from app.services.metrics import created_total, deleted_total, entities_count
from app.domain.jobs.models import Job
from app.domain.realtime.events import emit_realtime_event

customers_router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


@customers_router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "customers", "status": "scaffolded"}


@customers_router.get("", response_model=PaginatedResponse[CustomerRead])
def list_customers(
    type: str | None = Query(None, description="Filter by type: customer, product_supplier, rental_supplier, crew_supplier"),
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[CustomerRead]:
    stmt = select(Customer).order_by(Customer.name, Customer.id)
    if type == "customer":
        stmt = stmt.where(Customer.is_customer.is_(True))
    elif type == "product_supplier":
        stmt = stmt.where(Customer.is_product_supplier.is_(True))
    elif type == "rental_supplier":
        stmt = stmt.where(Customer.is_rental_supplier.is_(True))
    elif type == "crew_supplier":
        stmt = stmt.where(Customer.is_crew_supplier.is_(True))
    items, total = paginate_query(db, stmt, pagination.skip, pagination.limit)
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@customers_router.get("/{customer_id}/info", response_model=CustomerInfoRead)
def get_customer_info(customer_id: int, db: Session = Depends(get_db)) -> CustomerInfoRead:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = CustomerInfoRead(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        postal_code=customer.postal_code,
        country=customer.country,
        notes=customer.notes,
        external_source=customer.external_source,
        external_reference=customer.external_reference,
        is_customer=customer.is_customer,
        is_product_supplier=customer.is_product_supplier,
        is_rental_supplier=customer.is_rental_supplier,
        is_crew_supplier=customer.is_crew_supplier,
        created_at=customer.created_at,
    )

    if customer.is_customer:
        jobs = list(db.scalars(
            select(Job).where(Job.customer_id == customer_id).order_by(Job.id.desc())
        ).all())
        result.jobs = [
            CustomerJobSummary(
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

    if customer.is_product_supplier or customer.is_rental_supplier:
        ps_rows = list(db.scalars(
            select(ProductSupplier)
            .where(ProductSupplier.supplier_id == customer_id)
            .options(selectinload(ProductSupplier.product))
        ).all())
        products = [ps.product for ps in ps_rows if ps.product]
        if customer.is_rental_supplier and not customer.is_product_supplier:
            products = [p for p in products if p.is_rental_product]
        result.supplied_products = [
            CustomerProductSummary(
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

    if customer.is_crew_supplier:
        from app.domain.crew.models import CrewMember

        crew_members = list(db.scalars(
            select(CrewMember)
            .where(CrewMember.supplier_id == customer_id)
            .options(
                selectinload(CrewMember.skills),
                selectinload(CrewMember.certifications),
                selectinload(CrewMember.preferred_roles),
            )
            .order_by(CrewMember.name)
        ).all())
        result.crew_members = [
            CustomerCrewMemberSummary(
                id=cm.id,
                name=cm.name,
                email=cm.email,
                phone=cm.phone,
                user_id=cm.user_id,
                supplier_id=cm.supplier_id,
                hourly_rate=float(cm.hourly_rate) if cm.hourly_rate else None,
                daily_rate=float(cm.daily_rate) if cm.daily_rate else None,
                is_active=cm.is_active,
                skills=[sk.skill for sk in cm.skills] if cm.skills else [],
                certifications=[
                    {"certification": c.certification, "expires_at": c.expires_at.isoformat() if c.expires_at else None}
                    for c in cm.certifications
                ] if cm.certifications else [],
                preferred_role_ids=[r.id for r in cm.preferred_roles] if cm.preferred_roles else [],
                preferred_role_names=[r.name for r in cm.preferred_roles] if cm.preferred_roles else [],
                notes=cm.notes,
            )
            for cm in crew_members
        ]

    return result


@customers_router.post("", response_model=CustomerRead)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Customer:
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.flush()
    db.refresh(customer)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=customer.id,
        action="create",
        message_format="customer_created",
        message_params={"name": customer.name},
        details={"name": customer.name},
    )
    emit_realtime_event("customers.updated", {"entity": "customer", "action": "create", "id": customer.id})
    created_total.labels(entity="customer").inc()
    entities_count.labels(entity="customer").inc()
    db.commit()
    return customer


@customers_router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.flush()
    db.refresh(customer)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=customer.id,
        action="update",
        message_format="customer_updated",
        message_params={"name": customer.name},
        details={"name": customer.name},
    )
    emit_realtime_event("customers.updated", {"entity": "customer", "action": "update", "id": customer.id})
    db.commit()
    return customer


@customers_router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> None:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    linked_products = list(db.scalars(
        select(ProductSupplier).where(ProductSupplier.supplier_id == customer_id)
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

    linked_devices = list(db.scalars(
        select(Device).where(Device.supplier_id == customer_id)
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

    customer_name = customer.name
    jobs = list(db.scalars(select(Job).where(Job.customer_id == customer_id)).all())
    for job in jobs:
        job.customer_id = None
        job.customer_name = None

    db.delete(customer)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=customer_id,
        action="delete",
        message_format="customer_deleted",
        message_params={"name": customer_name},
        details={"name": customer_name},
    )
    emit_realtime_event("customers.updated", {"entity": "customer", "action": "delete", "id": customer_id})
    deleted_total.labels(entity="customer").inc()
    entities_count.labels(entity="customer").dec()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Company Endpoints
# ============================================================================

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
            .order_by(CrewMember.name)
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
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Company:
    company = Company(**payload.model_dump())
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
    return company


@companies_router.put("/{company_id}", response_model=CompanyRead)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Company:
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
def create_person(payload: PersonCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Person:
    person = Person(**payload.model_dump())
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
    return person


@persons_router.put("/{person_id}", response_model=PersonRead)
def update_person(person_id: int, payload: PersonUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Person:
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)
