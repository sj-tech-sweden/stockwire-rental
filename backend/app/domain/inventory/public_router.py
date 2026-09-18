from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.pagination import PaginatedResponse, PaginationParams, paginate_query
from app.db.session import get_db
from app.domain.inventory.models import Product
from app.domain.inventory.schemas import PublicProductRead

router = APIRouter(prefix="/public", tags=["public"])


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        result = Decimal(text)
        if not result.is_finite():
            return None
        return result
    except (InvalidOperation, ValueError):
        return None


def _product_to_public(product: Product) -> PublicProductRead:
    return PublicProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category=product.category,
        brand=product.brand,
        product_type=product.product_type,
        daily_rate=product.daily_rate,
        rental_price=product.rental_price,
        weight_kg=product.weight_kg,
        height_cm=product.height_cm,
        width_cm=product.width_cm,
        depth_cm=product.depth_cm,
    )


@router.get("/products", response_model=PaginatedResponse[PublicProductRead])
def list_public_products(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
    q: str | None = Query(None, description="Search by name, SKU, or brand"),
    category: str | None = Query(None, description="Filter by category"),
    min_daily_rate: str | None = Query(None, description="Minimum daily rate"),
    max_daily_rate: str | None = Query(None, description="Maximum daily rate"),
    min_rental_price: str | None = Query(None, description="Minimum rental price"),
    max_rental_price: str | None = Query(None, description="Maximum rental price"),
) -> PaginatedResponse[PublicProductRead]:
    stmt = select(Product).where(Product.is_public.is_(True))

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            Product.name.ilike(pattern) | Product.sku.ilike(pattern) | Product.brand.ilike(pattern)
        )

    if category:
        stmt = stmt.where(Product.category == category.strip())

    min_dr = _parse_decimal(min_daily_rate)
    if min_dr is not None:
        stmt = stmt.where(Product.daily_rate >= min_dr)

    max_dr = _parse_decimal(max_daily_rate)
    if max_dr is not None:
        stmt = stmt.where(Product.daily_rate <= max_dr)

    min_rp = _parse_decimal(min_rental_price)
    if min_rp is not None:
        stmt = stmt.where(Product.rental_price >= min_rp)

    max_rp = _parse_decimal(max_rental_price)
    if max_rp is not None:
        stmt = stmt.where(Product.rental_price <= max_rp)

    stmt = stmt.order_by(Product.name, Product.id)

    products, total = paginate_query(db, stmt, pagination.skip, pagination.limit)
    items = [_product_to_public(p) for p in products]

    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@router.get("/products/{product_id}", response_model=PublicProductRead)
def get_public_product(product_id: int, db: Session = Depends(get_db)) -> PublicProductRead:
    product = db.get(Product, product_id)
    if product is None or not product.is_public:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_public(product)
