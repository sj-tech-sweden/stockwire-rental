import pytest
from sqlalchemy import select

from app.domain.inventory.models import (
    CategoryTranslation,
    InventoryCategory,
    Product,
    ProductTypeTranslation,
)
from app.domain.storage.models import AssetFile


def _make_category(db, name="Lighting", en="Lighting", sv="Belysning"):
    cat = InventoryCategory(name=name)
    db.add(cat)
    db.flush()
    db.add(CategoryTranslation(category_id=cat.id, locale="en", name=en))
    db.add(CategoryTranslation(category_id=cat.id, locale="sv", name=sv))
    db.commit()
    return cat


def _make_product(db, category, product_type="equipment", is_public=True):
    product = Product(
        sku="SKU-LOCAL-1",
        name="Pro Light",
        category="general",
        category_id=category.id,
        product_type=product_type,
        is_public=is_public,
        daily_rate=10,
        rental_price=20,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _make_image(db, product, content_type="image/png"):
    image = AssetFile(
        entity_type="product",
        entity_id=product.id,
        category="product-image",
        original_filename="pic.png",
        stored_filename="pic.png",
        content_type=content_type,
        size_bytes=10,
        storage_backend="local",
        storage_key=f"product/{product.id}/pic-{content_type.replace('/', '_')}.png",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def test_public_product_list_translates_category_and_type(client, db_session):
    category = _make_category(db_session)
    product = _make_product(db_session, category)
    _make_image(db_session, product)

    # Default locale (en)
    resp = client.get("/api/v1/public/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["category"] == "Lighting"
    assert item["product_type"] == "Equipment"
    assert len(item["images"]) == 1
    assert item["images"][0]["url"] == f"/api/v1/storage/public/product-image/{product.id}"

    # Swedish locale
    resp_sv = client.get("/api/v1/public/products?locale=sv")
    assert resp_sv.status_code == 200
    item_sv = resp_sv.json()["items"][0]
    assert item_sv["category"] == "Belysning"
    assert item_sv["product_type"] == "Utrustning"


def test_public_product_detail_translates(client, db_session):
    category = _make_category(db_session)
    product = _make_product(db_session, category, product_type="crew")

    resp = client.get(f"/api/v1/public/products/{product.id}?locale=sv")
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "Belysning"
    assert body["product_type"] == "Personal"
    assert body["images"] == []


def test_public_product_type_db_translation_any_language(client, db_session):
    category = _make_category(db_session)
    product = _make_product(db_session, category, product_type="equipment")

    # Add a translation for a language not in the built-in fallback dict.
    db_session.add(ProductTypeTranslation(product_type="equipment", locale="de", label="Ausrüstung"))
    db_session.commit()

    resp = client.get(f"/api/v1/public/products/{product.id}?locale=de")
    assert resp.status_code == 200
    assert resp.json()["product_type"] == "Ausrüstung"

    # Unknown locale with no DB row falls back to the raw code gracefully.
    resp_fallback = client.get(f"/api/v1/public/products/{product.id}?locale=fr")
    assert resp_fallback.status_code == 200
    assert resp_fallback.json()["product_type"] == "Equipment"  # fr not seeded -> en fallback


def test_public_product_image_download_guards(client, db_session):
    category = _make_category(db_session)
    product = _make_product(db_session, category)
    image = _make_image(db_session, product)

    # Non-existent file -> 404
    assert client.get("/api/v1/storage/public/product-image/999999").status_code == 404

    # Non-image content type -> 404
    pdf = _make_image(db_session, product, content_type="application/pdf")
    assert client.get(f"/api/v1/storage/public/product-image/{pdf.id}").status_code == 404

    # Deleted image -> 404 (mark deleted)
    image.is_deleted = True
    db_session.commit()
    assert client.get(f"/api/v1/storage/public/product-image/{image.id}").status_code == 404


def test_public_product_hidden_when_not_public(client, db_session):
    category = _make_category(db_session)
    product = _make_product(db_session, category, is_public=False)

    assert client.get(f"/api/v1/public/products/{product.id}").status_code == 404
    assert client.get("/api/v1/public/products").json()["total"] == 0
