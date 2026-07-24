from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.customers.models import Customer
from app.domain.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.domain.inventory.models import Device, ProductSupplier
from app.services.metrics import created_total, deleted_total, entities_count
from app.domain.jobs.models import Job
from app.domain.realtime.events import emit_realtime_event

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "customers", "status": "scaffolded"}


@router.get("", response_model=list[CustomerRead])
def list_customers(
    type: str | None = Query(None, description="Filter by type: customer, product_supplier, rental_supplier, crew_supplier"),
    db: Session = Depends(get_db),
) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.name, Customer.id)
    if type == "customer":
        stmt = stmt.where(Customer.is_customer.is_(True))
    elif type == "product_supplier":
        stmt = stmt.where(Customer.is_product_supplier.is_(True))
    elif type == "rental_supplier":
        stmt = stmt.where(Customer.is_rental_supplier.is_(True))
    elif type == "crew_supplier":
        stmt = stmt.where(Customer.is_crew_supplier.is_(True))
    return list(db.scalars(stmt).all())


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
