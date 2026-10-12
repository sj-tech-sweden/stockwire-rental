"""Tests for the Ubiquiti Store (UI.com) web scraper plugin."""
from types import SimpleNamespace

import pytest

from app.domain.inventory.scraper_ui_com import UiComScraperPlugin, _iter_json_objects
from app.domain.inventory.vendor_catalog import IMPORTER_PLUGINS


@pytest.fixture
def plugin():
    return UiComScraperPlugin(
        config={
            "start_urls": "https://eu.store.ui.com/eu/en/category/all-wifi",
            "default_currency": "EUR",
            "max_pages": 2,
        }
    )


def test_plugin_is_registered():
    assert "uicom_scraper" in IMPORTER_PLUGINS
    assert IMPORTER_PLUGINS["uicom_scraper"] is UiComScraperPlugin


def test_config_schema_has_no_editable_url():
    schema = UiComScraperPlugin.config_schema
    assert any(f["key"] == "start_urls" for f in schema)
    # The store host is fixed; users never edit a single URL field.
    assert all(f.get("key") != "url" for f in schema)


def test_normalize_maps_uicom_product():
    plugin = UiComScraperPlugin(config={"start_urls": "x"})
    raw = [{
        "name": "Access Point E7",
        "sku": "E7",
        "external_reference": "E7",
        "description": "WiFi 7 AP",
        "image_url": "https://cdn.ecomm.ui.com/x.png",
        "unit_cost": 449.0,
        "currency": "EUR",
        "category": "all-wifi",
        "product_url": "https://eu.store.ui.com/eu/en/category/all-wifi/products/e7",
        "stock_quantity": None,
        "availability": "Available",
    }]
    recs = plugin.normalize(raw)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.name == "Access Point E7"
    assert rec.sku == "E7"
    assert rec.unit_cost == 449.0
    assert rec.currency == "EUR"
    assert rec.product_url.endswith("/products/e7")
    assert rec.source_plugin == "uicom_scraper"


def test_fetch_extracts_products_from_html(plugin, monkeypatch):
    html = (
        '<html><body>'
        '<script>self.__next_f.push([1,"",{"__typename":"Product",'
        '"title":"Access Point E7","slug":"e7","displaySku":"E7",'
        '"minDisplayPrice":{"amount":44900,"currency":"EUR"},'
        '"thumbnail":{"url":"https://cdn.ecomm.ui.com/x.png"},'
        '"shortDescription":"WiFi 7 AP","organizationalCollectionSlug":"all-wifi",'
        '"status":"Available"}])</script>'
        "</body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_ui_com.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert len(records) == 1
    rec = records[0]
    assert rec.sku == "E7"
    assert rec.unit_cost == 449.0  # 44900 cents -> 449.00
    assert rec.currency == "EUR"
    assert rec.product_url == (
        "https://eu.store.ui.com/eu/en/category/all-wifi/products/e7"
    )
    assert rec.image_url == "https://cdn.ecomm.ui.com/x.png"


def test_fetch_follows_pagination(plugin, monkeypatch):
    page1 = (
        '<html><body><a href="/eu/en/category/all-wifi?page=2">next</a>'
        '<script>self.__next_f.push([1,"",{"__typename":"Product",'
        '"title":"A","slug":"a","displaySku":"A","minDisplayPrice":{"amount":1000},'
        '"thumbnail":null,"status":"Available"}])</script></body></html>'
    )
    page2 = (
        '<html><body>'
        '<script>self.__next_f.push([1,"",{"__typename":"Product",'
        '"title":"B","slug":"b","displaySku":"B","minDisplayPrice":{"amount":2000},'
        '"thumbnail":null,"status":"Available"}])</script></body></html>'
    )

    def fake_get(url, **kwargs):
        text = page2 if "page=2" in url else page1
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_ui_com.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    skus = {r.sku for r in records}
    assert skus == {"A", "B"}


def test_iter_json_objects_handles_nested():
    text = 'prefix {"a":1,"b":{"c":2}} trailer {"d":3}'
    objs = list(_iter_json_objects(text))
    all_keys = set().union(*[o.keys() for o in objs])
    # Both top-level objects (and the nested one) are recovered.
    assert "a" in all_keys and "d" in all_keys
