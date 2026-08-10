from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.pagination import PaginationParams, PaginatedResponse, paginate_query
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.customers.models import Customer
from app.domain.customers.schemas import (
    CustomerCreate,
    CustomerCrewMemberSummary,
    CustomerInfoRead,
    CustomerJobSummary,
    CustomerProductSummary,
    CustomerRead,
    CustomerUpdate,
)
from app.domain.inventory.models import Device, ProductSupplier
from app.services.metrics import created_total, deleted_total, entities_count
from app.domain.jobs.models import Job
from app.domain.realtime.events import emit_realtime_event

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "customers", "status": "scaffolded"}


@router.get("", response_model=PaginatedResponse[CustomerRead])
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


@router.get("/{customer_id}/info", response_model=CustomerInfoRead)
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


@router.post("", response_model=CustomerRead)
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


@router.put("/{customer_id}", response_model=CustomerRead)
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


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
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
