from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.finance.models import FinancialTransaction
from app.domain.finance.schemas import (
    ALLOWED_TRANSACTION_STATUSES,
    ALLOWED_TRANSACTION_TYPES,
    FinanceJobInsightsRead,
    FinanceSummaryRead,
    FinancialTransactionCreate,
    FinancialTransactionListQuery,
    FinancialTransactionRead,
    FinancialTransactionUpdate,
)
from app.domain.inventory.models import Device
from app.domain.inventory.models import Product
from app.domain.jobs.models import Job
from app.domain.jobs.models import JobRequirement

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "finance", "status": "scaffolded"}


@router.get("/job-insights", response_model=FinanceJobInsightsRead)
def get_job_finance_insights(db: Session = Depends(get_db)) -> FinanceJobInsightsRead:
    jobs = list(db.scalars(select(Job)).all())
    if not jobs:
        return FinanceJobInsightsRead()

    requirement_rows = db.execute(
        select(
            JobRequirement.job_id,
            JobRequirement.quantity_required,
            JobRequirement.quantity_picked,
            Product.daily_rate,
            Product.rental_price,
        ).join(Product, Product.id == JobRequirement.product_id)
    ).all()

    tx_rows = db.execute(
        select(
            FinancialTransaction.job_id,
            FinancialTransaction.amount,
            FinancialTransaction.status,
        ).where(FinancialTransaction.job_id.is_not(None))
    ).all()

    req_by_job: dict[int, dict[str, Decimal | int]] = {}
    for job_id, qty_required, qty_picked, daily_rate, rental_price in requirement_rows:
        if job_id is None:
            continue
        bucket = req_by_job.setdefault(
            int(job_id),
            {
                "lines": 0,
                "required": 0,
                "picked": 0,
                "estimated": Decimal("0.00"),
            },
        )
        required = max(int(qty_required or 0), 0)
        picked = max(int(qty_picked or 0), 0)
        rate = Decimal(str(rental_price or 0))
        if rate <= 0:
            rate = Decimal(str(daily_rate or 0))

        bucket["lines"] = int(bucket["lines"]) + 1
        bucket["required"] = int(bucket["required"]) + required
        bucket["picked"] = int(bucket["picked"]) + picked
        bucket["estimated"] = Decimal(bucket["estimated"]) + (Decimal(required) * rate)

    tx_by_job: dict[int, dict[str, Decimal]] = {}
    for job_id, amount, tx_status in tx_rows:
        if job_id is None:
            continue
        bucket = tx_by_job.setdefault(int(job_id), {"all": Decimal("0.00"), "completed": Decimal("0.00")})
        money = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        bucket["all"] = bucket["all"] + money
        if str(tx_status or "").lower() == "completed":
            bucket["completed"] = bucket["completed"] + money

    active_statuses = {"draft", "confirmed", "in_progress"}
    completed_statuses = {"completed"}
    cancelled_statuses = {"cancelled"}

    top_jobs: list[dict[str, object]] = []
    projected_total = Decimal("0.00")
    projected_active = Decimal("0.00")
    projected_completed = Decimal("0.00")
    sales_total = Decimal("0.00")
    sales_paid = Decimal("0.00")
    sales_unpaid = Decimal("0.00")
    invoice_paid_jobs = 0
    invoice_unpaid_jobs = 0
    tx_total = Decimal("0.00")
    collected_total = Decimal("0.00")
    jobs_active = 0
    jobs_completed = 0
    jobs_cancelled = 0

    for job in jobs:
        job_req = req_by_job.get(job.id, {"lines": 0, "required": 0, "picked": 0, "estimated": Decimal("0.00")})
        job_tx = tx_by_job.get(job.id, {"all": Decimal("0.00"), "completed": Decimal("0.00")})
        rental_days = _job_rental_days(job)
        estimated_value = (Decimal(job_req["estimated"]) * Decimal(rental_days)).quantize(Decimal("0.01"))
        sales_value = Decimal(str(getattr(job, "sales_price", 0) or 0)).quantize(Decimal("0.01"))
        if sales_value > 0:
            estimated_value = sales_value
        required_total = int(job_req["required"])
        picked_total = int(job_req["picked"])
        completion_percent = 0 if required_total <= 0 else max(0, min(100, int(round((picked_total / required_total) * 100))))

        status_norm = str(job.status or "draft").lower()
        projected_total += estimated_value
        sales_total += sales_value
        tx_total += Decimal(job_tx["all"])
        collected_total += Decimal(job_tx["completed"])
        if bool(getattr(job, "invoice_paid", False)):
            invoice_paid_jobs += 1
            sales_paid += sales_value
        else:
            invoice_unpaid_jobs += 1
            sales_unpaid += sales_value
        if status_norm in active_statuses:
            jobs_active += 1
            projected_active += estimated_value
        if status_norm in completed_statuses:
            jobs_completed += 1
            projected_completed += estimated_value
        if status_norm in cancelled_statuses:
            jobs_cancelled += 1

        top_jobs.append(
            {
                "job_id": job.id,
                "job_code": job.job_code,
                "customer_name": job.customer_name,
                "status": status_norm,
                "start_date": job.start_date,
                "end_date": job.end_date,
                "rental_days": rental_days,
                "requirement_lines": int(job_req["lines"]),
                "quantity_required_total": required_total,
                "quantity_picked_total": picked_total,
                "completion_percent": completion_percent,
                "estimated_value": estimated_value,
                "transaction_total": Decimal(job_tx["all"]).quantize(Decimal("0.01")),
                "completed_transaction_total": Decimal(job_tx["completed"]).quantize(Decimal("0.01")),
            }
        )

    top_jobs = sorted(top_jobs, key=lambda row: Decimal(str(row.get("estimated_value") or 0)), reverse=True)[:8]

    return FinanceJobInsightsRead(
        jobs_total=len(jobs),
        jobs_active=jobs_active,
        jobs_completed=jobs_completed,
        jobs_cancelled=jobs_cancelled,
        projected_total_value=projected_total.quantize(Decimal("0.01")),
        projected_active_value=projected_active.quantize(Decimal("0.01")),
        projected_completed_value=projected_completed.quantize(Decimal("0.01")),
        sales_total_value=sales_total.quantize(Decimal("0.01")),
        sales_paid_value=sales_paid.quantize(Decimal("0.01")),
        sales_unpaid_value=sales_unpaid.quantize(Decimal("0.01")),
        invoice_paid_jobs=invoice_paid_jobs,
        invoice_unpaid_jobs=invoice_unpaid_jobs,
        transaction_total=tx_total.quantize(Decimal("0.01")),
        collected_total=collected_total.quantize(Decimal("0.01")),
        top_jobs=top_jobs,
    )


@router.get("/summary", response_model=FinanceSummaryRead)
def get_finance_summary(db: Session = Depends(get_db)) -> FinanceSummaryRead:
    rows = list(db.scalars(select(FinancialTransaction)).all())
    today = datetime.now(UTC).date()
    # Business rule: supplier-rented Eventory quantities are excluded from warehouse valuation.
    # Owned non-serialized products are valued per product replace_cost, and serialized owned
    # inventory is valued via devices.
    owned_product_filters = (
        Product.is_rental_product.is_(False),
        Product.product_type != "rental",
    )
    warehouse_products_sum = db.scalar(
        select(func.coalesce(func.sum(Product.replace_cost), 0)).where(
            *owned_product_filters,
            ~exists(select(1).where(Device.product_id == Product.id)),
        )
    )
    warehouse_devices_sum = db.scalar(
        select(func.coalesce(func.sum(func.coalesce(Device.purchase_price, Product.replace_cost, 0)), 0))
        .select_from(Device)
        .join(Product, Device.product_id == Product.id)
        .where(
            *owned_product_filters,
            Device.status.in_(["available", "reserved", "maintenance"]),
        )
    )
    warehouse_products_value = Decimal(str(warehouse_products_sum or 0))
    warehouse_devices_value = Decimal(str(warehouse_devices_sum or 0))

    pending_amount = Decimal("0.00")
    overdue_amount = Decimal("0.00")
    completed_amount = Decimal("0.00")
    pending_count = 0
    overdue_count = 0
    completed_count = 0

    for tx in rows:
        amount = Decimal(str(tx.amount or 0)).quantize(Decimal("0.01"))
        is_completed = str(tx.status or "").lower() == "completed"
        due = tx.due_date.date() if tx.due_date else None
        is_overdue = bool(due and due < today and not is_completed)

        if is_completed:
            completed_count += 1
            completed_amount += amount
        else:
            pending_count += 1
            pending_amount += amount
            if is_overdue:
                overdue_count += 1
                overdue_amount += amount

    return FinanceSummaryRead(
        currency="SEK",
        total_transactions=len(rows),
        pending_count=pending_count,
        overdue_count=overdue_count,
        completed_count=completed_count,
        pending_amount=pending_amount,
        overdue_amount=overdue_amount,
        completed_amount=completed_amount,
        warehouse_products_value=warehouse_products_value.quantize(Decimal("0.01")),
        warehouse_devices_value=warehouse_devices_value.quantize(Decimal("0.01")),
        warehouse_total_value=(warehouse_products_value + warehouse_devices_value).quantize(Decimal("0.01")),
    )


@router.get("/transactions", response_model=list[FinancialTransactionRead])
def list_transactions(
    status_filter: str | None = Query(default=None, alias="status"),
    transaction_type: str | None = Query(default=None),
    job_id: int | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    overdue_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[FinancialTransactionRead]:
    query = FinancialTransactionListQuery(
        status=status_filter,
        transaction_type=transaction_type,
        job_id=job_id,
        customer_name=customer_name,
        from_date=from_date,
        to_date=to_date,
        overdue_only=overdue_only,
    )

    statement: Select = (
        select(FinancialTransaction, Job.job_code, Job.customer_name)
        .outerjoin(Job, Job.id == FinancialTransaction.job_id)
        .order_by(FinancialTransaction.transaction_date.desc(), FinancialTransaction.id.desc())
    )

    if query.status:
        normalized = query.status.strip().lower()
        if normalized not in ALLOWED_TRANSACTION_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        statement = statement.where(func.lower(FinancialTransaction.status) == normalized)

    if query.transaction_type:
        normalized = query.transaction_type.strip().lower()
        if normalized not in ALLOWED_TRANSACTION_TYPES:
            raise HTTPException(status_code=422, detail="Invalid transaction_type filter")
        statement = statement.where(func.lower(FinancialTransaction.transaction_type) == normalized)

    if query.job_id is not None:
        statement = statement.where(FinancialTransaction.job_id == query.job_id)

    if query.customer_name:
        like = f"%{query.customer_name.strip()}%"
        statement = statement.where(Job.customer_name.ilike(like))

    if query.from_date:
        statement = statement.where(FinancialTransaction.transaction_date >= datetime.combine(query.from_date, datetime.min.time(), tzinfo=UTC))

    if query.to_date:
        statement = statement.where(FinancialTransaction.transaction_date <= datetime.combine(query.to_date, datetime.max.time(), tzinfo=UTC))

    if query.overdue_only:
        today = datetime.now(UTC)
        statement = statement.where(
            FinancialTransaction.due_date.is_not(None),
            FinancialTransaction.due_date < today,
            func.lower(FinancialTransaction.status) != "completed",
        )

    rows = db.execute(statement).all()
    return [_to_financial_transaction_read(tx, job_code, customer_name) for tx, job_code, customer_name in rows]


@router.post("/transactions", response_model=FinancialTransactionRead)
def create_transaction(
    payload: FinancialTransactionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> FinancialTransactionRead:
    if payload.job_id is not None and db.get(Job, payload.job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    data = payload.model_dump()
    if data.get("transaction_date") is None:
        data["transaction_date"] = datetime.now(UTC)

    due_date = data.get("due_date")
    tx_date = data.get("transaction_date")
    if due_date and tx_date and due_date < tx_date:
        raise HTTPException(status_code=422, detail="due_date cannot be before transaction_date")

    tx = FinancialTransaction(**data)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    job = db.get(Job, tx.job_id) if tx.job_id else None
    return _to_financial_transaction_read(tx, job.job_code if job else None, job.customer_name if job else None)


@router.put("/transactions/{transaction_id}", response_model=FinancialTransactionRead)
def update_transaction(
    transaction_id: int,
    payload: FinancialTransactionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> FinancialTransactionRead:
    tx = db.get(FinancialTransaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    updates = payload.model_dump(exclude_unset=True)
    if "job_id" in updates and updates["job_id"] is not None and db.get(Job, updates["job_id"]) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    next_tx_date = updates.get("transaction_date", tx.transaction_date)
    next_due_date = updates.get("due_date", tx.due_date)
    if next_due_date and next_tx_date and next_due_date < next_tx_date:
        raise HTTPException(status_code=422, detail="due_date cannot be before transaction_date")

    for key, value in updates.items():
        setattr(tx, key, value)

    db.commit()
    db.refresh(tx)
    job = db.get(Job, tx.job_id) if tx.job_id else None
    return _to_financial_transaction_read(tx, job.job_code if job else None, job.customer_name if job else None)


@router.post("/transactions/{transaction_id}/settle", response_model=FinancialTransactionRead)
def settle_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> FinancialTransactionRead:
    tx = db.get(FinancialTransaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.status = "completed"
    tx.transaction_date = datetime.now(UTC)
    db.commit()
    db.refresh(tx)

    job = db.get(Job, tx.job_id) if tx.job_id else None
    return _to_financial_transaction_read(tx, job.job_code if job else None, job.customer_name if job else None)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> None:
    tx = db.get(FinancialTransaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_financial_transaction_read(
    tx: FinancialTransaction,
    job_code: str | None,
    customer_name: str | None,
) -> FinancialTransactionRead:
    today = datetime.now(UTC).date()
    due = tx.due_date.date() if tx.due_date else None
    is_completed = str(tx.status or "").lower() == "completed"
    is_overdue = bool(due and due < today and not is_completed)
    days_overdue = max((today - due).days, 0) if is_overdue and due else 0

    return FinancialTransactionRead(
        id=tx.id,
        job_id=tx.job_id,
        transaction_type=tx.transaction_type,
        status=tx.status,
        amount=Decimal(str(tx.amount or 0)).quantize(Decimal("0.01")),
        currency=(tx.currency or "SEK").upper(),
        transaction_date=tx.transaction_date,
        due_date=tx.due_date,
        created_at=tx.created_at,
        job_code=job_code,
        customer_name=customer_name,
        days_overdue=days_overdue,
        is_overdue=is_overdue,
    )


def _job_rental_days(job: Job) -> int:
    if job.start_date and job.end_date:
        return max(1, int((job.end_date - job.start_date).days) + 1)
    return 1
