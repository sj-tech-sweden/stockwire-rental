"""Regression tests for bulk requirement upserts."""
from decimal import Decimal

from app.domain.inventory.models import Product, VendorProduct
from app.domain.jobs.models import Job, JobRequirement


def _product(db_session, sku: str) -> Product:
    p = Product(sku=sku, name=sku, product_type="equipment")
    db_session.add(p)
    db_session.commit()
    return p


def _vendor_product(db_session, name: str) -> VendorProduct:
    vp = VendorProduct(name=name, sku=name, currency="SEK")
    db_session.add(vp)
    db_session.commit()
    return vp


def _job(db_session, code: str) -> Job:
    job = Job(job_code=code)
    db_session.add(job)
    db_session.commit()
    return job


def test_bulk_upsert_product_requirement(client, db_session):
    job = _job(db_session, "BULK-1")
    product = _product(db_session, "PROD-1")

    resp = client.put(
        f"/api/v1/jobs/{job.id}/requirements/bulk",
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity_required": 3,
                    "quantity_picked": 1,
                    "notes": "note",
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["product_id"] == product.id
    assert data[0]["quantity_required"] == 3
    assert data[0]["vendor_product_id"] is None


def test_bulk_upsert_vendor_product_requirement(client, db_session):
    job = _job(db_session, "BULK-2")
    vp = _vendor_product(db_session, "VP-1")

    resp = client.put(
        f"/api/v1/jobs/{job.id}/requirements/bulk",
        json={
            "items": [
                {
                    "vendor_product_id": vp.id,
                    "unit_price": "123.45",
                    "quantity_required": 2,
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["product_id"] is None
    assert data[0]["vendor_product_id"] == vp.id
    assert Decimal(data[0]["unit_price"]) == Decimal("123.45")


def test_bulk_upsert_preserves_existing_unit_price(client, db_session):
    job = _job(db_session, "BULK-3")
    product = _product(db_session, "PROD-3")
    req = JobRequirement(
        job_id=job.id,
        product_id=product.id,
        quantity_required=1,
        unit_price=Decimal("99.00"),
    )
    db_session.add(req)
    db_session.commit()

    # Frontend save that does not send unit_price should not wipe it.
    resp = client.put(
        f"/api/v1/jobs/{job.id}/requirements/bulk",
        json={"items": [{"product_id": product.id, "quantity_required": 5}]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert Decimal(data[0]["unit_price"]) == Decimal("99.00")
    assert data[0]["quantity_required"] == 5


def test_bulk_upsert_deletes_missing_requirements(client, db_session):
    job = _job(db_session, "BULK-4")
    product = _product(db_session, "PROD-4")
    req = JobRequirement(job_id=job.id, product_id=product.id, quantity_required=1)
    db_session.add(req)
    db_session.commit()

    resp = client.put(
        f"/api/v1/jobs/{job.id}/requirements/bulk",
        json={"items": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
