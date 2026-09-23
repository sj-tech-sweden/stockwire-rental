import json
import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.inventory.category_segment_translations import CATEGORY_SEGMENT_SV

from app.api.pagination import PaginatedResponse, PaginationParams, paginate_query
from app.db.session import get_db
from app.domain.inventory.models import (
    InventoryCategory,
    Product,
    ProductTypeTranslation,
)
from app.domain.inventory.schemas import PublicProductImage, PublicProductRead
from app.domain.settings.models import AppSetting
from app.domain.storage.models import AssetFile

router = APIRouter(prefix="/public", tags=["public"])

COMPANY_PROFILE_KEY = "company.profile"
PRODUCT_IMAGE_CATEGORY = "product-image"

# Fallback labels so the endpoint works even before translations are seeded.
PRODUCT_TYPE_LABELS: dict[str, dict[str, str]] = {
    "equipment": {"en": "Equipment", "sv": "Utrustning"},
    "accessory": {"en": "Accessory", "sv": "Tillbehor"},
    "consumable": {"en": "Consumable", "sv": "Forbrukningsvara"},
    "case": {"en": "Case", "sv": "Lada"},
    "rental": {"en": "Rental", "sv": "Uthyrning"},
    "bundle": {"en": "Bundle", "sv": "Paket"},
    "crew": {"en": "Crew", "sv": "Personal"},
}


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


def _resolve_locale(db: Session, requested: str | None) -> str:
    """Resolve the response locale: explicit param > company default > 'en'."""
    if requested and requested.strip():
        return requested.strip().lower()[:5]
    setting = db.execute(
        select(AppSetting).where(AppSetting.key == COMPANY_PROFILE_KEY)
    ).scalar_one_or_none()
    if setting and setting.value_json:
        try:
            data = json.loads(setting.value_json)
        except Exception:
            data = None
        if isinstance(data, dict):
            lang = data.get("default_language")
            if isinstance(lang, str) and lang.strip():
                return lang.strip().lower()[:5]
    return "en"


def _canonicalize_segment(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", " ").replace("-", " ")).strip()


def _static_category_label(segment: str, locale: str) -> str | None:
    """Static fallback matching the frontend's prefill dictionary.

    Only Swedish is bundled in the backend; for other locales we rely on the
    database translations or the category's base name.
    """
    if locale and locale.startswith("sv"):
        return CATEGORY_SEGMENT_SV.get(_canonicalize_segment(segment))
    return None


def _translate_single_category(node: InventoryCategory, locale: str) -> str:
    exact: str | None = None
    fallback_en: str | None = None
    for tr in node.translations:
        if tr.locale == locale:
            exact = tr.name
            break
        if tr.locale == "en":
            fallback_en = tr.name
    return exact or fallback_en or _static_category_label(node.name, locale) or node.name


def _translate_free_text_category(value: str | None, locale: str) -> str:
    """Translate a legacy free-text category path (e.g. 'Cable > Power > 32A').

    Each segment is localized via the static dictionary when available; unknown
    segments are left as-is, mirroring the web UI's translatePrefillCategoryLine.
    """
    if not value:
        return ""
    segments = [seg.strip() for seg in str(value).split(">")]
    translated: list[str] = []
    for seg in segments:
        if not seg:
            continue
        label = _static_category_label(seg, locale)
        translated.append(label if label else seg)
    return " > ".join(translated)


def _translate_category_path(
    product: Product, locale: str, categories_by_id: dict[int, InventoryCategory]
) -> str:
    """Return the product's full category breadcrumb (root -> leaf), each segment
    translated for the requested locale."""
    if product.category_id is None or product.category_id not in categories_by_id:
        return _translate_free_text_category(product.category, locale)

    segments: list[str] = []
    seen: set[int] = set()
    node = categories_by_id.get(product.category_id)
    while node is not None and node.id not in seen:
        seen.add(node.id)
        segments.append(_translate_single_category(node, locale))
        node = categories_by_id.get(node.parent_id) if node.parent_id is not None else None
    segments.reverse()
    return " / ".join(segments)


def _load_product_type_translations(
    db: Session, product_types: list[str], locale: str
) -> dict[tuple[str, str], str]:
    """Load (product_type, locale) -> label rows for the requested locale and English."""
    if not product_types:
        return {}
    rows = db.execute(
        select(ProductTypeTranslation).where(
            ProductTypeTranslation.product_type.in_(product_types),
            ProductTypeTranslation.locale.in_([locale, "en"]),
        )
    ).scalars().all()
    return {(r.product_type, r.locale): r.label for r in rows}


def _translate_product_type(
    product_type: str,
    locale: str,
    translations: dict[tuple[str, str], str],
) -> str:
    return (
        translations.get((product_type, locale))
        or translations.get((product_type, "en"))
        or PRODUCT_TYPE_LABELS.get(product_type, {}).get(locale)
        or PRODUCT_TYPE_LABELS.get(product_type, {}).get("en")
        or product_type
    )


def _load_product_images(db: Session, product_ids: list[int]) -> dict[int, list[AssetFile]]:
    if not product_ids:
        return {}
    rows = db.execute(
        select(AssetFile).where(
            AssetFile.entity_type == "product",
            AssetFile.entity_id.in_(product_ids),
            AssetFile.category == PRODUCT_IMAGE_CATEGORY,
            AssetFile.is_deleted.is_(False),
        )
    ).scalars().all()
    grouped: dict[int, list[AssetFile]] = {}
    for row in rows:
        grouped.setdefault(row.entity_id, []).append(row)
    return grouped


def _load_categories(db: Session) -> dict[int, InventoryCategory]:
    rows = db.execute(
        select(InventoryCategory).options(selectinload(InventoryCategory.translations))
    ).scalars().all()
    return {row.id: row for row in rows}


def _to_image(item: AssetFile) -> PublicProductImage:
    return PublicProductImage(
        id=item.id,
        url=f"/api/v1/storage/public/product-image/{item.id}",
        content_type=item.content_type,
        original_filename=item.original_filename,
    )


def _product_to_public(
    product: Product,
    locale: str,
    images: list[AssetFile],
    type_translations: dict[tuple[str, str], str],
    categories_by_id: dict[int, InventoryCategory],
) -> PublicProductRead:
    return PublicProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category=_translate_category_path(product, locale, categories_by_id),
        brand=product.brand,
        product_type=_translate_product_type(product.product_type, locale, type_translations),
        daily_rate=product.daily_rate,
        rental_price=product.rental_price,
        weight_kg=product.weight_kg,
        height_cm=product.height_cm,
        width_cm=product.width_cm,
        depth_cm=product.depth_cm,
        images=[_to_image(img) for img in images],
    )


@router.get("/products", response_model=PaginatedResponse[PublicProductRead])
def list_public_products(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
    q: str | None = Query(None, description="Search by name, SKU, or brand"),
    category: str | None = Query(None, description="Filter by category"),
    locale: str | None = Query(None, description="Response language code, e.g. 'en' or 'sv'"),
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
    resolved_locale = _resolve_locale(db, locale)
    type_translations = _load_product_type_translations(
        db, [p.product_type for p in products], resolved_locale
    )
    categories_by_id = _load_categories(db)
    images_by_id = _load_product_images(db, [p.id for p in products])
    items = [
        _product_to_public(
            p, resolved_locale, images_by_id.get(p.id, []), type_translations, categories_by_id
        )
        for p in products
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@router.get("/products/{product_id}", response_model=PublicProductRead)
def get_public_product(
    product_id: int,
    db: Session = Depends(get_db),
    locale: str | None = Query(None, description="Response language code, e.g. 'en' or 'sv'"),
) -> PublicProductRead:
    product = db.get(Product, product_id)
    if product is None or not product.is_public:
        raise HTTPException(status_code=404, detail="Product not found")
    resolved_locale = _resolve_locale(db, locale)
    type_translations = _load_product_type_translations(
        db, [product.product_type], resolved_locale
    )
    categories_by_id = _load_categories(db)
    images = _load_product_images(db, [product.id]).get(product.id, [])
    return _product_to_public(
        product, resolved_locale, images, type_translations, categories_by_id
    )
