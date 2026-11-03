from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.inventory.models import Device, Product
from app.domain.jobs.models import Job, JobRequirement


class MissingProductsError(ValueError):
    def __init__(self, product_ids: list[int]) -> None:
        self.product_ids = product_ids
        super().__init__(f"Product(s) not found: {product_ids}")


def calculate_product_availability(
    db: Session,
    product_ids: list[int],
    start_date: date,
    end_date: date,
) -> list[dict[str, int | date]]:
    """Return each product's minimum available device quantity for an inclusive date range."""
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    existing_ids = set(db.scalars(select(Product.id).where(Product.id.in_(product_ids))).all())
    missing_ids = [product_id for product_id in product_ids if product_id not in existing_ids]
    if missing_ids:
        raise MissingProductsError(missing_ids)

    device_counts = {
        product_id: int(quantity)
        for product_id, quantity in db.execute(
            select(Device.product_id, func.count())
            .where(
                Device.product_id.in_(product_ids),
                Device.status.in_(["available", "reserved", "in_use"]),
                or_(Device.condition.is_(None), Device.condition != "damaged"),
            )
            .group_by(Device.product_id)
        )
    }

    reservations = db.execute(
        select(
            JobRequirement.product_id,
            Job.start_date,
            Job.end_date,
            JobRequirement.quantity_required,
        )
        .join(JobRequirement, JobRequirement.job_id == Job.id)
        .where(
            JobRequirement.product_id.in_(product_ids),
            Job.status.notin_(["cancelled", "completed"]),
            Job.start_date.is_not(None),
            Job.end_date.is_not(None),
            Job.start_date <= end_date,
            Job.end_date >= start_date,
        )
    ).all()

    reservation_changes: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for product_id, job_start, job_end, quantity_required in reservations:
        if product_id is None or job_start is None or job_end is None:
            continue
        quantity = max(int(quantity_required or 0), 0)
        if quantity == 0:
            continue
        overlap_start = max(job_start, start_date)
        overlap_end = min(job_end, end_date)
        reservation_changes[product_id][overlap_start] += quantity
        reservation_changes[product_id][overlap_end + timedelta(days=1)] -= quantity

    availability: list[dict[str, int | date]] = []
    for product_id in product_ids:
        max_reserved_quantity = 0
        reserved_quantity = 0
        for change_date in sorted(reservation_changes[product_id]):
            if change_date > end_date:
                break
            reserved_quantity += reservation_changes[product_id][change_date]
            max_reserved_quantity = max(max_reserved_quantity, reserved_quantity)

        total_quantity = device_counts.get(product_id, 0)
        availability.append(
            {
                "product_id": product_id,
                "start_date": start_date,
                "end_date": end_date,
                "total_quantity": total_quantity,
                "max_reserved_quantity": max_reserved_quantity,
                "available_quantity": max(total_quantity - max_reserved_quantity, 0),
            }
        )

    return availability
