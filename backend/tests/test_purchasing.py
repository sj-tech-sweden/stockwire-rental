"""Tests for the best-purchase / supplier-comparison feature and FX rates."""
import json
from datetime import date

from sqlalchemy import select

from app.db import session as _dbsession
from app.domain.customers.models import Company, Customer
from app.domain.inventory.models import Device, Product, ProductSupplier, VendorProduct
from app.domain.jobs.models import Job, JobRequirement
from app.domain.purchasing.models import PurchaseOrder, PurchaseOrderLine
from app.domain.settings.models import AppSetting



def _seed_two_vendors(client):
    """Seed two vendors supplying overlapping items in two currencies.

    Item X (EAN-1): Vendor A sells for 100 SEK (~8.70 EUR), Vendor B for 12 EUR.
    Item Y (EAN-2): Vendor A sells for 200 SEK but is out of stock, Vendor B for 20 EUR.
    """
    db = _dbsession.SessionLocal()
    try:
        db.add_all([Company(id=1, name="Vendor A"), Company(id=2, name="Vendor B")])
        db.add_all(
            [
                VendorProduct(
                    id=1, sku="A-X", name="Widget X", external_reference="EAN-1",
                    unit_cost=100, currency="SEK", stock_quantity=10,
                    availability="in_stock", vendor_id=1,
                ),
                VendorProduct(
                    id=2, sku="B-X", name="Widget X", external_reference="EAN-1",
                    unit_cost=12, currency="EUR", stock_quantity=5,
                    availability="in_stock", vendor_id=2,
                ),
                VendorProduct(
                    id=3, sku="A-Y", name="Gadget Y", external_reference="EAN-2",
                    unit_cost=200, currency="SEK", stock_quantity=0,
                    availability="in_stock", vendor_id=1,
                ),
                VendorProduct(
                    id=4, sku="B-Y", name="Gadget Y", external_reference="EAN-2",
                    unit_cost=20, currency="EUR", stock_quantity=3,
                    availability="in_stock", vendor_id=2,
                ),
            ]
        )
        job = Job(id=1, job_code="J-TEST", status="draft")
        db.add(job)
        db.add(JobRequirement(id=1, job_id=1, vendor_product_id=1, quantity_required=2))
        db.add(JobRequirement(id=2, job_id=1, vendor_product_id=3, quantity_required=1))
        db.add(
            AppSetting(
                key="fx_rates",
                value_json=json.dumps({"base": "EUR", "rates": {"SEK": 0.087}}),
            )
        )
        db.commit()
        return job.id
    finally:
        db.close()


def test_fx_rates_endpoints(client):
    get = client.get("/api/v1/settings/fx-rates")
    assert get.status_code == 200
    assert get.json()["base"] == "EUR"
    assert get.json()["rates"] == {}

    put = client.put(
        "/api/v1/settings/fx-rates",
        json={"base": "EUR", "rates": {"SEK": 0.087, "USD": 0.92}},
    )
    assert put.status_code == 200
    assert put.json()["rates"]["SEK"] == 0.087

    again = client.get("/api/v1/settings/fx-rates").json()
    assert again["rates"]["USD"] == 0.92


def test_convert_handles_rate_inversion_and_fx_missing():
    from app.domain.purchasing.service import convert

    # EUR expressed in SEK (rate stored as "SEK": 0.087, i.e. 1 SEK = 0.087 EUR).
    # Converting EUR -> SEK must invert the rate, not silently pass the amount through.
    amt, missing = convert(100, "EUR", {"base": "EUR", "rates": {"SEK": 0.087}}, "SEK")
    assert not missing
    assert abs(float(amt) - (100 / 0.087)) < 1e-3

    # SEK -> EUR (direct) still works.
    amt, missing = convert(100, "SEK", {"base": "EUR", "rates": {"SEK": 0.087}}, "EUR")
    assert not missing
    assert abs(float(amt) - 8.7) < 1e-6

    # Missing rate must surface as fx_missing, never a mislabelled number.
    amt, missing = convert(100, "EUR", {"base": "SEK", "rates": {}}, "SEK")
    assert missing
    assert amt is None



def test_best_purchase_multi_vs_single(client):
    job_id = _seed_two_vendors(client)

    resp = client.post(f"/api/v1/purchasing/jobs/{job_id}/best-purchase")
    assert resp.status_code == 200
    body = resp.json()
    assert body["draft_id"]
    assert body["report_currency"] == "EUR"

    # Multi-supplier optimiser: cheapest per line -> X from A (8.70*2), Y from B (20).
    multi = body["multi_supplier"]
    assert multi["supplier_count"] == 2
    assert multi["total"] == 37.4
    assert multi["unmet_lines"] == []

    # Single-cheapest supplier: Vendor B covers both lines (44 EUR) vs A (1 line).
    single = body["single_supplier"]
    assert single["vendor_id"] == 2
    assert single["lines_covered"] == 2
    assert single["total"] == 44.0
    assert single["unmet_lines"] == []

    # The persisted draft reflects the multi-supplier basket (2 lines).
    draft = client.get(f"/api/v1/purchasing/drafts/{body['draft_id']}").json()
    assert draft["job_id"] == job_id
    assert draft["supplier_count"] == 2
    assert len(draft["lines"]) == 2
    assert draft["report_currency"] == "EUR"
    # One line sourced from Vendor A, one from Vendor B.
    vendor_ids = {ln["vendor_id"] for ln in draft["lines"]}
    assert vendor_ids == {1, 2}


def test_best_purchase_persists_single_strategy(client):
    job_id = _seed_two_vendors(client)
    resp = client.post(
        f"/api/v1/purchasing/jobs/{job_id}/best-purchase",
        json={"strategy": "single"},
    )
    assert resp.status_code == 200
    draft = client.get(f"/api/v1/purchasing/drafts/{resp.json()['draft_id']}").json()
    # Single supplier (Vendor B) supplies both lines.
    assert draft["supplier_count"] == 1
    assert all(ln["vendor_id"] == 2 for ln in draft["lines"])
    assert len(draft["lines"]) == 2


def test_best_purchase_requires_vendor_linked_requirements(client):
    db = _dbsession.SessionLocal()
    try:
        db.add(Job(id=9, job_code="J-EMPTY", status="draft"))
        # No vendor_product_id -> not a vendor-linked requirement.
        db.add(JobRequirement(id=9, job_id=9, vendor_product_id=None, quantity_required=1))
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/purchasing/jobs/9/best-purchase")
    assert resp.status_code == 400


def test_best_purchase_single_currency_needs_no_fx(client):
    db = _dbsession.SessionLocal()
    try:
        db.add_all([Company(id=1, name="Vendor A"), Company(id=2, name="Vendor B")])
        db.add_all(
            [
                VendorProduct(
                    id=1, sku="A-X", name="Widget X", external_reference="EAN-1",
                    unit_cost=100, currency="SEK", stock_quantity=5,
                    availability="in_stock", vendor_id=1,
                ),
                VendorProduct(
                    id=2, sku="B-X", name="Widget X", external_reference="EAN-1",
                    unit_cost=90, currency="SEK", stock_quantity=5,
                    availability="in_stock", vendor_id=2,
                ),
            ]
        )
        db.add(Job(id=1, job_code="J-SEK", status="draft"))
        db.add(JobRequirement(id=1, job_id=1, vendor_product_id=1, quantity_required=1))
        # Ensure no fx_rates setting interferes (single currency only).
        db.query(AppSetting).filter_by(key="fx_rates").delete()
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/purchasing/jobs/1/best-purchase")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # Single distinct currency -> report currency is SEK, no FX conversion needed.
    assert body["report_currency"] == "SEK"
    for line in body["lines"]:
        for c in line["candidates"]:
            assert c["fx_missing"] is False
            assert c["converted_unit_cost"] == c["unit_cost"]


# --------------------------------------------------------------------------- #
# Purchase orders
# --------------------------------------------------------------------------- #


def _seed_po_fixture():
    """Seed two suppliers, products (one below min stock), and two jobs."""
    db = _dbsession.SessionLocal()
    try:
        db.add_all([Company(id=10, name="Sup X"), Company(id=11, name="Sup Y")])
        db.add_all(
            [
                Customer(id=10, name="Sup X", is_product_supplier=True),
                Customer(id=11, name="Sup Y", is_product_supplier=True),
            ]
        )
        db.add_all(
            [
                Product(id=300, name="Cable", sku="C", min_stock_level=5),
                Product(id=301, name="Server", sku="S"),
            ]
        )
        db.add(
            ProductSupplier(
                id=1, product_id=300, supplier_id=10, supplier_company_id=10,
                is_primary=True, unit_cost=5,
            )
        )
        db.add_all(
            [
                VendorProduct(
                    id=20, sku="SX", name="Server", unit_cost=100, currency="EUR",
                    stock_quantity=2, availability="in_stock", vendor_id=10,
                ),
                VendorProduct(
                    id=21, sku="SY", name="Switch", unit_cost=50, currency="EUR",
                    stock_quantity=2, availability="in_stock", vendor_id=11,
                ),
            ]
        )
        db.add(Job(id=50, job_code="J-C1", status="draft"))
        db.add(Job(id=51, job_code="J-C2", status="draft"))
        db.add(JobRequirement(id=50, job_id=50, vendor_product_id=20, product_id=301, quantity_required=2))
        db.add(JobRequirement(id=51, job_id=51, vendor_product_id=21, quantity_required=3))
        db.commit()
    finally:
        db.close()


def test_create_po_from_draft_groups_by_supplier(client):
    job_id = _seed_two_vendors(client)
    bp = client.post(f"/api/v1/purchasing/jobs/{job_id}/best-purchase").json()
    draft_id = bp["draft_id"]

    resp = client.post(f"/api/v1/purchasing/purchase-orders/from-draft/{draft_id}")
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    # X sourced from Vendor A, Y from Vendor B -> one PO per supplier.
    assert len(pos) == 2
    assert {po["supplier_company_id"] for po in pos} == {1, 2}
    for po in pos:
        assert po["status"] == "draft"
        assert po["po_number"].startswith("PO-")


def test_po_preserves_original_currency_when_fx_missing(client):
    """A line whose currency cannot be converted must keep its original currency
    in the PO/PDF rather than being silently folded into the report currency."""
    from types import SimpleNamespace

    from app.domain.purchasing.pdf import generate_purchase_order_pdf
    from app.domain.purchasing.service import build_purchase_orders

    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=1, name="Anthropic 2"))
        db.add(Customer(id=1, name="Anthropic 2", is_product_supplier=True))
        # FX base is SEK but there is no EUR rate, so EUR lines cannot convert.
        db.add(
            AppSetting(
                key="fx_rates",
                value_json=json.dumps({"base": "SEK", "rates": {"USD": 10}}),
            )
        )
        db.commit()
    finally:
        db.close()

    db = _dbsession.SessionLocal()
    try:
        items = [
            SimpleNamespace(
                vendor_company_id=1, vendor_product_id=None, product_id=None,
                description=None, sku="EUR1", name="Euro item", qty=1,
                unit_cost=179, currency="EUR",
            ),
            SimpleNamespace(
                vendor_company_id=1, vendor_product_id=None, product_id=None,
                description=None, sku="SEK1", name="Sek item", qty=1,
                unit_cost=100, currency="SEK",
            ),
        ]
        pos = build_purchase_orders(db, [], extra_items=items, freight={1: 150})
        po = pos[0]
        assert po.report_currency == "SEK"

        eur_line = [l for l in po.lines if l.currency == "EUR"][0]
        sek_line = [l for l in po.lines if l.currency == "SEK"][0]
        # EUR line could not be converted -> no mislabelled report-currency value.
        assert eur_line.converted_unit_cost is None
        assert eur_line.line_total is None
        # SEK line (== report currency) converts trivially.
        assert sek_line.converted_unit_cost == 100
        assert sek_line.line_total == 100
        # total_base only counts the converted goods line.
        assert po.total_base == 100

        pdf = generate_purchase_order_pdf(db, po)
        # PDF is generated without error and contains the two lines/totals.
        assert len(pdf) > 500
    finally:
        db.close()


def test_combined_po_groups_by_supplier_and_restock(client):
    _seed_po_fixture()
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50, 51], "include_restock": True},
    )
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    # Supplier 10 (Server + restock Cable) and Supplier 11 (Switch).
    assert len(pos) == 2
    by_supplier = {po["supplier_company_id"]: po for po in pos}
    assert 10 in by_supplier and 11 in by_supplier
    sx = by_supplier[10]
    assert len(sx["lines"]) == 2
    restock = [ln for ln in sx["lines"] if ln["is_restock"]]
    assert restock, "restock item should be included"
    assert restock[0]["product_id"] == 300


def test_restock_resolves_vendor_from_vendor_product(client):
    """A below-limit product with no company-linked supplier still yields a
    restock line, using the vendor catalog item's vendor as the supplier."""
    from app.domain.purchasing.service import _collect_restock_lines

    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=20, name="Catalog Vendor"))
        db.add(Product(id=400, name="Gadget", sku="W", min_stock_level=3, min_order_qty=1))
        db.add(
            VendorProduct(
                id=40, sku="W40", name="Widget", unit_cost=12, currency="EUR",
                vendor_id=20,
            )
        )
        db.add(
            ProductSupplier(
                id=5, product_id=400, supplier_id=20, supplier_company_id=None,
                vendor_product_id=40, is_primary=True,
            )
        )
        db.commit()
        lines = _collect_restock_lines(db)
    finally:
        db.close()

    widget = [l for l in lines if l["product_id"] == 400]
    assert widget, "below-limit product should produce a restock line"
    assert widget[0]["vendor_id"] == 20
    assert widget[0]["vendor_product_id"] == 40


def test_receive_po_creates_stock_and_devices(client):
    _seed_po_fixture()
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    )
    po = resp.json()[0]
    line_id = po["lines"][0]["id"]

    rcv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 2}]},
    )
    assert rcv.status_code == 200, rcv.text
    assert rcv.json()["status"] == "received"

    db = _dbsession.SessionLocal()
    try:
        devices = db.query(Device).filter(Device.product_id == 301).count()
        assert devices == 2
    finally:
        db.close()


def test_receive_po_partial_then_full(client):
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    line_id = po["lines"][0]["id"]

    part = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 1}]},
    )
    assert part.json()["status"] == "partial"

    full = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 2}]},
    )
    assert full.json()["status"] == "received"
    db = _dbsession.SessionLocal()
    try:
        # Second receive only adds the remaining delta (1), not double-count.
        assert db.query(Device).filter(Device.product_id == 301).count() == 2
    finally:
        db.close()


def test_receive_po_device_line_empty_devices_creates_none(client):
    """When an explicit (empty) devices list is supplied for a device line, the
    backend must not auto-fill Devices — creation is driven by the provided specs."""
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    line_id = po["lines"][0]["id"]
    assert po["lines"][0]["creates_device"] is True

    rcv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 2, "devices": []}]},
    )
    assert rcv.status_code == 200, rcv.text
    db = _dbsession.SessionLocal()
    try:
        assert db.query(Device).filter(Device.product_id == 301).count() == 0
    finally:
        db.close()


def test_receive_po_sale_article_no_device_records_serials(client):
    """A sale-article line (no linked warehouse product) is received without
    minting Device records; captured serials are stored on the line."""
    _seed_po_fixture()
    created = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [51], "include_restock": False},
    ).json()[0]
    # The GET endpoint computes creates_device from linkage + job requirement.
    po = client.get(f"/api/v1/purchasing/purchase-orders/{created['id']}").json()
    line_id = po["lines"][0]["id"]
    assert po["lines"][0]["creates_device"] is False

    rcv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 3, "serials": ["SN-A", "SN-B"]}]},
    )
    assert rcv.status_code == 200, rcv.text
    assert rcv.json()["status"] == "received"
    db = _dbsession.SessionLocal()
    try:
        assert db.query(Device).count() == 0
        line = db.get(PurchaseOrderLine, line_id)
        assert line.serials == ["SN-A", "SN-B"]
    finally:
        db.close()


def test_receive_po_with_scanned_devices(client):
    """A device line received with an explicit (non-empty) devices list must mint
    one Device per spec, carrying the scanned asset tag / serial / condition."""
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    line_id = po["lines"][0]["id"]

    rcv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={
            "lines": [
                {
                    "line_id": line_id,
                    "received_qty": 2,
                    "devices": [
                        {"asset_tag": "TAG-1", "serial_number": "SN-1", "condition": "good"},
                        {"asset_tag": "TAG-2", "serial_number": "SN-2", "condition": "fair"},
                    ],
                }
            ]
        },
    )
    assert rcv.status_code == 200, rcv.text
    assert rcv.json()["status"] == "received"
    db = _dbsession.SessionLocal()
    try:
        devices = db.query(Device).filter(Device.product_id == 301).all()
        assert len(devices) == 2
        assert {d.asset_tag for d in devices} == {"TAG-1", "TAG-2"}
        assert any(d.serial_number == "SN-1" for d in devices)
        assert any(d.condition == "fair" for d in devices)
    finally:
        db.close()


def test_receive_po_ignores_lower_received_qty(client):
    """A receive payload that lowers received_qty must not decrease the recorded
    count or remove already-minted Device/stock records (stock desync guard)."""
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    line_id = po["lines"][0]["id"]
    client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 1}]},
    )
    rcv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 0}]},
    )
    assert rcv.status_code == 200, rcv.text
    assert rcv.json()["status"] == "partial"
    db = _dbsession.SessionLocal()
    try:
        assert db.query(Device).filter(Device.product_id == 301).count() == 1
        assert db.get(PurchaseOrderLine, line_id).received_qty == 1
    finally:
        db.close()


def test_purchase_order_pdf(client):
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    resp = client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=7, name="Report Supplier AB"))
        db.commit()
    finally:
        db.close()

    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={
            "job_ids": [],
            "extra_items": [
                {
                    "name": "Widget",
                    "qty": 2,
                    "unit_cost": 100,
                    "currency": "SEK",
                    "vendor_company_id": 7,
                }
            ],
        },
    ).json()[0]

    db = _dbsession.SessionLocal()
    try:
        from app.domain.reports.seed import seed_report_templates
        from app.domain.reports.models import ReportTemplate
        from app.services.pdf_service import PDFService

        seed_report_templates(db)
        tpl = db.scalars(
            select(ReportTemplate).where(ReportTemplate.data_source_type == "purchase_order")
        ).first()
        assert tpl is not None

        pdf_en = PDFService(db).generate_pdf(
            tpl.id, "purchase_order", po["id"], language="en"
        )
        assert pdf_en[:4] == b"%PDF"
        assert len(pdf_en) > 500

        pdf_sv = PDFService(db).generate_pdf(
            tpl.id, "purchase_order", po["id"], language="sv"
        )
        assert pdf_sv[:4] == b"%PDF"
    finally:
        db.close()


def _seed_linked_products(client):
    """Two vendor products for the same item stored under different identifiers.

    One was added manually (manufacturer no. lives in ``sku``), the other imported
    (manufacturer no. lives in ``external_reference``). They must still match.
    """
    db = _dbsession.SessionLocal()
    try:
        db.add_all([Company(id=20, name="Anthropic 2"), Company(id=21, name="Aurdel")])
        db.add_all(
            [
                VendorProduct(
                    id=100, sku="U7-Lite", name="Access Point U7 Lite",
                    external_reference=None, unit_cost=10, currency="SEK",
                    stock_quantity=0, availability="out", vendor_id=20,
                ),
                VendorProduct(
                    id=101, sku="2412369", name="U7 Lite", external_reference="U7-Lite",
                    supplier_item_number="2412369", unit_cost=12, currency="SEK",
                    stock_quantity=5, availability="in_stock", vendor_id=21,
                    expected_delivery_date=date(2026, 10, 23), incoming_quantity=60,
                ),
            ]
        )
        db.add(Job(id=60, job_code="J-LINK", status="draft"))
        db.add(JobRequirement(id=60, job_id=60, vendor_product_id=100, quantity_required=1))
        db.commit()
        return 60
    finally:
        db.close()


def test_linked_products_match_across_suppliers(client):
    job_id = _seed_linked_products(client)
    resp = client.post(f"/api/v1/purchasing/jobs/{job_id}/best-purchase")
    assert resp.status_code == 200, resp.text
    line = resp.json()["lines"][0]
    vendor_ids = {c["vendor_id"] for c in line["candidates"]}
    assert vendor_ids == {20, 21}
    # The out-of-stock item surfaces the linked in-stock alternative's ETA.
    assert line["next_restock_date"] == "2026-10-23"


def test_preview_lists_alternative_suppliers(client):
    job_id = _seed_two_vendors(client)
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/preview",
        json={"job_ids": [job_id], "include_restock": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "lines" in body
    lines = body["lines"]
    assert len(lines) == 2
    for line in lines:
        assert len(line["candidates"]) >= 2  # selected + at least one alternative
    assert body["report_currency"] in {None, "SEK", "EUR"}
    assert isinstance(body["freight"], dict)


def test_build_po_from_selections_chooses_supplier(client):
    job_id = _seed_two_vendors(client)
    # Force both lines onto Vendor B by choosing its vendor products.
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/build",
        json={
            "lines": [
                {"requirement_id": 1, "vendor_product_id": 2, "qty": 2},
                {"requirement_id": 2, "vendor_product_id": 4, "qty": 1},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    assert len(pos) == 1
    assert pos[0]["supplier_company_id"] == 2
    assert len(pos[0]["lines"]) == 2


def test_from_job_creates_po(client):
    job_id = _seed_two_vendors(client)
    resp = client.post(f"/api/v1/purchasing/purchase-orders/from-job/{job_id}")
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    # Both linked vendor products are from Vendor A -> single PO.
    assert len(pos) == 1
    assert pos[0]["supplier_company_id"] == 1


def test_add_lines_to_po_and_reject_wrong_supplier(client):
    job_id = _seed_two_vendors(client)
    po = client.post(f"/api/v1/purchasing/purchase-orders/from-job/{job_id}").json()[0]
    po_id = po["id"]
    initial_lines = len(po["lines"])

    # Same supplier -> appended.
    add = client.post(
        f"/api/v1/purchasing/purchase-orders/{po_id}/add-lines",
        json={"lines": [{"requirement_id": 1, "vendor_product_id": 1}]},
    )
    assert add.status_code == 200, add.text
    assert len(add.json()["lines"]) == initial_lines + 1

    # Different supplier -> rejected.
    bad = client.post(
        f"/api/v1/purchasing/purchase-orders/{po_id}/add-lines",
        json={"lines": [{"requirement_id": 1, "vendor_product_id": 2}]},
    )
    assert bad.status_code == 400


def test_delete_purchase_order(client):
    job_id = _seed_two_vendors(client)
    po = client.post(f"/api/v1/purchasing/purchase-orders/from-job/{job_id}").json()[0]
    po_id = po["id"]

    # Delete succeeds.
    resp = client.delete(f"/api/v1/purchasing/purchase-orders/{po_id}")
    assert resp.status_code == 204, resp.text

    # Gone afterwards.
    gone = client.get(f"/api/v1/purchasing/purchase-orders/{po_id}")
    assert gone.status_code == 404

    # Deleting again is a 404, not a 500.
    again = client.delete(f"/api/v1/purchasing/purchase-orders/{po_id}")
    assert again.status_code == 404


def test_delete_received_purchase_order_rejected(client):
    """A PO that has been (partially) received must not be deleted: its stock is
    represented by Device records with no FK back to the PO, so deletion would
    silently orphan inventory."""
    _seed_po_fixture()
    po = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": False},
    ).json()[0]
    line_id = po["lines"][0]["id"]
    client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 1}]},
    )

    resp = client.delete(f"/api/v1/purchasing/purchase-orders/{po['id']}")
    assert resp.status_code == 400, resp.text

    # Still present afterwards.
    still = client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}")
    assert still.status_code == 200


def test_build_po_includes_supplier_freight(client):
    job_id = _seed_two_vendors(client)
    db = _dbsession.SessionLocal()
    try:
        c1 = db.get(Company, 1)
        c2 = db.get(Company, 2)
        c1.freight_cost = 50
        c1.freight_currency = "SEK"
        c2.freight_cost = 120
        c2.freight_currency = "SEK"
        db.commit()
    finally:
        db.close()

    # Both lines forced onto Vendor A (company 1, SEK) -> single PO with its freight.
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/build",
        json={
            "lines": [
                {"requirement_id": 1, "vendor_product_id": 1, "qty": 2},
                {"requirement_id": 2, "vendor_product_id": 3, "qty": 1},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    po = resp.json()[0]
    assert po["supplier_company_id"] == 1
    # Freight is applied (converted to the report currency, here SEK == SEK).
    assert po["freight_base"] is not None
    assert abs(po["freight_base"] - 50) < 0.001
    # Grand total = goods subtotal + freight.
    assert abs(po["grand_total_base"] - (po["total_base"] + po["freight_base"])) < 0.001


def test_freight_override_in_build_request(client):
    job_id = _seed_two_vendors(client)
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/build",
        json={
            "lines": [
                {"requirement_id": 1, "vendor_product_id": 2, "qty": 2},
                {"requirement_id": 2, "vendor_product_id": 4, "qty": 1},
            ],
            "freight": {2: 9.99},
        },
    )
    assert resp.status_code == 200, resp.text
    po = resp.json()[0]
    assert abs(po["freight_base"] - 9.99) < 0.001


def test_restock_line_uses_vendor_product_currency(client):
    _seed_po_fixture()
    db = _dbsession.SessionLocal()
    try:
        db.add(
            VendorProduct(
                id=50, sku="C", name="Cable", unit_cost=7, currency="EUR",
                stock_quantity=10, availability="in_stock", vendor_id=10,
            )
        )
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={"job_ids": [50], "include_restock": True},
    )
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    sx = [po for po in pos if po["supplier_company_id"] == 10][0]
    restock = [ln for ln in sx["lines"] if ln["is_restock"]]
    assert restock, "restock line should be included"
    r = restock[0]
    # Cost + currency come from the matched vendor catalog item, not blank.
    assert r["currency"] == "EUR"
    assert r["vendor_product_id"] == 50
    assert r["unit_cost"] == 7


def test_products_search_and_exclude_rental(client):
    db = _dbsession.SessionLocal()
    try:
        db.add_all([
            Product(id=900, sku="RENT-1", name="Camera Rental", is_rental_product=True),
            Product(id=901, sku="BUY-1", name="Cable Buy", is_rental_product=False),
        ])
        db.commit()
    finally:
        db.close()
    resp = client.get("/api/v1/inventory/products?exclude_rental=true&limit=50")
    skus = {p["sku"] for p in resp.json()["items"]}
    assert "RENT-1" not in skus
    assert "BUY-1" in skus
    resp = client.get("/api/v1/inventory/products?search=Cable&limit=50")
    skus = {p["sku"] for p in resp.json()["items"]}
    assert "BUY-1" in skus
    assert "RENT-1" not in skus


def test_product_purchase_info_links_vendor_catalog_item(client):
    db = _dbsession.SessionLocal()
    try:
        db.add_all([
            Company(id=20, name="Sup Z"),
            Customer(id=20, name="Sup Z", is_product_supplier=True),
        ])
        db.add(Product(id=910, sku="PI-1", name="Widget", min_stock_level=3, min_order_qty=2))
        db.add(ProductSupplier(id=10, product_id=910, supplier_id=20, supplier_company_id=20, is_primary=True, unit_cost=5))
        db.add(VendorProduct(id=60, sku="PI-1", name="Widget", unit_cost=12, currency="USD", stock_quantity=4, availability="in_stock", vendor_id=20))
        db.commit()
    finally:
        db.close()
    resp = client.get("/api/v1/inventory/products/910/purchase-info")
    assert resp.status_code == 200, resp.text
    info = resp.json()
    assert info["supplier_company_id"] == 20
    assert info["vendor_product_id"] == 60
    assert float(info["unit_cost"]) == 12
    assert info["currency"] == "USD"
    assert info["min_stock_level"] == 3


def test_fetch_fx_rates_inverts_provider(monkeypatch):
    from app.domain.purchasing import fx_sync

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"base": "EUR", "rates": {"SEK": 11.49, "USD": 1.08}}

    class FakeHttpx:
        def get(self, url, params=None, timeout=None, follow_redirects=False):
            return FakeResp()

    monkeypatch.setattr(fx_sync.httpx, "get", FakeHttpx().get)
    result = fx_sync.fetch_fx_rates("EUR")
    assert result["base"] == "EUR"
    assert abs(result["rates"]["SEK"] - (1 / 11.49)) < 1e-4
    assert abs(result["rates"]["USD"] - (1 / 1.08)) < 1e-4


def test_refresh_fx_rates_uses_company_currency(monkeypatch, db_session):
    from app.domain.purchasing import fx_sync

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"base": "SEK", "rates": {"EUR": 0.087, "USD": 0.095}}

    class FakeHttpx:
        def get(self, url, params=None, timeout=None, follow_redirects=False):
            assert params.get("from") == "SEK"
            return FakeResp()

    monkeypatch.setattr(fx_sync.httpx, "get", FakeHttpx().get)
    data = fx_sync.refresh_fx_rates(db_session)
    assert data["base"] == "SEK"
    assert "EUR" in data["rates"]
    assert "USD" in data["rates"]


def test_update_and_delete_po_line(client):
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=5, name="Line Supplier"))
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={
            "job_ids": [],
            "extra_items": [
                {
                    "name": "Gizmo",
                    "qty": 2,
                    "unit_cost": 100,
                    "currency": "SEK",
                    "vendor_company_id": 5,
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    assert len(pos) == 1
    po = pos[0]
    assert len(po["lines"]) == 1
    line_id = po["lines"][0]["id"]

    # Update the line.
    upd = client.put(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}",
        json={"qty": 5, "unit_cost": 12.5, "currency": "SEK", "name": "Gizmo X"},
    )
    assert upd.status_code == 200, upd.text
    data = upd.json()
    assert data["qty"] == 5
    assert data["unit_cost"] == 12.5
    assert data["name"] == "Gizmo X"
    assert abs((data["line_total"] or 0) - 62.5) < 0.01

    # A line belonging to a different PO returns 404.
    missing = client.put(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/999999",
        json={"qty": 1},
    )
    assert missing.status_code == 404

    # Delete the line.
    dele = client.delete(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}"
    )
    assert dele.status_code == 204
    get = client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}")
    assert get.status_code == 200
    assert get.json()["lines"] == []


def test_cannot_edit_received_po_line(client):
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=6, name="Recv Supplier"))
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/purchasing/purchase-orders/combined",
        json={
            "job_ids": [],
            "extra_items": [
                {
                    "name": "Locked item",
                    "qty": 2,
                    "unit_cost": 50,
                    "currency": "SEK",
                    "vendor_company_id": 6,
                }
            ],
        },
    )
    po = resp.json()[0]
    line_id = po["lines"][0]["id"]
    recv = client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/receive",
        json={"lines": [{"line_id": line_id, "received_qty": 1}]},
    )
    assert recv.status_code == 200, recv.text

    upd = client.put(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}",
        json={"qty": 9},
    )
    assert upd.status_code == 400
    dele = client.delete(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}"
    )
    assert dele.status_code == 400


def _seed_receiving_fixture():
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=10, name="Sup X"))
        db.add(Product(id=301, name="Server", sku="S", barcode="BC-123"))
        db.add(
            PurchaseOrder(
                id=9001, po_number="PO-RCV", supplier_company_id=10,
                status="draft", report_currency="EUR",
            )
        )
        db.add(
            PurchaseOrderLine(
                id=9001, po_id=9001, product_id=301, qty=3, received_qty=0,
                unit_cost=100, currency="EUR", name="Server", sku="S",
            )
        )
        db.commit()
    finally:
        db.close()


def test_receiving_lookup_by_barcode(client):
    _seed_receiving_fixture()
    resp = client.get("/api/v1/purchasing/receiving/lookup?code=BC-123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["product"] is not None
    assert body["product"]["barcode"] == "BC-123"
    assert len(body["lines"]) == 1
    line = body["lines"][0]
    assert line["line_id"] == 9001
    assert line["remaining"] == 3

    # SKU fallback also resolves the same product.
    resp2 = client.get("/api/v1/purchasing/receiving/lookup?code=S")
    assert resp2.status_code == 200
    assert resp2.json()["product"]["id"] == 301

    # Unknown code yields no product and no lines.
    resp3 = client.get("/api/v1/purchasing/receiving/lookup?code=NOPE")
    assert resp3.json()["product"] is None
    assert resp3.json()["lines"] == []


def test_receiving_lookup_excludes_received_po(client):
    """A received PO must not surface in receiving lookup (open-status guard)."""
    _seed_receiving_fixture()
    db = _dbsession.SessionLocal()
    try:
        po = db.get(PurchaseOrder, 9001)
        po.status = "received"
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/purchasing/receiving/lookup?code=BC-123")
    assert resp.status_code == 200, resp.text
    assert resp.json()["lines"] == []


def test_reorder_product_supplier_opens_new_po(client):
    """Reordering a linked product opens a new draft PO carrying a restock line."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=70, name="Reorder Vendor"))
        db.add(Product(id=700, name="Toner", sku="T", min_stock_level=2, min_order_qty=3))
        db.add(
            VendorProduct(id=70, sku="T-VP", name="Toner", unit_cost=9, currency="EUR", vendor_id=70)
        )
        db.add(
            ProductSupplier(
                id=70, product_id=700, supplier_id=70, supplier_company_id=70,
                is_primary=True, vendor_product_id=70,
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/inventory/products/700/suppliers/70/reorder", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    po_id, line_id = body["po_id"], body["line_id"]
    assert po_id and line_id

    po = client.get(f"/api/v1/purchasing/purchase-orders/{po_id}").json()
    assert po["status"] == "draft"
    line = next(l for l in po["lines"] if l["id"] == line_id)
    assert line["is_restock"] is True
    assert line["product_id"] == 700
    assert float(line["unit_cost"]) == 9.0


def test_reorder_product_supplier_rejects_mismatched_po(client):
    """Reordering onto a PO whose supplier differs from the vendor item is rejected."""
    db = _dbsession.SessionLocal()
    try:
        db.add_all([Company(id=71, name="V1"), Company(id=72, name="V2")])
        db.add(Product(id=701, name="Ink", sku="I", min_stock_level=1))
        db.add(
            VendorProduct(id=71, sku="I-VP", name="Ink", unit_cost=5, currency="EUR", vendor_id=71)
        )
        db.add(
            ProductSupplier(
                id=71, product_id=701, supplier_id=71, supplier_company_id=71,
                is_primary=True, vendor_product_id=71,
            )
        )
        db.add(
            PurchaseOrder(
                id=7701, po_number="PO-MISMATCH", supplier_company_id=72,
                status="draft", report_currency="EUR",
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/inventory/products/701/suppliers/71/reorder",
        json={"po_id": 7701},
    )
    assert resp.status_code == 400, resp.text


def test_low_stock_lists_below_min(client):
    """Only products whose device count is below min_stock_level appear."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Product(id=710, name="Paper", sku="P", min_stock_level=5))
        db.add(Product(id=711, name="Clip", sku="CL", min_stock_level=5))
        for i in range(5):
            db.add(Device(id=9000 + i, product_id=711, asset_tag=f"CL-{i}"))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/low-stock")
    assert resp.status_code == 200, resp.text
    ids = {p["product_id"] for p in resp.json()}
    assert 710 in ids
    assert 711 not in ids


def test_receive_po_with_serials(client):
    _seed_receiving_fixture()
    rcv = client.post(
        "/api/v1/purchasing/purchase-orders/9001/receive",
        json={
            "lines": [
                {
                    "line_id": 9001,
                    "received_qty": 2,
                    "devices": [
                        {"serial_number": "SN-1", "condition": "new"},
                        {"serial_number": "SN-2"},
                    ],
                }
            ]
        },
    )
    assert rcv.status_code == 200, rcv.text
    assert rcv.json()["status"] == "partial"

    db = _dbsession.SessionLocal()
    try:
        serials = [
            s
            for (s,) in db.query(Device.serial_number)
            .filter(Device.product_id == 301)
            .all()
        ]
        assert set(serials) == {"SN-1", "SN-2"}
    finally:
        db.close()


def test_generate_asset_tag_route_not_shadowed(client):
    """GET /devices/generate-asset-tag must not be caught by /devices/{device_id}
    (which would 422 trying to parse the literal 'generate-asset-tag' as int)."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Product(id=888, name="Receive Gadget", sku="RG", product_type="rental"))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/devices/generate-asset-tag?product_id=888")
    assert resp.status_code == 200, resp.text
    assert resp.json()["asset_tag"]


def test_generate_asset_tag_named_route_resolves(client):
    """The literal 'generate-asset-tag' must resolve to the named route, not 422."""
    resp = client.get("/api/v1/inventory/devices/generate-asset-tag")
    assert resp.status_code == 200, resp.text


def test_product_purchase_info_uses_explicit_vendor_link(client):
    """A product linked to a vendor catalog item via ProductSupplier.vendor_product_id
    must return that item's unit_cost/currency even when SKU/name don't match."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=30, name="Linked Vendor"))
        db.add(Product(id=500, name="Odd Name", sku="ODD", product_type="consumable"))
        db.add(
            VendorProduct(
                id=50, sku="DIFFERENT", name="Different Name", unit_cost=42,
                currency="EUR", vendor_id=30,
            )
        )
        db.add(
            ProductSupplier(
                id=7, product_id=500, supplier_id=30, supplier_company_id=None,
                vendor_product_id=50, is_primary=True,
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/products/500/purchase-info")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor_product_id"] == 50
    assert float(body["unit_cost"]) == 42.0
    assert body["currency"] == "EUR"


def test_preview_include_restock_lists_consumable(client):
    """Toggling include_restock must surface a below-limit consumable whose vendor
    is resolved through ProductSupplier.vendor_product_id (the common Thomann
    import case), even with no job requirements selected."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=31, name="Thomann Co"))
        db.add(Product(id=501, name="Test förbrukningsvara", sku="TC", product_type="consumable", min_stock_level=10))
        db.add(Device(id=9001, product_id=501, asset_tag="TC-1"))
        db.add(
            VendorProduct(id=51, sku="TC-VP", name="Test förbrukningsvara", unit_cost=9, currency="EUR", vendor_id=31)
        )
        db.add(
            ProductSupplier(id=8, product_id=501, supplier_id=31, supplier_company_id=None, vendor_product_id=51, is_primary=True)
        )
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/purchasing/purchase-orders/preview",
        json={"job_ids": [], "include_restock": True},
    )
    assert resp.status_code == 200, resp.text
    lines = resp.json()["lines"]
    restock = [l for l in lines if l.get("is_restock") and l.get("product_id") == 501]
    assert restock, "below-limit consumable should appear when include_restock is on"
    cand = (restock[0]["candidates"] or [{}])[0]
    assert cand.get("vendor_id") == 31
    assert float(cand.get("unit_cost")) == 9.0
    assert cand.get("currency") == "EUR"


def test_product_purchase_info_links_non_primary_supplier(client):
    """The linked vendor catalog item may sit on a secondary (non-primary) supplier
    row; purchase-info must still return its unit_cost/currency."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=40, name="Primary NoLink"))
        db.add(Company(id=41, name="Secondary Linked"))
        db.add(Product(id=502, name="NonPrimary Item", sku="NPI", product_type="consumable"))
        db.add(
            VendorProduct(
                id=52, sku="NPI-VP", name="NonPrimary Item", unit_cost=77,
                currency="GBP", vendor_id=41,
            )
        )
        db.add(
            ProductSupplier(id=9, product_id=502, supplier_id=40, supplier_company_id=40, is_primary=True)
        )
        db.add(
            ProductSupplier(id=10, product_id=502, supplier_id=41, supplier_company_id=41, vendor_product_id=52)
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/products/502/purchase-info")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor_product_id"] == 52
    assert float(body["unit_cost"]) == 77.0
    assert body["currency"] == "GBP"


def test_restock_without_company_uses_customer_name(client):
    """A below-limit product linked only to a Customer (no Company) must still be
    restocked, with the supplier filled from the Customer name."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Customer(id=60, name="Loose Customer", is_product_supplier=True))
        db.add(Product(id=503, name="Loose Item", sku="LI", product_type="consumable", min_stock_level=5))
        db.add(
            ProductSupplier(id=11, product_id=503, supplier_id=60, supplier_company_id=None, is_primary=True)
        )
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/purchasing/purchase-orders/build",
        json={"lines": [], "include_restock": True},
    )
    assert resp.status_code == 200, resp.text
    pos = resp.json()
    assert len(pos) == 1
    assert pos[0]["supplier_name"] == "Loose Customer"
    line = pos[0]["lines"][0]
    assert line["name"] == "Loose Item"


def test_purchase_info_prefers_priced_sku_match(client):
    """When a product isn't explicitly linked, a confident SKU match to a vendor
    catalog item must resolve to the priced variant, not a priceless one."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=50, name="Some Vendor"))
        db.add(Product(id=504, name="Generic Widget", sku="GW", product_type="consumable"))
        # Two catalog items share the exact SKU; one has a price, one doesn't.
        db.add(
            VendorProduct(id=60, sku="GW", name="Generic Widget", unit_cost=None, currency="EUR", vendor_id=50)
        )
        db.add(
            VendorProduct(id=61, sku="GW", name="Generic Widget", unit_cost=88, currency="EUR", vendor_id=50)
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/products/504/purchase-info")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor_product_id"] == 61
    assert float(body["unit_cost"]) == 88.0
    assert body["currency"] == "EUR"


def test_purchase_info_no_name_only_match_without_link(client):
    """A coincidental exact-name match must NOT price a product that has no
    explicit supplier link and no SKU/external-reference match."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=50, name="Some Vendor"))
        db.add(Product(id=505, name="Generic Widget", sku="XYZ", product_type="consumable"))
        db.add(
            VendorProduct(id=62, sku="OTHER", name="Generic Widget", unit_cost=88, currency="EUR", vendor_id=50)
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/products/505/purchase-info")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor_product_id"] is None
    assert body["unit_cost"] is None


def test_build_extra_items_count_in_total(client):
    """Restock/extra items sent with a resolved supplier and unit cost must be
    included in the resulting PO's line goods total, not silently dropped."""
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=70, name="Extra Vendor"))
        db.add(
            VendorProduct(id=71, sku="X-1", name="Extra Item", unit_cost=12.5, currency="SEK", vendor_id=70)
        )
        db.commit()
    finally:
        db.close()

    payload = {
        "prefer_same_supplier": False,
        "extra_items": [
            {
                "name": "Extra Item",
                "qty": 4,
                "unit_cost": 12.5,
                "currency": "SEK",
                "vendor_company_id": 70,
                "vendor_product_id": 71,
            }
        ],
    }
    resp = client.post("/api/v1/purchasing/purchase-orders/build", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    order = data[0]
    line = next((l for l in order["lines"] if l["name"] == "Extra Item"), None)
    assert line is not None
    assert float(line["line_total"]) == 50.0
    assert float(order["total_base"]) == 50.0


def test_build_extra_item_manual_supplier_counts(client):
    """A restock/extra item with a manual price but no linked vendor must still
    be accepted (carried supplier name) and counted in the PO total."""
    payload = {
        "prefer_same_supplier": False,
        "extra_items": [
            {
                "name": "No Vendor Item",
                "qty": 2,
                "unit_cost": 75.0,
                "currency": "SEK",
                "supplier_name": "Manuell",
            }
        ],
    }
    resp = client.post("/api/v1/purchasing/purchase-orders/build", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1
    order = data[0]
    assert order["supplier_name"] == "Manuell"
    line = next((l for l in order["lines"] if l["name"] == "No Vendor Item"), None)
    assert line is not None
    assert float(line["line_total"]) == 150.0
    assert float(order["total_base"]) == 150.0


def test_build_extra_item_restock_flag(client):
    """A restock item sent via build's extra_items (is_restock=True) must be tagged
    as a restock line, not a manual line, so it renders/PDFs consistently."""
    payload = {
        "prefer_same_supplier": False,
        "extra_items": [
            {
                "name": "Restock Widget",
                "qty": 3,
                "unit_cost": 10.0,
                "currency": "SEK",
                "vendor_company_id": 70,
                "is_restock": True,
            }
        ],
    }
    resp = client.post("/api/v1/purchasing/purchase-orders/build", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    line = data[0]["lines"][0]
    assert line["is_restock"] is True
    assert line["is_manual"] is False
