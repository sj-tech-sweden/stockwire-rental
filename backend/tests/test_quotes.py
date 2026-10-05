"""Tests for the quotes subsystem (settings + PDF generation)."""
import json
from datetime import date

from app.domain.crew.models import CrewRole, JobCrewRequirement
from app.domain.inventory.models import Product, VendorProduct
from app.domain.jobs.models import Job, JobRequirement
from app.domain.settings.accessors import get_company_profile_currency
from app.domain.settings.models import AppSetting
from app.services.pdf_service import PDFService


def test_get_default_quotes_settings(client):
    resp = client.get("/api/v1/quotes/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_markup_pct"] == 30.0
    assert data["vat_rate"] == 0.25


def test_update_quotes_settings(client):
    resp = client.put(
        "/api/v1/quotes/settings",
        json={"default_markup_pct": 25.0, "vat_rate": 0.1},
    )
    assert resp.status_code == 200
    assert resp.json()["default_markup_pct"] == 25.0
    assert resp.json()["vat_rate"] == 0.1

    resp = client.get("/api/v1/quotes/settings")
    assert resp.json()["vat_rate"] == 0.1


def test_generate_quote_returns_pdf(client, db_session):
    product = Product(sku="QTEST-SPK", name="Test Speaker")
    job = Job(job_code="QTEST-001")
    db_session.add_all([product, job])
    db_session.flush()
    req = JobRequirement(job_id=job.id, product_id=product.id, quantity_required=2)
    db_session.add(req)
    db_session.commit()

    resp = client.post(f"/api/v1/quotes/jobs/{job.id}/generate")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert len(resp.content) > 100

    db_session.refresh(job)
    assert job.status == "quotation"


def test_quote_crew_daily_line_total(client, db_session):
    role = CrewRole(name="Stagehand")
    db_session.add(role)
    job = Job(job_code="QTEST-DAILY")
    db_session.add(job)
    db_session.flush()
    db_session.add(JobCrewRequirement(
        job_id=job.id,
        crew_role_id=role.id,
        quantity=2,
        rate_basis="daily",
        daily_rate=1000,
        days=3,
    ))
    db_session.commit()

    context = PDFService(db_session).resolve_context("job", job.id)
    crew_lines = context["crew_lines"]
    assert len(crew_lines) == 1
    line = crew_lines[0]
    assert line["basis"] == "daily"
    assert line["days"] == 3
    # Monetary values are formatted with the company currency.
    assert line["rate"] == "1000.00 SEK"
    # 1000/day * 2 people * 3 days
    assert line["line_total"] == "6000.00 SEK"


def test_quote_rental_per_day_line_total(client, db_session):
    product = Product(sku="RENT-1", name="Light", rental_price=500, daily_rate=500)
    # 2026-01-01 -> 2026-01-04 inclusive = 4 rental days.
    job = Job(job_code="QTEST-RENT", start_date=date(2026, 1, 1), end_date=date(2026, 1, 4))
    db_session.add_all([product, job])
    db_session.flush()
    db_session.add(JobRequirement(job_id=job.id, product_id=product.id, quantity_required=2))
    db_session.commit()

    context = PDFService(db_session).resolve_context("job", job.id)
    lines = context["quote_lines"]
    assert len(lines) == 1
    line = lines[0]
    assert line["source_type"] == "rental"
    assert line["days"] == 4
    assert line["unit_price"] == "500.00 SEK"
    # 500/day * 4 days * 2 units
    assert line["line_total"] == "4000.00 SEK"


def test_quote_purchase_line_applies_default_markup(client, db_session):
    # Pin the markup so the expectation is deterministic regardless of order.
    client.put("/api/v1/quotes/settings", json={"default_markup_pct": 50.0, "vat_rate": 0.25})

    vendor_product = VendorProduct(
        sku="BUY-1", name="Speaker", brand="Deltaco", unit_cost=100.0, currency="SEK"
    )
    job = Job(job_code="QTEST-BUY")
    db_session.add_all([vendor_product, job])
    db_session.flush()
    db_session.add(JobRequirement(
        job_id=job.id, vendor_product_id=vendor_product.id, quantity_required=2
    ))
    db_session.commit()

    context = PDFService(db_session).resolve_context("job", job.id)
    lines = context["quote_lines"]
    assert len(lines) == 1
    line = lines[0]
    assert line["source_type"] == "purchase"
    # 100 * 1.5 = 150; formatted with company currency.
    assert line["unit_cost"] == "100.00 SEK"
    assert line["unit_price"] == "150.00 SEK"
    # 150 * 2 units
    assert line["line_total"] == "300.00 SEK"


def test_quote_purchase_line_respects_explicit_unit_price(client, db_session):
    client.put("/api/v1/quotes/settings", json={"default_markup_pct": 50.0, "vat_rate": 0.25})

    vendor_product = VendorProduct(
        sku="BUY-2", name="Cable", unit_cost=100.0, currency="SEK"
    )
    job = Job(job_code="QTEST-BUY2")
    db_session.add_all([vendor_product, job])
    db_session.flush()
    # An explicitly set per-row unit price overrides the default markup.
    db_session.add(JobRequirement(
        job_id=job.id, vendor_product_id=vendor_product.id,
        quantity_required=3, unit_price=180.0,
    ))
    db_session.commit()

    context = PDFService(db_session).resolve_context("job", job.id)
    line = context["quote_lines"][0]
    assert line["source_type"] == "purchase"
    assert line["unit_cost"] == "100.00 SEK"
    assert line["unit_price"] == "180.00 SEK"
    # 180 * 3 units
    assert line["line_total"] == "540.00 SEK"


def test_quote_generation_sets_job_status_and_totals(client, db_session):
    client.put("/api/v1/quotes/settings", json={"default_markup_pct": 30.0, "vat_rate": 0.25})

    vendor_product = VendorProduct(
        sku="BUY-3", name="Truss", unit_cost=200.0, currency="SEK"
    )
    job = Job(job_code="QTEST-STATUS")
    db_session.add_all([vendor_product, job])
    db_session.flush()
    db_session.add(JobRequirement(
        job_id=job.id, vendor_product_id=vendor_product.id, quantity_required=1
    ))
    db_session.commit()

    context = PDFService(db_session).resolve_context("job", job.id)
    assert context["quote_lines"][0]["line_total"] == "260.00 SEK"
    assert context["quote"]["subtotal"] == "260.00 SEK"
    assert context["quote"]["vat_amount"] == "65.00 SEK"
    assert context["quote"]["total"] == "325.00 SEK"

    resp = client.post(f"/api/v1/quotes/jobs/{job.id}/generate")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")

    db_session.refresh(job)
    assert job.status == "quotation"


def test_company_profile_currency_default_and_setting(db_session):
    # Falls back to SEK when unset.
    assert get_company_profile_currency(db_session) == "SEK"
    db_session.add(AppSetting(
        key="company.profile",
        value_json=json.dumps({"currency": "EUR", "default_language": "sv"}),
    ))
    db_session.commit()
    assert get_company_profile_currency(db_session) == "EUR"


def test_quote_template_includes_rental_columns_and_no_currency_row(db_session):
    from app.domain.quotes.templates import ensure_default_quote_template

    tpl = ensure_default_quote_template(db_session)
    body = json.loads(tpl.body_json)
    quote_kv = next(
        f for f in body["flowables"]
        if f.get("type") == "key_value" and f.get("source") == "quote"
    )
    # Currency is rendered with each price, not as a separate row.
    assert not any(f["key"] == "currency" for f in quote_kv["fields"])
    equip = next(
        f for f in body["flowables"]
        if f.get("type") == "table" and f.get("source") == "quote_lines"
    )
    keys = {c["key"] for c in equip["columns"]}
    assert "source_type" in keys
    assert "days" in keys


def test_sync_twenty_requires_active_integration(client, db_session):
    job = Job(job_code="QTEST-002", status="quotation")
    db_session.add(job)
    db_session.commit()

    resp = client.post(f"/api/v1/quotes/jobs/{job.id}/sync-twenty")
    assert resp.status_code == 400
    assert "Twenty" in resp.json()["detail"]


def test_public_quote_pdf_download(client, db_session):
    from app.domain.storage.models import AssetFile
    from app.domain.storage.service import StorageService

    storage = StorageService()
    storage_key, stored_filename = storage.make_storage_key(
        entity_type="job", category="quote", original_filename="q.pdf"
    )
    storage.save_bytes(storage_key=storage_key, payload=b"%PDF-1.4 quote", content_type="application/pdf")

    asset = AssetFile(
        entity_type="job",
        entity_id=1,
        category="quote",
        original_filename="q.pdf",
        stored_filename=stored_filename,
        content_type="application/pdf",
        size_bytes=13,
        storage_key=storage_key,
        public_token="secret-token-123",
    )
    db_session.add(asset)
    db_session.commit()

    # No token -> not found (anonymous access denied)
    assert client.get(f"/api/v1/storage/public/files/{asset.id}").status_code == 404
    # Wrong token -> not found
    assert (
        client.get(f"/api/v1/storage/public/files/{asset.id}?token=wrong").status_code == 404
    )
    # Correct token -> served without auth
    resp = client.get(f"/api/v1/storage/public/files/{asset.id}?token=secret-token-123")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
