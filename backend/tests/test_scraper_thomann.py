"""Tests for the Thomann web scraper plugin."""
from types import SimpleNamespace

import pytest

from app.domain.inventory.scraper_thomann import ThomannScraperPlugin
from app.domain.inventory.vendor_catalog import IMPORTER_PLUGINS


@pytest.fixture
def plugin():
    return ThomannScraperPlugin(
        config={
            "start_urls": "https://www.thomann.de/se/some_listing.html",
            "default_currency": "SEK",
            "max_pages": 2,
            "max_products": 50,
            "request_delay": 0,
        }
    )


def test_plugin_is_registered():
    assert "thomann_scraper" in IMPORTER_PLUGINS
    assert IMPORTER_PLUGINS["thomann_scraper"] is ThomannScraperPlugin


def test_config_schema_defaults():
    schema = ThomannScraperPlugin.config_schema
    assert any(f["key"] == "start_urls" for f in schema)
    assert any(f["key"] == "default_currency" and f.get("default") == "SEK" for f in schema)


def test_normalize_maps_thomann_product():
    plugin = ThomannScraperPlugin(config={"start_urls": "x"})
    raw = [{
        "name": "Yamaha HS8",
        "sku": "HS8",
        "brand": "Yamaha",
        "category": "Monitors",
        "description": "Studio monitor",
        "image_url": "https://thomann.de/x.jpg",
        "unit_cost": "1890.00",
        "currency": "SEK",
        "product_url": "https://www.thomann.de/se/yamaha_hs8.html",
        "availability": "in stock",
    }]
    recs = plugin.normalize(raw)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.name == "Yamaha HS8"
    assert rec.sku == "HS8"
    assert rec.unit_cost == 1890.0
    assert rec.currency == "SEK"
    assert rec.product_url.endswith("/yamaha_hs8.html")
    assert rec.source_plugin == "thomann_scraper"


def test_fetch_extracts_product_from_jsonld(plugin, monkeypatch):
    html = (
        '<html><head>'
        '<script type="application/ld+json">{"@context":"https://schema.org",'
        '"@type":"Product","name":"Yamaha HS8","sku":"HS8",'
        '"brand":{"@type":"Brand","name":"Yamaha"},'
        '"image":"https://thomann.de/x.jpg","description":"Studio monitor",'
        '"offers":{"@type":"Offer","price":"1890.00","priceCurrency":"SEK",'
        '"availability":"https://schema.org/InStock",'
        '"url":"https://www.thomann.de/se/yamaha_hs8.html"}}</script>'
        "</head><body></body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert len(records) == 1
    rec = records[0]
    assert rec.sku == "HS8"
    assert rec.unit_cost == 1890.0
    assert rec.currency == "SEK"
    assert rec.brand == "Yamaha"
    assert rec.availability == "in stock"


def test_fetch_follows_listing_and_product_links(plugin, monkeypatch):
    listing = (
        '<html><body>'
        '<a href="https://www.thomann.de/se/yamaha_hs8_p_12345.html">hs8</a>'
        '<a href="https://www.thomann.de/se/listing?pg=2">next</a>'
        "</body></html>"
    )
    product_html = (
        '<html><head>'
        '<script type="application/ld+json">{"@context":"https://schema.org",'
        '"@type":"Product","name":"Yamaha HS8","sku":"HS8",'
        '"offers":{"@type":"Offer","price":"1890.00","priceCurrency":"SEK"}}'
        "</script></head><body></body></html>"
    )
    listing2 = '<html><body></body></html>'

    def fake_get(url, **kwargs):
        if "yamaha_hs8" in url:
            text = product_html
        elif "pg=2" in url:
            text = listing2
        else:
            text = listing
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    skus = {r.sku for r in records}
    assert skus == {"HS8"}


def test_fetch_uses_meta_fallback(monkeypatch):
    plugin = ThomannScraperPlugin(config={"start_urls": "https://www.thomann.de/se/foo.html", "request_delay": 0})
    html = (
        '<html><head>'
        '<meta property="og:title" content="Roland AE-01">'
        '<meta property="product:price:amount" content="1290.00">'
        '<meta property="product:price:currency" content="SEK">'
        '<meta property="og:url" content="https://www.thomann.de/se/roland_ae_01_p_631362.html">'
        "</head><body></body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert len(records) == 1
    rec = records[0]
    assert rec.name == "Roland AE-01"
    assert rec.unit_cost == 1290.0
    assert rec.currency == "SEK"
    assert rec.sku == "631362"


def test_fetch_skips_listing_pages(monkeypatch):
    # A category/listing page has a title and links to products but no price and
    # no product URL pattern of its own — it must be crawled, not imported.
    listing = (
        '<html><head><meta property="og:title" content="Thomann Köp DJ hos Thomann">'
        "</head><body>"
        '<a href="https://www.thomann.de/se/yamaha_hs8_p_12345.html">hs8</a>'
        '<a href="https://www.thomann.de/se/foo_p_999.html">foo</a>'
        "</body></html>"
    )
    product_html = (
        '<html><head>'
        '<script type="application/ld+json">{"@context":"https://schema.org",'
        '"@type":"Product","name":"Yamaha HS8","sku":"HS8",'
        '"offers":{"@type":"Offer","price":"1890.00","priceCurrency":"SEK"}}'
        "</script></head><body></body></html>"
    )

    def fake_get(url, **kwargs):
        text = product_html if "_p_" in url else listing
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)
    plugin = ThomannScraperPlugin(
        config={"start_urls": "https://www.thomann.de/se/dj.html", "default_currency": "SEK", "request_delay": 0}
    )
    records = plugin.normalize(plugin.fetch())
    # The listing itself is not imported (no record named after the category).
    assert not any(r.name == "Thomann Köp DJ hos Thomann" for r in records)
    # The followed product links are imported.
    assert {r.sku for r in records} == {"HS8"}


def test_fetch_extracts_product_from_gtm_blob(monkeypatch):
    # The live thomann.se front-end has no JSON-LD and no price meta; product
    # data lives in the GTM 'prod.fx.gtm' ecommerce blob. Product URLs end in
    # .htm and carry no _p_ segment.
    plugin = ThomannScraperPlugin(
        config={"start_urls": "https://www.thomann.se/flyht_pro_wp_safe_box_5_ip65.htm", "request_delay": 0}
    )
    html = (
        '<html><head>'
        '<meta property="og:image" content="https://www.thomann.de/thumb/opengraph/pics/prod/330507.jpg">'
        '<meta property="og:url" content="https://www.thomann.se/flyht_pro_wp_safe_box_5_ip65.htm">'
        '<meta property="og:description" content="IP65 transport case">'
        "<script type=\"text/javascript\">tho.bootstrapModule('prod.fx.gtm', "
        '[{"ecommerce":{"items":[{"item_id":"330507","item_name":"WP Safe Box 5 IP65","currency":"SEK","item_brand":"Flyht Pro","item_category":"CA","price":789}]}}], []);</script>'
        "</head><body>"
        '<nav><ol>'
        '<li itemprop="itemListElement"><a><span itemprop="name">Alla kategorier</span></a></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Case, rack &amp; väskor</span></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Cases</span></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Tillbehörscase</span></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Flyht Pro</span></li>'
        "</ol></nav>"
        '<span class="fx-availability fx-availability--in-stock">i lager och kan levereras omgående.</span>'
        "</body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert len(records) == 1
    rec = records[0]
    assert rec.sku == "330507"
    assert rec.unit_cost == 789.0
    assert rec.currency == "SEK"
    assert rec.brand == "Flyht Pro"
    assert rec.name == "WP Safe Box 5 IP65"
    assert rec.image_url.endswith("330507.jpg")
    # Human-readable breadcrumb category, not the "CA" code.
    assert rec.category == "Case, rack & väskor > Cases > Tillbehörscase"
    assert rec.availability == "in stock"


def test_fetch_extracts_backorder_availability(monkeypatch):
    plugin = ThomannScraperPlugin(
        config={"start_urls": "https://www.thomann.se/presonus_dm_7.htm", "request_delay": 0}
    )
    html = (
        '<html><head>'
        "<script type=\"text/javascript\">tho.bootstrapModule('prod.fx.gtm', "
        '[{"ecommerce":{"items":[{"item_id":"564038","item_name":"DM7","currency":"SEK","item_brand":"PreSonus","item_category":"ST","price":21890}]}}], []);</script>'
        "</head><body>"
        '<li itemprop="itemListElement"><span itemprop="name">Alla kategorier</span></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Mikrofoner</span></li>'
        '<li itemprop="itemListElement"><span itemprop="name">Presonus</span></li>'
        '<span class="fx-availability fx-availability--on-date">I lager om 6-8 veckor</span>'
        "</body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert len(records) == 1
    rec = records[0]
    assert rec.category == "Mikrofoner"
    assert rec.availability == "backorder"


def test_fetch_follows_htm_product_links(monkeypatch):
    # A .html category listing links to .htm product pages (with a ?type=category
    # query). The crawler must follow those and skip the listing itself.
    plugin = ThomannScraperPlugin(
        config={
            "start_urls": "https://www.thomann.se/cases_racks_vaeskor.html",
            "default_currency": "SEK",
            "request_delay": 0,
        }
    )
    listing = (
        '<html><body>'
        '<a href="https://www.thomann.se/flyht_pro_wp_safe_box_5_ip65.htm?type=category">box</a>'
        '<a href="https://www.thomann.se/cases_racks_vaeskor.html">self category</a>'
        "</body></html>"
    )
    product_html = (
        '<html><head>'
        "<script type=\"text/javascript\">tho.bootstrapModule('prod.fx.gtm', "
        '[{"ecommerce":{"items":[{"item_id":"330507","item_name":"WP Safe Box 5 IP65",'
        '"currency":"SEK","price":789}]}}], []);</script>'
        "</head><body></body></html>"
    )

    def fake_get(url, **kwargs):
        text = product_html if "wp_safe_box" in url else listing
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert {r.sku for r in records} == {"330507"}


def test_fetch_traverses_subcategories(monkeypatch):
    # A category listing links to a subcategory (.html) page which in turn lists
    # its own products. With follow_subcategories the crawler must descend and
    # collect products from both levels.
    plugin = ThomannScraperPlugin(
        config={
            "start_urls": "https://www.thomann.se/cases_racks_vaeskor.html",
            "default_currency": "SEK",
            "max_pages": 10,
            "request_delay": 0,
        }
    )
    top_listing = (
        '<html><body>'
        '<a href="https://www.thomann.se/flyht_pro_wp_safe_box_5_ip65.htm?type=category">box</a>'
        '<a href="https://www.thomann.se/flight_cases.html">Flight cases</a>'
        '<a href="https://www.thomann.se/the_basket.html">cart (skip)</a>'
        "</body></html>"
    )
    sub_listing = (
        '<html><body>'
        '<a href="https://www.thomann.se/peli_0500_foam_black.htm?type=category">pelicase</a>'
        "</body></html>"
    )
    product_html = (
        '<html><head>'
        "<script type=\"text/javascript\">tho.bootstrapModule('prod.fx.gtm', "
        '[{"ecommerce":{"items":[{"item_id":"PLACEHOLDER","item_name":"X","currency":"SEK","price":1}]}}], []);</script>'
        "</head><body></body></html>"
    )

    def fake_get(url, **kwargs):
        if "flight_cases.html" in url:
            text = sub_listing
        elif "wp_safe_box" in url:
            text = product_html.replace("PLACEHOLDER", "330507").replace('"X"', '"WP Safe Box"')
        elif "pelicase" in url or "pelicase" in url or "peli_0500" in url:
            text = product_html.replace("PLACEHOLDER", "987654").replace('"X"', '"Peli 0500"')
        else:
            text = top_listing
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    assert {r.sku for r in records} == {"330507", "987654"}


def test_subcategory_links_excludes_sibling_nav():
    # The global header / mega-menu links to *sibling* top-level categories the
    # operator did not select. _subcategory_links must scope to the on-page
    # subcategory grid (fx-category-grid anchors) and ignore those siblings.
    html = (
        '<html><body>'
        '<a class="fx-link fx-category-grid__item fx-grid__col" href="/monitorer.html">Monitors</a>'
        '<a class="fx-link fx-category-grid__item" href="/preamps.html">Preamps</a>'
        # Sibling top-level categories live in hidden mega-menu markup.
        '<div class="hidden"><a href="/gitarrer_basar.html">Guitars</a>'
        '<a href="/trummor_slagverk.html">Drums</a></div>'
        # Non-category wrapper pages.
        '<a class="fx-category-grid__item" href="/special_cyber-deals.html">Deals</a>'
        '<a class="fx-category-grid__item" href="/the_basket.html">Cart</a>'
        "</body></html>"
    )
    links = ThomannScraperPlugin._subcategory_links(
        html, "https://www.thomann.se/studio_inspelning.html"
    )
    assert links == [
        "https://www.thomann.se/monitorer.html",
        "https://www.thomann.se/preamps.html",
    ]


def test_fetch_extracts_listing_cards(monkeypatch):
    # A category listing renders every product as an inline fx-product-box card,
    # so the crawler should extract them all from a SINGLE listing request
    # (no per-product page fetches) — this is what beats Cloudflare throttling.
    plugin = ThomannScraperPlugin(
        config={
            "start_urls": "https://www.thomann.de/se/mikrofoner.html",
            "default_currency": "SEK",
            "request_delay": 0,
            "follow_subcategories": False,
        }
    )
    listing = (
        '<html><body>'
        '<a href="shure_sm58.htm" class="js-product fx-product-box fx-grid__col">'
        '<img alt="Shure SM58 LC" '
        'data-srcset="https://thumbs.static-thomann.de/thumb/thumb248x248/pics/prod/105767.webp">'
        '<span class="description__manufacturer">Shure</span>'
        '<div class="price"><div class="fx-price-group"><span>1 299 kr</span></div></div>'
        "</a>"
        '<a href="rode_nt1.htm" class="js-product fx-product-box fx-grid__col">'
        '<img alt="Rode NT1" '
        'data-srcset="https://thumbs.static-thomann.de/thumb/thumb248x248/pics/prod/204612.webp">'
        '<span class="description__manufacturer">Rode</span>'
        '<div class="price"><div class="fx-price-group"><span>2 490 kr</span></div></div>'
        "</a>"
        "</body></html>"
    )
    seen = []

    def fake_get(url, **kwargs):
        seen.append(url)
        return SimpleNamespace(text=listing, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    records = plugin.normalize(plugin.fetch())
    # Only the listing URL is fetched — no per-product requests.
    assert seen == ["https://www.thomann.de/se/mikrofoner.html"]
    by = {r.sku: r for r in records}
    assert set(by) == {"105767", "204612"}
    assert by["105767"].name == "Shure SM58 LC"
    assert by["105767"].brand == "Shure"
    assert by["105767"].unit_cost == 1299.0
    assert by["105767"].currency == "SEK"
    assert by["105767"].product_url.endswith("shure_sm58.htm")


def test_discover_categories_filters_products(monkeypatch):
    html = (
        '<html><body>'
        '<a href="/se/dj.html">DJ</a>'
        '<a href="/se/recording.html">Recording</a>'
        '<a href="/se/yamaha_hs8_p_12345.html">product</a>'
        '<a href="/se/the_basket.html">cart</a>'
        '<a href="https://other.site/x.html">external</a>'
        "</body></html>"
    )

    def fake_get(url, **kwargs):
        return SimpleNamespace(text=html, raise_for_status=lambda: None)

    monkeypatch.setattr("app.domain.inventory.scraper_thomann.httpx.get", fake_get)

    cats = ThomannScraperPlugin.discover_categories("https://www.thomann.de/se/")
    urls = {c["url"] for c in cats}
    assert "https://www.thomann.de/se/dj.html" in urls
    assert "https://www.thomann.de/se/recording.html" in urls
    # product / cart / external links are excluded
    assert not any("_p_" in u for u in urls)
    assert not any("the_basket" in u for u in urls)
    assert all("thomann.de" in u for u in urls)

