"""Tests for linking warehouse products to vendor catalog items and reordering."""
from decimal import Decimal

from app.db import session as _dbsession
from app.domain.customers.models import Company
from app.domain.inventory.models import Product, ProductSupplier, VendorProduct
from app.domain.purchasing.models import PurchaseOrder


def _seed(db=None):
    own = db is None
    s = db or _dbsession.SessionLocal()
    try:
        s.add(Company(id=1, name="Thomann"))
        s.add(Company(id=1, name="Thomann Supplier", is_product_supplier=True))
        s.add(Product(id=1, sku="P-1", name="Mic Stand", min_order_qty=2))
        s.add(
            VendorProduct(
                id=1,
                sku="T-1",
                name="Mic Stand",
                unit_cost=199,
                currency="SEK",
                vendor_id=1,
                stock_quantity=5,
                availability="in_stock",
                product_url="https://www.thomann.se/mic_stand.html",
            )
        )
        s.commit()
    finally:
        if own:
            s.close()


def _link(client):
    r = client.put(
        "/api/v1/inventory/products/1/suppliers",
        json=[{"supplier_id": 1, "vendor_product_id": 1, "is_primary": True}],
    )
    assert r.status_code == 200, r.text
    return r.json()[0]["id"]


def test_supplier_link_returns_vendor_product(client):
    _seed()
    link_id = _link(client)
    res = client.get("/api/v1/inventory/products/1/suppliers")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == link_id
    assert body[0]["vendor_product_id"] == 1
    vp = body[0]["vendor_product"]
    assert vp is not None
    assert vp["name"] == "Mic Stand"
    assert vp["unit_cost"] == "199.00"
    assert vp["currency"] == "SEK"
    assert vp["product_url"].endswith("mic_stand.html")


def test_reorder_creates_new_po(client):
    _seed()
    link_id = _link(client)
    res = client.post(
        f"/api/v1/inventory/products/1/suppliers/{link_id}/reorder", json={}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["po_id"] and data["po_number"]

    db = _dbsession.SessionLocal()
    try:
        po = db.get(PurchaseOrder, data["po_id"])
        assert po is not None
        assert po.supplier_company_id == 1
        assert po.status == "draft"
        assert len(po.lines) == 1
        line = po.lines[0]
        assert line.is_restock is True
        assert line.vendor_product_id == 1
        assert line.product_id == 1
        # qty falls back to the product's min_order_qty (2)
        assert line.qty == 2
        assert line.unit_cost == Decimal("199.00")
        assert line.currency == "SEK"
        assert po.total_base is not None
    finally:
        db.close()


def test_reorder_existing_po(client):
    _seed()
    link_id = _link(client)
    db = _dbsession.SessionLocal()
    try:
        po = PurchaseOrder(
            status="draft",
            supplier_company_id=1,
            report_currency="SEK",
            po_number="PO-000001",
            total_base=0,
        )
        db.add(po)
        db.commit()
        po_id = po.id
    finally:
        db.close()

    res = client.post(
        f"/api/v1/inventory/products/1/suppliers/{link_id}/reorder",
        json={"po_id": po_id, "qty": 3},
    )
    assert res.status_code == 200, res.text
    assert res.json()["po_id"] == po_id

    db = _dbsession.SessionLocal()
    try:
        po = db.get(PurchaseOrder, po_id)
        assert len(po.lines) == 1
        assert po.lines[0].qty == 3
        assert po.lines[0].is_restock is True
        # 3 * 199 = 597
        assert po.total_base == Decimal("597.00")
    finally:
        db.close()


def test_reorder_vendor_mismatch_rejected(client):
    _seed()
    link_id = _link(client)
    db = _dbsession.SessionLocal()
    try:
        db.add(Company(id=2, name="Other vendor"))
        po = PurchaseOrder(
            status="draft",
            supplier_company_id=2,
            report_currency="SEK",
            po_number="PO-000002",
        )
        db.add(po)
        db.commit()
        po_id = po.id
    finally:
        db.close()

    res = client.post(
        f"/api/v1/inventory/products/1/suppliers/{link_id}/reorder",
        json={"po_id": po_id},
    )
    assert res.status_code == 400, res.text
    assert "supplier" in res.json()["detail"].lower()


def test_reorder_requires_vendor_product(client):
    _seed()
    db = _dbsession.SessionLocal()
    try:
        link = ProductSupplier(product_id=1, supplier_id=1, is_primary=True)
        db.add(link)
        db.commit()
        link_id = link.id
    finally:
        db.close()

    res = client.post(
        f"/api/v1/inventory/products/1/suppliers/{link_id}/reorder", json={}
    )
    assert res.status_code == 400, res.text
    assert "no linked vendor" in res.json()["detail"].lower()


def test_link_inherits_vendor_barcode(client):
    _seed()
    db = _dbsession.SessionLocal()
    try:
        vp = db.get(VendorProduct, 1)
        vp.barcode = "4001234567890"
        db.commit()
    finally:
        db.close()

    _link(client)

    db = _dbsession.SessionLocal()
    try:
        product = db.get(Product, 1)
        assert product.barcode == "4001234567890"
    finally:
        db.close()


def test_link_rejects_no_price_vendor_item(client):
    """Saving a supplier link to a vendor catalog item that has no unit cost (and
    supplying no manual cost) must be rejected so the PO line isn't priceless."""
    _seed()
    db = _dbsession.SessionLocal()
    try:
        db.add(
            VendorProduct(
                id=2, sku="T-2", name="No Price Item", unit_cost=None,
                currency="SEK", vendor_id=1, stock_quantity=1, availability="in_stock",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.put(
        "/api/v1/inventory/products/1/suppliers",
        json=[{"supplier_id": 1, "vendor_product_id": 2, "is_primary": True}],
    )
    assert r.status_code == 400, r.text
    assert "unit cost" in r.json()["detail"].lower()

    # Supplying a manual cost alongside the no-price link is allowed.
    r2 = client.put(
        "/api/v1/inventory/products/1/suppliers",
        json=[{"supplier_id": 1, "vendor_product_id": 2, "is_primary": True, "unit_cost": 50}],
    )
    assert r2.status_code == 200, r2.text
