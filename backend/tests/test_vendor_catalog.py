"""Tests for the vendor catalog subsystem (products, sources, importer)."""
from app.domain.inventory.vendor_catalog import (
    AurdelPricesPlugin,
    get_plugin,
    infer_field_map,
    parse_xml_items,
    upsert_vendor_products,
)


def test_vendor_product_crud(client):
    create = client.post(
        "/api/v1/vendor-products",
        json={"name": "Vendor Widget", "sku": "VW-1", "unit_cost": 10.5},
    )
    assert create.status_code == 201
    vp_id = create.json()["id"]

    listing = client.get("/api/v1/vendor-products")
    assert listing.status_code == 200
    assert any(v["id"] == vp_id for v in listing.json())

    got = client.get(f"/api/v1/vendor-products/{vp_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "Vendor Widget"

    updated = client.put(f"/api/v1/vendor-products/{vp_id}", json={"name": "Widget Pro"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Widget Pro"

    deleted = client.delete(f"/api/v1/vendor-products/{vp_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/vendor-products/{vp_id}").status_code == 404


def test_list_importer_plugins(client):
    resp = client.get("/api/v1/vendor-catalog/plugins")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()}
    assert "generic_api" in ids
    assert "generic_csv" in ids


def test_vendor_sources_crud(client):
    listing = client.get("/api/v1/vendor-catalog/sources")
    assert listing.status_code == 200
    assert listing.json() == []

    created = client.post(
        "/api/v1/vendor-catalog/sources",
        json={
            "name": "Acme feed",
            "plugin_id": "generic_csv",
            "config": {"url": "https://example.com/feed.csv"},
            "field_map": {"sku": "sku", "name": "name", "unit_cost": "price"},
        },
    )
    assert created.status_code == 201
    source_id = created.json()["id"]
    assert created.json()["plugin_id"] == "generic_csv"

    listing = client.get("/api/v1/vendor-catalog/sources")
    assert len(listing.json()) == 1

    updated = client.put(
        f"/api/v1/vendor-catalog/sources/{source_id}", json={"name": "Acme feed v2"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Acme feed v2"

    deleted = client.delete(f"/api/v1/vendor-catalog/sources/{source_id}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/vendor-catalog/sources").json() == []


def test_delete_source_cascades_products(client):
    source = client.post(
        "/api/v1/vendor-catalog/sources",
        json={"name": "Thomann feed", "plugin_id": "thomann_scraper", "config": {"url": "x"}},
    )
    assert source.status_code == 201
    source_id = source.json()["id"]

    vp1 = client.post(
        "/api/v1/vendor-products",
        json={"name": "Thomann Köp A", "sku": "A", "source_plugin": "thomann_scraper"},
    ).json()["id"]
    vp2 = client.post(
        "/api/v1/vendor-products",
        json={"name": "Keep me", "sku": "K", "source_plugin": "generic_csv"},
    ).json()["id"]

    # Without delete_products, products survive.
    del_resp = client.delete(f"/api/v1/vendor-catalog/sources/{source_id}")
    assert del_resp.status_code == 204
    assert client.get(f"/api/v1/vendor-products/{vp1}").status_code == 200

    # Recreate the source and cascade-delete this time.
    source_id = client.post(
        "/api/v1/vendor-catalog/sources",
        json={"name": "Thomann feed", "plugin_id": "thomann_scraper", "config": {"url": "x"}},
    ).json()["id"]
    resp = client.delete(
        f"/api/v1/vendor-catalog/sources/{source_id}", params={"delete_products": True}
    )
    assert resp.status_code == 204
    assert client.get(f"/api/v1/vendor-products/{vp1}").status_code == 404
    # Unrelated product is untouched.
    assert client.get(f"/api/v1/vendor-products/{vp2}").status_code == 200


def test_importer_normalize_and_upsert(db_session):
    plugin = get_plugin(
        "generic_csv",
        {"sku": "sku", "name": "name", "unit_cost": "price"},
        {},
    )
    records = plugin.normalize(
        [
            {"sku": "A1", "name": "Speaker", "price": "12.50"},
            {"sku": "B2", "name": "Cable", "price": "3.00"},
        ]
    )
    assert len(records) == 2
    assert records[0].unit_cost == 12.5

    result = upsert_vendor_products(db_session, records, vendor_id=None, source_plugin=None)
    assert result["created"] == 2

    # Re-running the same external references should update, not create.
    result2 = upsert_vendor_products(db_session, records, vendor_id=None, source_plugin=None)
    assert result2["updated"] == 2
    assert result2["created"] == 0


def test_infer_field_map_from_csv_headers():
    headers = [
        "Index", "Name", "Description", "Brand", "Category", "Price",
        "Currency", "Stock", "EAN", "Color", "Size", "Availability", "Internal ID",
    ]
    mapping = infer_field_map(headers)
    assert mapping["name"] == "Name"
    assert mapping["unit_cost"] == "Price"
    assert mapping["currency"] == "Currency"
    assert mapping["stock_quantity"] == "Stock"
    assert mapping["availability"] == "Availability"
    assert mapping["external_reference"] == "EAN"
    assert mapping["sku"] == "Internal ID"


def test_parse_xml_items_handles_nested_and_repeating():
    xml = (
        "<Prices>"
        "<Item><ItemNo>1001</ItemNo><ItemName>Stage light</ItemName>"
        "<Price>199.50</Price><Currency>SEK</Currency><Stock>12</Stock></Item>"
        "<Item><ItemNo>1002</ItemNo><ItemName>Truss</ItemName>"
        "<Price>899</Price><Currency>SEK</Currency><Stock>3</Stock></Item>"
        "</Prices>"
    )
    items = parse_xml_items(xml)
    assert len(items) == 2
    assert items[0]["ItemName"] == "Stage light"
    assert items[1]["ItemNo"] == "1002"


def test_aurdel_net_with_chemical_tax_attribute():
    # <net includedchemicaltax="...">385,57</net> is a text+attribute node.
    # The price must be the text value, not a mangled attribute-dict repr.
    xml = (
        "<database>"
        "<item id=\"DPE-101GI\">"
        "<description><short>1-Port Gigabit PoE Injector</short></description>"
        "<manufacturer id=\"DPE-101GI\"><description>dlink</description></manufacturer>"
        "<ean>790069341335</ean>"
        "<price currencycode=\"SEK\"><net includedchemicaltax=\"81,32\">385,57</net></price>"
        "</item>"
        "<item id=\"OTHER\"><description><short>Other</short></description>"
        "<manufacturer id=\"OTHER\"><description>acme</description></manufacturer>"
        "<ean>123</ean><price currencycode=\"SEK\"><net>10,00</net></price></item>"
        "</database>"
    )
    items = parse_xml_items(xml)
    plugin = AurdelPricesPlugin(
        field_map=AurdelPricesPlugin.default_field_map,
        config={"default_currency": "SEK"},
    )
    recs = plugin.normalize(items)
    assert len(recs) == 2
    rec = next(r for r in recs if r.sku == "DPE-101GI")
    assert rec.unit_cost == 385.57
    assert rec.vendor_item_number == "DPE-101GI"
    assert rec.supplier_item_number == "DPE-101GI"


def test_aurdel_incoming_stock_and_image_extraction():
    # <stock><delivery><date quantity="60">26-10-23</date></delivery></stock>
    # is a YY-MM-DD date with an incoming quantity; sentinels 00/99 mean "no ETA".
    # Pictures are a list, so the first picture's url should be extracted.
    xml = (
        "<database>"
        "<item id=\"2412369\">"
        "<description><short>U7 Lite</short><long>U7 Lite</long></description>"
        "<manufacturer id=\"U7-Lite\"><description>ubiquiti</description></manufacturer>"
        "<weight unit=\"kg\">0,313</weight>"
        "<countryoforigin>VN</countryoforigin>"
        "<intrastat>85176200</intrastat>"
        "<stock quantity=\"0\">"
        "<delivery><date quantity=\"60\">26-10-23</date></delivery>"
        "</stock>"
        "<price currencycode=\"SEK\"><net includedchemicaltax=\"56,56\">1042,54</net></price>"
        "<pictures><list><picture><url>https://aurdel.com/assets?code=2412369</url>"
        "<filename>2412369.png</filename></picture></list></pictures>"
        "</item>"
        "<item id=\"SENTINEL\">"
        "<description><short>No ETA</short></description>"
        "<manufacturer id=\"X\"><description>acme</description></manufacturer>"
        "<stock quantity=\"5\"><delivery><date quantity=\"0\">00-01-07</date></delivery></stock>"
        "<price currencycode=\"SEK\"><net>10,00</net></price>"
        "</item>"
        "</database>"
    )
    items = parse_xml_items(xml)
    plugin = AurdelPricesPlugin(
        field_map=AurdelPricesPlugin.default_field_map,
        config={"default_currency": "SEK"},
    )
    recs = plugin.normalize(items)
    assert len(recs) == 2

    r = next(x for x in recs if x.sku == "2412369")
    assert r.vendor_item_number == "U7-Lite"
    assert r.supplier_item_number == "2412369"
    assert r.weight == 0.313
    assert r.country_of_origin == "VN"
    assert r.intrastat_code == "85176200"
    assert r.unit_cost == 1042.54
    assert r.incoming_quantity == 60
    assert str(r.expected_delivery_date) == "2026-10-23"
    assert r.image_url == "https://aurdel.com/assets?code=2412369"
    # The webshop deeplink is built by the plugin, not the frontend.
    assert r.product_url == "https://aurdel.com/se/2412369"

    # Sentinel dates (00 / 99) must not pollute the data.
    s = next(x for x in recs if x.sku == "SENTINEL")
    assert s.expected_delivery_date is None
    assert s.incoming_quantity == 0


def test_aurdel_multiple_deliveries_captured():
    # Aurdel may advertise several upcoming deliveries per item, each as a
    # separate <date quantity="N">YY-MM-DD</date> inside <stock><delivery>.
    # Every valid delivery must be captured (sentinels skipped).
    xml = (
        "<database>"
        "<item id=\"03-TP\">"
        "<description><short>Dual drop</short></description>"
        "<manufacturer id=\"M\"><description>mfr</description></manufacturer>"
        "<stock quantity=\"0\">"
        "<delivery>"
        "<date quantity=\"1250\">26-11-03</date>"
        "<date quantity=\"1250\">27-01-16</date>"
        "<date quantity=\"0\">00-00-00</date>"
        "</delivery>"
        "</stock>"
        "<price currencycode=\"SEK\"><net>10,00</net></price>"
        "</item>"
        "</database>"
    )
    items = parse_xml_items(xml)
    plugin = AurdelPricesPlugin(
        field_map=AurdelPricesPlugin.default_field_map,
        config={"default_currency": "SEK"},
    )
    rec = plugin.normalize(items)[0]
    assert rec.incoming_quantity == 1250
    assert str(rec.expected_delivery_date) == "2026-11-03"
    assert rec.incoming_deliveries == [
        {"expected_delivery_date": "2026-11-03", "incoming_quantity": 1250},
        {"expected_delivery_date": "2027-01-16", "incoming_quantity": 1250},
    ]


def test_aurdel_plugin_registered_and_builds_default_params():
    from app.domain.inventory.vendor_catalog import IMPORTER_PLUGINS

    assert "aurdel_prices" in IMPORTER_PLUGINS
    plugin = AurdelPricesPlugin(
        config={
            "customerid": "12345",
            "companyid": "SE",
            "apikey": "secret",
            "default_currency": "SEK",
        }
    )
    # 2-letter company id gets the "AD" prefix per the spec.
    assert plugin.config["companyid"] == "ADSE"
    # The plugin declares its config fields (no user-editable URL).
    assert all("key" in f for f in plugin.config_schema)
    assert plugin.config_schema and all(f.get("key") != "url" for f in plugin.config_schema)


def test_list_vendor_products_pagination_sorting_facets(client):
    for i, (cat, brand, cost) in enumerate(
        [("Cables", "Deltaco", 10), ("Cables", "Deltaco", 5), ("Switches", "D-Link", 100)]
    ):
        client.post(
            "/api/v1/vendor-products",
            json={
                "name": f"Item {i}",
                "sku": f"SKU-{i}",
                "category": cat,
                "brand": brand,
                "unit_cost": cost,
            },
        )

    # Pagination + total header.
    page = client.get("/api/v1/vendor-products", params={"limit": 2, "offset": 0})
    assert page.status_code == 200
    assert len(page.json()) == 2
    assert int(page.headers.get("X-Total-Count", 0)) == 3

    # Sorting by unit_cost descending.
    desc = client.get(
        "/api/v1/vendor-products", params={"sort_by": "unit_cost", "sort_dir": "desc", "limit": 10}
    )
    costs = [float(v["unit_cost"]) for v in desc.json()]
    assert costs == sorted(costs, reverse=True)

    # Filtering by category.
    filtered = client.get("/api/v1/vendor-products", params={"category": "Switches"})
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["brand"] == "D-Link"

    # Fetch by id list.
    by_ids = client.get("/api/v1/vendor-products", params={"ids": "1,2", "limit": 10})
    assert len(by_ids.json()) == 2

    # Facets.
    facets = client.get("/api/v1/vendor-products/facets")
    assert "Cables" in facets.json()["categories"]
    assert "D-Link" in facets.json()["brands"]


def test_vendor_product_persists_incoming_deliveries_and_url(client):
    create = client.post(
        "/api/v1/vendor-products",
        json={
            "name": "Drop-ship widget",
            "sku": "DS-1",
            "unit_cost": 50.0,
            "currency": "SEK",
            "product_url": "https://example.com/DS-1",
            "incoming_deliveries": [
                {"expected_delivery_date": "2026-12-01", "incoming_quantity": 12},
                {"expected_delivery_date": "2027-02-15", "incoming_quantity": 8},
            ],
        },
    )
    assert create.status_code == 201
    vp_id = create.json()["id"]

    got = client.get(f"/api/v1/vendor-products/{vp_id}")
    assert got.status_code == 200
    body = got.json()
    assert body["product_url"] == "https://example.com/DS-1"
    # Every advertised delivery is stored and returned verbatim.
    assert body["incoming_deliveries"] == [
        {"expected_delivery_date": "2026-12-01", "incoming_quantity": 12},
        {"expected_delivery_date": "2027-02-15", "incoming_quantity": 8},
    ]


def test_bulk_delete_vendor_products(client):
    created = []
    for i in range(3):
        r = client.post(
            "/api/v1/vendor-products",
            json={"name": f"Thomann Köp {i}", "sku": f"T-{i}", "source_plugin": "thomann_scraper"},
        )
        assert r.status_code == 201
        created.append(r.json()["id"])
    keep = client.post(
        "/api/v1/vendor-products",
        json={"name": "Real item", "sku": "R-1", "source_plugin": "thomann_scraper"},
    ).json()["id"]

    resp = client.post(
        "/api/v1/vendor-products/bulk-delete",
        json={"source_plugin": "thomann_scraper", "name_contains": "Thomann Köp"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3

    # The filtered-out product survives.
    assert client.get(f"/api/v1/vendor-products/{keep}").status_code == 200
    for vp_id in created:
        assert client.get(f"/api/v1/vendor-products/{vp_id}").status_code == 404

    # At least one filter is required.
    bad = client.post("/api/v1/vendor-products/bulk-delete", json={})
    assert bad.status_code == 400


def test_apply_import_upserts_normalized_rows(client):
    # The apply endpoint is the core write path used by the importer UI. It
    # should upsert the supplied normalized rows and return created/updated.
    rows = [
        {
            "sku": "APPLY-1",
            "name": "Applied item A",
            "unit_cost": 19.9,
            "currency": "SEK",
            "stock_quantity": 5,
        },
        {
            "sku": "APPLY-2",
            "name": "Applied item B",
            "unit_cost": 7.5,
            "currency": "SEK",
            "incoming_deliveries": [
                {"expected_delivery_date": "2026-09-01", "incoming_quantity": 3}
            ],
        },
    ]
    resp = client.post("/api/v1/vendor-catalog/apply", json={"rows": rows})
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    # A second apply with the same SKUs should update, not duplicate.
    rows[0]["unit_cost"] = 21.0
    resp2 = client.post("/api/v1/vendor-catalog/apply", json={"rows": rows})
    assert resp2.status_code == 200
    assert resp2.json()["created"] == 0
    assert resp2.json()["updated"] == 2

    listing = client.get("/api/v1/vendor-products", params={"sku": "APPLY-1"})
    assert float(listing.json()[0]["unit_cost"]) == 21.0


def test_vendor_catalog_auto_sync_runs_due_enabled_sources(client):
    # The scheduler stage should sync only sources that are enabled, have a
    # positive auto_sync_interval, and are due (interval elapsed since the last
    # successful sync).
    from app.db.session import SessionLocal
    from app.domain.integrations.auto_sync import _run_vendor_catalog_sync
    from app.domain.inventory import vendor_catalog as vc_module
    from app.domain.inventory.vendor_catalog import (
        BaseImporterPlugin,
        VendorEquipmentRecord,
        register_importer_plugin,
    )
    from app.domain.inventory.vendor_router import (
        _read_sources,
        _write_sources,
    )

    def get_source(source_id):
        listing = client.get("/api/v1/vendor-catalog/sources").json()
        return next(s for s in listing if s["id"] == source_id)

    class FakePlugin(BaseImporterPlugin):
        id = "fake_autosync"
        label = "Fake autosync"

        def fetch(self):
            return []

        def run(self):
            return [VendorEquipmentRecord(name="Auto Widget", sku="AWS-1", unit_cost=5.0)]

    register_importer_plugin(FakePlugin)
    try:
        due = client.post(
            "/api/v1/vendor-catalog/sources",
            json={
                "name": "Due",
                "plugin_id": "fake_autosync",
                "enabled": True,
                "auto_sync_interval": 60,
            },
        ).json()
        disabled = client.post(
            "/api/v1/vendor-catalog/sources",
            json={
                "name": "Disabled",
                "plugin_id": "fake_autosync",
                "enabled": False,
                "auto_sync_interval": 60,
            },
        ).json()
        notdue = client.post(
            "/api/v1/vendor-catalog/sources",
            json={
                "name": "NotDue",
                "plugin_id": "fake_autosync",
                "enabled": True,
                "auto_sync_interval": 99999,
            },
        ).json()

        # Force a recent sync time on the "not due" source.
        db = SessionLocal()
        try:
            sources = _read_sources(db)
            for s in sources:
                if s["id"] == notdue["id"]:
                    s["last_synced_at"] = "2099-01-01T00:00:00+00:00"
            _write_sources(db, sources)
        finally:
            db.close()

        _run_vendor_catalog_sync()

        products = client.get("/api/v1/vendor-products").json()
        assert any(p["sku"] == "AWS-1" for p in products)

        due_after = get_source(due["id"])
        assert due_after["last_synced_at"] is not None
        # Disabled and not-due sources must not have synced.
        disabled_after = get_source(disabled["id"])
        assert disabled_after["last_synced_at"] is None
        notdue_after = get_source(notdue["id"])
        assert notdue_after["last_synced_at"] == "2099-01-01T00:00:00+00:00"
    finally:
        vc_module.IMPORTER_PLUGINS.pop("fake_autosync", None)


def test_vendor_catalog_auto_sync_failure_records_error(client):
    # A failing source sync must record the error on the source (for UI
    # visibility) and throttle retries by touching last_synced_at.
    from app.db.session import SessionLocal
    from app.domain.integrations.auto_sync import _run_vendor_catalog_sync
    from app.domain.inventory import vendor_catalog as vc_module
    from app.domain.inventory.vendor_catalog import (
        BaseImporterPlugin,
        register_importer_plugin,
    )
    from app.domain.inventory.vendor_router import _read_sources

    class BoomPlugin(BaseImporterPlugin):
        id = "fake_boom"
        label = "Fake boom"

        def fetch(self):
            return []

        def run(self):
            raise RuntimeError("catalog down")

    register_importer_plugin(BoomPlugin)
    try:
        client.post(
            "/api/v1/vendor-catalog/sources",
            json={
                "name": "Boom",
                "plugin_id": "fake_boom",
                "enabled": True,
                "auto_sync_interval": 60,
            },
        ).json()

        _run_vendor_catalog_sync()

        db = SessionLocal()
        try:
            sources = _read_sources(db)
            boom = next(s for s in sources if s.get("name") == "Boom")
            assert boom.get("last_auto_sync_error")
            assert boom.get("last_synced_at")  # throttled
        finally:
            db.close()
    finally:
        vc_module.IMPORTER_PLUGINS.pop("fake_boom", None)


def test_cluster_vendor_products(client):
    # Two suppliers list the same item under different reference fields.
    a = client.post(
        "/api/v1/vendor-products",
        json={"name": "U7 Lite", "sku": "U7-Lite", "unit_cost": 10, "currency": "SEK"},
    ).json()["id"]
    b = client.post(
        "/api/v1/vendor-products",
        json={
            "name": "U7 Lite (other)",
            "external_reference": "u7-lite",
            "unit_cost": 12,
            "currency": "EUR",
        },
    ).json()["id"]
    # An unrelated item stays in its own cluster.
    c = client.post(
        "/api/v1/vendor-products", json={"name": "Totally different", "sku": "XYZ"}
    ).json()["id"]

    resp = client.get("/api/v1/vendor-products/clusters")
    assert resp.status_code == 200
    clusters = resp.json()
    # Two clusters: the U7 pair and the unrelated item.
    assert len(clusters) == 2

    merged = next(cl for cl in clusters if cl["member_count"] == 2)
    assert {m["id"] for m in merged["members"]} == {a, b}
    # Matching is case-insensitive and spans sku/external_reference.
    assert "u7-lite" in merged["keys"]
    # Representative keeps the name with the most reference keys (tie -> lowest id).
    assert merged["name"] == "U7 Lite"

    singles = [cl for cl in clusters if cl["member_count"] == 1]
    assert any(cl["members"][0]["id"] == c for cl in singles)




