"""Web scraper plugin for Thomann (https://www.thomann.de/ and regional mirrors).

Thomann's front-end has changed over time, so this plugin supports two markup
shapes for product data:

* The **live** ``.se`` / ``.de`` front-end embeds product data in a
  ``tho.bootstrapModule('prod.fx.gtm', [{ ecommerce: { items: [...] } }])``
  call (Google Tag Manager ``view_item`` payload). There is **no** JSON-LD and
  **no** price meta tag on these pages.
* Older / API-style pages still embed JSON-LD (``Product`` + an
  ``AggregateOffer``) plus Open Graph / ``product:`` meta tags as a fallback.

Product URLs on the live site are ``<slug>.htm`` (note: ``.htm``, not
``.html``) and contain no ``_p_<id>`` segment, so link discovery and
product-page detection must match both the old ``_p_`` convention and the new
``.htm`` convention.

This plugin recovers the product objects from that markup and maps them to
:class:`VendorEquipmentRecord`.

It handles two kinds of start URL:

* A single **product** page -> one record.
* A **listing** (category / search / manufacturer) page -> the plugin follows the
  pagination links and scrapes every linked product page it finds, up to
  ``max_pages`` listing pages and ``max_products`` products per run.

Because the data lives in HTML rather than a real API, this plugin is inherently
more fragile than the API/CSV importers: a Thomann front-end redesign can move or
rename the embedded fields. Treat the extracted fields as best-effort and review
the imported products before approving them.

ToS note: scraping Thomann may be disallowed by its terms of service. Only enable
this for sources you are permitted to crawl, and respect robots.txt / rate limits.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import ClassVar
from urllib.parse import urljoin, urlparse

import httpx

from app.domain.inventory.vendor_catalog import (
    IMPORTER_PLUGINS,
    BaseImporterPlugin,
    VendorEquipmentRecord,
    _coerce_float,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,sv;q=0.8",
}


def _availability(value: str | None) -> str | None:
    """Normalise a schema.org availability IRI to a short label."""
    if not value:
        return None
    last = str(value).rstrip("/").split("/")[-1]
    mapping = {
        "Instock": "in stock",
        "OutOfStock": "out of stock",
        "PreOrder": "preorder",
        "BackOrder": "backorder",
        "PreSale": "presale",
        "LimitedAvailability": "limited",
        "SoldOut": "sold out",
        "Discontinued": "discontinued",
        "InStock": "in stock",
    }
    return mapping.get(last, last)


def _walk(node, out: list) -> None:
    if isinstance(node, dict):
        out.append(node)
        for v in node.values():
            _walk(v, out)
    elif isinstance(node, list):
        for x in node:
            _walk(x, out)


def _by_type(nodes: list, type_name: str):
    flat: list[dict] = []
    for n in nodes:
        _walk(n, flat)
    for obj in flat:
        t = obj.get("@type")
        if isinstance(t, str):
            types = [t]
        elif isinstance(t, list):
            types = list(t)
        else:
            types = []
        if type_name in {str(x).lower() for x in types}:
            return obj
    return None


def _as_str(value):
    if isinstance(value, list):
        value = value[0] if value else None
    return value if isinstance(value, str) else (str(value) if value is not None else None)


class ThomannScraperPlugin(BaseImporterPlugin):
    """Scrape products from a Thomann product or listing page."""

    id = "thomann_scraper"
    label = "Thomann (.de/.se) scraper"
    source_type = "scraper"
    config_schema: ClassVar[list] = [
        {
            "key": "store",
            "label": "Thomann store",
            "type": "select",
            "default": "https://www.thomann.se",
            "options": [
                {"label": "Sweden (.se) — SEK", "value": "https://www.thomann.se"},
                {"label": "Germany / Swedish locale (.de/se) — EUR", "value": "https://www.thomann.de/se/"},
                {"label": "Germany (.de) — EUR", "value": "https://www.thomann.de/"},
                {"label": "United Kingdom (.co.uk) — GBP", "value": "https://www.thomann.co.uk/"},
                {"label": "United States (.com) — USD", "value": "https://www.thomann.com/"},
            ],
            "help": (
                "Regional store to scrape. Set this before browsing categories so "
                "the discovered links and prices use the right store/currency."
            ),
        },
        {
            "key": "start_urls",
            "label": "Thomann URLs",
            "type": "textarea",
            "required": True,
            "help": (
                "One product or listing (category/search) URL per line, e.g. "
                "https://www.thomann.se/some_product.html"
            ),
        },
        {
            "key": "default_currency",
            "label": "Default currency",
            "type": "text",
            "default": "SEK",
            "help": "Used when a product has no currency of its own.",
        },
        {
            "key": "max_pages",
            "label": "Max listing pages",
            "type": "number",
            "default": 500,
            "help": (
                "How many listing/subcategory pages to crawl per start URL. "
                "Thomann shows ~100 products per listing page, so a large "
                "category with many subcategories needs a high value to capture "
                "everything."
            ),
        },
        {
            "key": "max_products",
            "label": "Max products",
            "type": "number",
            "default": 20000,
            "help": (
                "Stop after scraping this many products in total across all start "
                "URLs. Set high (or raise further) to import a full catalog; the "
                "crawl stops early otherwise and later categories are skipped."
            ),
        },
        {
            "key": "follow_subcategories",
            "label": "Follow subcategories",
            "type": "checkbox",
            "default": True,
            "help": (
                "Thomann paginates via JavaScript, so a category page only lists "
                "its own products. Enable this to also crawl linked subcategory "
                "(.html) pages and collect their products too."
            ),
        },
        {
            "key": "request_delay",
            "label": "Delay between requests (s)",
            "type": "number",
            "default": 1.5,
            "help": (
                "Seconds to wait between HTTP requests. Thomann rate-limits "
                "(HTTP 429); a small delay avoids being throttled mid-crawl."
            ),
        },
        {
            "key": "max_retries",
            "label": "Retries on 429",
            "type": "number",
            "default": 3,
            "help": "How many times to back off and retry when rate-limited.",
        },
    ]
    default_field_map: ClassVar[dict] = {}

    def __init__(self, field_map: dict | None = None, config: dict | None = None):
        super().__init__(field_map, config)
        raw_urls = str(self.config.get("start_urls") or "")
        self.start_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
        self.max_pages = int(self.config.get("max_pages") or 20)
        self.max_products = int(self.config.get("max_products") or 200)
        self.follow_subcategories = bool(self.config.get("follow_subcategories", True))
        rd = self.config.get("request_delay")
        self.request_delay = float(rd) if rd is not None else 1.5
        mr = self.config.get("max_retries")
        self.max_retries = int(mr) if mr is not None else 3
        self.default_currency = self.config.get("default_currency") or "SEK"

    # -- fetching -----------------------------------------------------------

    def _get(self, url: str) -> str | None:
        # Thomann rate-limits aggressively (HTTP 429), so space requests out and
        # back off + retry when throttled. Without this the crawler gets a handful
        # of pages then silently drops the rest.
        delay = getattr(self, "request_delay", 0) or 0
        if delay:
            time.sleep(delay)
        max_retries = getattr(self, "max_retries", 3)
        for attempt in range(max_retries + 1):
            try:
                resp = httpx.get(url, headers=_HEADERS, timeout=60, follow_redirects=True)
            except Exception as exc:  # noqa: BLE001 - scraping is best-effort
                logger.warning("Thomann scrape failed for %s: %s", url, exc)
                return None
            status = getattr(resp, "status_code", 200)
            headers = getattr(resp, "headers", {}) or {}
            if status == 429 and attempt < max_retries:
                retry_after = headers.get("retry-after") if hasattr(headers, "get") else None
                try:
                    wait = float(retry_after) if retry_after else 0
                except (TypeError, ValueError):
                    wait = 0
                if wait <= 0:
                    wait = 2 ** attempt
                logger.warning(
                    "Thomann rate-limited (429) for %s, backing off %.1fs (attempt %d/%d)",
                    url,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                continue
            try:
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001 - scraping is best-effort
                logger.warning("Thomann scrape failed for %s: %s", url, exc)
                return None
            return resp.text
        logger.warning("Thomann scrape gave up on %s after %d retries", url, max_retries)
        return None

    def fetch(self) -> list[dict]:
        products: dict[str, dict] = {}
        for base in self.start_urls:
            visited_listing: set[str] = set()
            queue = [base]
            listing_pages = 0
            while queue and listing_pages < self.max_pages and len(products) < self.max_products:
                url = queue.pop(0)
                if url in visited_listing:
                    continue
                visited_listing.add(url)
                listing_pages += 1
                html = self._get(url)
                if html is None:
                    continue
                prod = self._extract_product(html, url)
                if prod and prod.get("name"):
                    key = prod.get("sku") or prod.get("name")
                    products[key] = prod
                    continue
                # Listing page: scrape every product card in a single request
                # (name/brand/price/sku/image) instead of fetching each product
                # page — this avoids Thomann's per-request Cloudflare throttling.
                crumbs = [
                    c
                    for c in self._breadcrumb_names(html)
                    if c.strip().lower() not in ("alla kategorier", "all categories")
                ]
                if len(crumbs) >= 2:
                    category = " > ".join(crumbs[:-1])
                elif len(crumbs) == 1:
                    category = crumbs[0]
                else:
                    # Fallback: derive a category from the listing URL slug.
                    slug = urlparse(url).path.rstrip("/").split("/")[-1]
                    slug = re.sub(r"\.html?$", "", slug)
                    category = slug.replace("_", " ").title() if slug else None
                cards = self._products_from_listing(html, url)
                if cards:
                    for rec in cards:
                        if category:
                            rec["category"] = category
                        key = rec.get("sku") or rec.get("name")
                        products[key] = rec
                else:
                    # Legacy fallback: queue individual product links (each will
                    # be fetched as its own page).
                    for link in self._product_links(html, url):
                        if link not in products and link not in visited_listing:
                            queue.append(link)
                # Thomann paginates via JS, so a category page only shows its own
                # products. Crawl linked subcategory (.html) pages to collect the
                # rest of the tree.
                for nxt in self._next_page_urls(html, url):
                    if nxt not in visited_listing:
                        queue.append(nxt)
                if self.follow_subcategories:
                    for link in self._subcategory_links(html, url):
                        if link not in visited_listing:
                            queue.append(link)
        return list(products.values())

    # -- parsing ------------------------------------------------------------

    @staticmethod
    def _jsonld_blocks(html: str) -> list:
        blocks = re.findall(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        nodes: list = []
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            try:
                data = json.loads(b)
            except (ValueError, json.JSONDecodeError):
                continue
            nodes.append(data)
        return nodes

    @staticmethod
    def _meta(html: str, prop: str) -> str | None:
        patterns = [
            rf'<meta[^>]+(?:property|name)="{re.escape(prop)}"[^>]+content="([^"]*)"',
            rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{re.escape(prop)}"',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _title(html: str) -> str | None:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    @staticmethod
    def _is_product_page(html: str, url: str) -> bool:
        """Heuristic: is this HTML a product detail page (vs a listing/category)?

        We treat a page as a product page when it carries JSON-LD ``Product``
        data, its own URL looks like a product URL (``.htm`` or the legacy
        ``_p_`` convention), it embeds a GTM ``prod.fx.gtm`` ecommerce item,
        or it exposes a product price in meta. Anything else (a
        category/listing page with a title but no product signal) is left for
        ``fetch`` to crawl for product links.
        """
        if any(_by_type(n, "product") for n in ThomannScraperPlugin._jsonld_blocks(html)):
            return True
        u = (url or "").lower().split("?")[0]
        if u.endswith(".htm") or "_p_" in u or "_p-" in u or "/p/" in u:
            return True
        if ThomannScraperPlugin._gtm_items(html):
            return True
        if ThomannScraperPlugin._meta(html, "product:price:amount") or ThomannScraperPlugin._meta(
            html, "og:price:amount"
        ):
            return True
        return False

    # -- live front-end: GTM ecommerce blob --------------------------------

    _GTM_RE = re.compile(
        r"bootstrapModule\(\s*['\"]prod\.fx\.gtm['\"]\s*,\s*", re.DOTALL
    )

    @classmethod
    def _gtm_items(cls, html: str) -> list[dict]:
        """Extract ecommerce item dicts from Thomann's GTM bootstrap script.

        The live ``.se`` / ``.de`` front-end embeds product data in a
        ``tho.bootstrapModule('prod.fx.gtm', [{ ecommerce: { items: [...] } }])``
        call rather than JSON-LD / price meta tags. The call's first argument is
        a JSON array whose trailing ``(, [])`` can confuse a naive regex, so we
        scan balanced brackets to slice out the JSON value.
        """
        out: list[dict] = []
        for m in cls._GTM_RE.finditer(html or ""):
            i = m.end()
            while i < len(html) and html[i] in " \t\r\n":
                i += 1
            if i >= len(html) or html[i] not in "[{":
                continue
            depth = 0
            j = i
            while j < len(html):
                c = html[j]
                if c in "[{":
                    depth += 1
                elif c in "]}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            blob = html[i : j + 1]
            try:
                data = json.loads(blob)
            except (ValueError, json.JSONDecodeError):
                continue
            flat: list = []
            _walk(data, flat)
            for obj in flat:
                if isinstance(obj, dict) and "ecommerce" in obj:
                    ec = obj.get("ecommerce")
                    items = ec.get("items") if isinstance(ec, dict) else None
                    if isinstance(items, list):
                        out.extend(x for x in items if isinstance(x, dict))
        return out

    @classmethod
    def _breadcrumb_names(cls, html: str) -> list[str]:
        """Extract breadcrumb category names from the live microdata markup.

        The live site exposes breadcrumbs as ``<li itemprop="itemListElement">``
        blocks with an ``itemprop="name"`` span — no JSON-LD ``BreadcrumbList``.
        Names are HTML-unescaped (e.g. ``&amp;`` -> ``&``).
        """
        from html import unescape

        names: list[str] = []
        for block in re.findall(
            r'<li[^>]*itemprop="itemListElement"[^>]*>(.*?)</li>',
            html or "",
            re.DOTALL | re.IGNORECASE,
        ):
            m = re.search(r'itemprop="name"[^>]*>([^<]+)<', block, re.IGNORECASE)
            if m:
                nm = unescape(m.group(1)).strip()
                if nm:
                    names.append(nm)
        return names

    @classmethod
    def _availability_from_html(cls, html: str) -> str | None:
        """Normalise the live ``fx-availability`` span text to a short label.

        Swedish examples seen on thomann.se: ``"i lager och kan levereras
        omgående."`` (in stock) and ``"I lager om 6-8 veckor"`` (backorder).
        """
        m = re.search(r'class="fx-availability[^"]*">([^<]+)<', html or "", re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1).strip()
        low = raw.lower()
        if "veckor" in low or "on-date" in m.group(0).lower():
            return "backorder"
        if "i lager" in low or "in stock" in low:
            return "in stock"
        if "sluts" in low or "out of stock" in low or "sold out" in low:
            return "out of stock"
        if "restnot" in low or "preorder" in low or "pre-order" in low:
            return "preorder"
        return None

    @classmethod
    def _product_from_gtm(cls, item: dict, html: str, url: str) -> dict | None:
        name = _as_str(item.get("item_name")) or _as_str(item.get("name"))
        if not name:
            return None
        sku = _as_str(item.get("item_id")) or _as_str(item.get("sku"))
        if not sku:
            m = re.search(r"_p[_-](\d+)", url)
            sku = m.group(1) if m else None
        price = _coerce_float(item.get("price"))
        currency = _as_str(item.get("currency"))
        brand = _as_str(item.get("item_brand")) or _as_str(item.get("brand"))
        # Prefer the human-readable breadcrumb path over the GTM ``item_category``
        # code (e.g. "CA"/"ST"). Drop the root ("Alla kategorier") and the final
        # brand/product crumb.
        crumbs = [
            c for c in cls._breadcrumb_names(html) if c.strip().lower() != "alla kategorier"
        ]
        if len(crumbs) >= 2:
            category = " > ".join(crumbs[:-1])
        elif crumbs:
            category = crumbs[0]
        else:
            category = _as_str(item.get("item_category"))
        # The GTM blob carries no image/description/availability, so enrich them
        # from OG/meta and the structured ``fx-availability`` span.
        product_url = cls._meta(html, "og:url") or url
        return {
            "name": name,
            "sku": sku,
            "brand": brand or "Thomann",
            "category": category,
            "description": cls._meta(html, "description") or cls._meta(html, "og:description"),
            "image_url": cls._meta(html, "og:image"),
            "unit_cost": price,
            "currency": currency,
            "product_url": product_url,
            "availability": cls._availability_from_html(html),
        }

    def _extract_product(self, html: str, url: str) -> dict | None:
        nodes = self._jsonld_blocks(html)
        product = _by_type(nodes, "product")
        breadcrumb = _by_type(nodes, "breadcrumblist")

        if product:
            rec = self._product_from_jsonld(product, breadcrumb, url)
            if rec and rec.get("name"):
                return rec

        # Live front-end: product data lives in the GTM 'prod.fx.gtm' blob.
        for gtm in self._gtm_items(html):
            rec = self._product_from_gtm(gtm, html, url)
            if rec and rec.get("name"):
                return rec

        # A listing/category page must be crawled for product links, not imported
        # as a (priceless) "product". Only proceed when this looks like a product
        # detail page. Price may still be absent — we import what we can and let
        # the operator fix the cost later.
        if not self._is_product_page(html, url):
            return None

        # Fallback to Open Graph / product: meta tags (legacy pages).
        name = self._meta(html, "og:title") or self._title(html)
        if not name:
            return None
        price = self._meta(html, "product:price:amount") or self._meta(html, "og:price:amount")
        currency = self._meta(html, "product:price:currency")
        product_url = self._meta(html, "og:url") or url
        sku = self._meta(html, "product:retailer_item_id")
        if not sku:
            m = re.search(r"_p[_-](\d+)", product_url)
            sku = m.group(1) if m else None
        return {
            "name": name,
            "sku": sku,
            "brand": self._meta(html, "og:site_name") or "Thomann",
            "description": self._meta(html, "description") or self._meta(html, "og:description"),
            "image_url": self._meta(html, "og:image"),
            "unit_cost": _coerce_float(price),
            "currency": currency or self.default_currency,
            "product_url": product_url,
            "availability": None,
        }

    def _product_from_jsonld(self, obj: dict, breadcrumb: dict | None, url: str) -> dict | None:
        name = _as_str(obj.get("name"))
        if not name:
            return None

        brand = obj.get("brand")
        if isinstance(brand, dict):
            brand = _as_str(brand.get("name"))
        else:
            brand = _as_str(brand)

        image = obj.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        image = _as_str(image)

        offers = obj.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else None

        price = None
        currency = self.default_currency
        availability = None
        offer_url = None
        if isinstance(offers, dict):
            price = _coerce_float(offers.get("price"))
            currency = _as_str(offers.get("priceCurrency")) or self.default_currency
            availability = _availability(_as_str(offers.get("availability")))
            offer_url = _as_str(offers.get("url"))

        sku = _as_str(obj.get("sku")) or _as_str(obj.get("gtin13")) or _as_str(obj.get("mpn"))
        if not sku:
            m = re.search(r"_p[_-](\d+)", url)
            sku = m.group(1) if m else None

        barcode = (
            _as_str(obj.get("gtin13"))
            or _as_str(obj.get("gtin14"))
            or _as_str(obj.get("gtin8"))
            or _as_str(obj.get("gtin"))
            or _as_str(obj.get("ean"))
        )

        category = _as_str(obj.get("category"))
        if not category and breadcrumb:
            category = self._breadcrumb_category(breadcrumb)

        product_url = offer_url or _as_str(obj.get("url")) or url

        return {
            "name": name,
            "sku": sku,
            "barcode": barcode,
            "brand": brand,
            "category": category,
            "description": _as_str(obj.get("description")),
            "image_url": image,
            "unit_cost": price,
            "currency": currency,
            "product_url": product_url,
            "availability": availability,
        }

    @staticmethod
    def _breadcrumb_category(breadcrumb: dict) -> str | None:
        items = breadcrumb.get("itemListElement")
        if not isinstance(items, list) or not items:
            return None
        last = items[-1]
        if isinstance(last, dict):
            item = last.get("item") if isinstance(last.get("item"), dict) else last
            return _as_str(item.get("name"))
        return None

    @staticmethod
    def _product_links(html: str, base: str) -> list[str]:
        out: list[str] = []
        host = urlparse(base).netloc
        for href in re.findall(r'href="([^"]+)"', html):
            full = urljoin(base, href)
            parsed = urlparse(full)
            if host and parsed.netloc and parsed.netloc != host:
                continue
            low = full.lower()
            path = parsed.path.lower()
            # Product pages are ``<slug>.htm`` on the live site (no ``_p_``) and
            # ``<slug>_p_<id>.html`` on the legacy site. Category/listing pages
            # end in ``.html`` and must NOT be treated as products.
            is_product = (
                path.endswith(".htm")
                or "_p_" in low
                or "_p-" in low
                or "/p/" in low
            )
            if not is_product:
                continue
            out.append(full)
        # de-dupe, keep order
        seen: set[str] = set()
        unique = []
        for u in out:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique

    # Segments that look like ``.html`` links but are not real categories.
    _SKIP_SEGMENTS = (
        "the_basket", "basket", "wish", "account", "login", "cart", "search",
        "newsletter", "service", "help", "agb", "imprint", "privacy", "sitemap",
        "manufacturer", "brand", "cms", "jobs", "press", "contact", "onlineexpert",
        "compinfo", "mythomann", "index", "prodnews", "hotdeals", "cat",
        "special", "topseller", "blowouts", "presentkort", "classified", "deal",
        "cyber", "downloaddeals", "new",
    )

    @staticmethod
    def _subcategory_links(html: str, base: str) -> list[str]:
        """Collect linked subcategory (.html) pages so the crawler can descend.

        Thomann paginates via JavaScript, so a single category page only lists its
        own products. To collect the whole tree we follow subcategory links.

        We restrict descent to the on-page **subcategory grid** (anchors carrying
        the ``fx-category-grid`` class). That grid lists the *children* of the
        current category only; the global header / mega-menu navigation (which
        links to *sibling* top-level categories the operator did not select)
        lives in separate ``hidden`` markup and is ignored. This keeps full-tree
        traversal inside the chosen category's branch instead of leaking into
        unrelated categories.
        """
        host = urlparse(base).netloc
        anchors: list[str] = []
        for tag in re.findall(r"<a\b[^>]*>", html or ""):
            if "fx-category-grid" not in tag.lower():
                continue
            hm = re.search(r'href="([^"]+)"', tag, re.IGNORECASE)
            if hm:
                anchors.append(hm.group(1))
        if not anchors:
            # Fallback for pages without the grid markup: take any internal
            # ``.html`` link (broader, may include sibling nav — only used when
            # there is no category grid to scope from).
            anchors = re.findall(r'href="([^"]+)"', html or "")
        out: list[str] = []
        for href in anchors:
            full = urljoin(base, href)
            parsed = urlparse(full)
            if parsed.netloc and host and parsed.netloc != host:
                continue
            if parsed.query or parsed.fragment:
                continue
            if "_p_" in full or "/p/" in full:
                continue
            if not parsed.path.lower().endswith(".html"):
                continue
            seg = parsed.path.rstrip("/").split("/")[-1]
            if any(s in seg for s in ThomannScraperPlugin._SKIP_SEGMENTS):
                continue
            out.append(full)
        # de-dupe, keep order
        seen: set[str] = set()
        unique = []
        for u in out:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique

    @staticmethod
    def _next_page_urls(html: str, current: str) -> list[str]:
        out: list[str] = []
        for href in re.findall(r'href="([^"]+)"', html):
            low = href.lower()
            if "pg=" in low or "page=" in low or re.search(r"[?/_]p?g?_?\d+\.html", low):
                full = urljoin(current, href)
                if full != current:
                    out.append(full)
        return out[:5]

    @classmethod
    def _products_from_listing(cls, html: str, base: str) -> list[dict]:
        """Extract every product rendered inline on a category/listing page.

        Thomann's listing pages render each product as an ``<a
        class="fx-product-box …">`` card containing the name, brand, image
        (whose URL embeds the article id in ``/prod/<id>``), and price. Scraping
        the cards yields the whole listing in a **single request**, which is far
        more robust against Thomann's Cloudflare rate-limiting than fetching one
        product page per item.
        """
        out: list[dict] = []
        host = urlparse(base).netloc
        card_re = re.compile(
            r'<a\b(?P<open>[^>]*)>(?P<body>.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        for m in card_re.finditer(html or ""):
            open_tag = m.group("open")
            if "fx-product" not in open_tag.lower():
                continue
            hm = re.search(r'href="([^"]+)"', open_tag)
            if not hm:
                continue
            full = urljoin(base, hm.group(1))
            if host and urlparse(full).netloc != host:
                continue
            if not full.lower().endswith(".htm"):
                continue
            body = m.group("body")

            # Name (image alt/title is the full "Brand Model" string).
            name = None
            im = re.search(r'alt="([^"]+)"', body) or re.search(r'title="([^"]+)"', body)
            if im:
                name = im.group(1).strip()
            if not name:
                dm = re.search(
                    r'description__manufacturer[^>]*>([^<]+)</span>\s*([^<]+)<', body
                )
                if dm:
                    name = f"{dm.group(1).strip()} {dm.group(2).strip()}".strip()
            if not name:
                continue

            # Brand (separate manufacturer span when present).
            brand = None
            bm = re.search(r'description__manufacturer[^>]*>([^<]+)<', body)
            if bm:
                brand = bm.group(1).strip()

            # SKU = the article id embedded in the image URL (…/pics/prod/<id>).
            sku = None
            sm = re.search(r'(?:data-srcset|src)="[^"]*pics/prod/(\d+)', body)
            if sm:
                sku = sm.group(1)
            if not sku:
                pm = re.search(r"_p[_-](\d+)", full)
                sku = pm.group(1) if pm else None

            image_url = None
            im2 = re.search(r'data-srcset="([^"]+)"', body) or re.search(r'src="([^"]+)"', body)
            if im2:
                image_url = im2.group(1)

            # Price + currency from the price block.
            price = None
            currency = None
            price_region = body
            pr = re.search(r'<div class="price">(.*?)</div>\s*</div>', body, re.DOTALL)
            if pr:
                price_region = pr.group(1)
            for tok in re.finditer(
                r"(\d[\d  .]*)\s*(kr|SEK|:-|EUR|€)", price_region, re.IGNORECASE
            ):
                num = _coerce_float(re.sub(r"[^\d.,]", "", tok.group(1)))
                if num is not None:
                    price = num
                    cur = tok.group(2).lower()
                    currency = {
                        "kr": "SEK",
                        "sek": "SEK",
                        ":-": "SEK",
                        "eur": "EUR",
                        "€": "EUR",
                    }.get(cur, cur.upper())
                    break

            out.append(
                {
                    "name": name,
                    "sku": sku,
                    "brand": brand or "Thomann",
                    "category": None,  # filled by the caller from the breadcrumb
                    "description": None,
                    "image_url": image_url,
                    "unit_cost": price,
                    "currency": currency,
                    "product_url": full,
                    "availability": None,
                }
            )
        return out

    # -- normalisation ------------------------------------------------------

    @staticmethod
    def discover_categories(
        base_url: str = "", config: dict | None = None, max_categories: int = 200
    ) -> list[dict]:
        """Discover Thomann category links from a page (home, category, …).

        Best-effort: extracts internal ``.html`` links that are not product pages
        and strips the locale prefix, returning ``{"name", "url"}`` entries. The
        exact set depends on the page's markup, so the UI should let the user
        pick the relevant ones rather than trusting the list blindly.

        ``base_url`` is the page to start discovery from (e.g. the configured
        ``store``). If omitted, the configured ``store`` (or the default Swedish
        store) is used, so category discovery always respects the selected
        regional store.
        """
        if not base_url:
            base_url = (config or {}).get("store") or "https://www.thomann.se/"
        try:
            resp = httpx.get(base_url, headers=_HEADERS, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:  # noqa: BLE001 - discovery is best-effort
            logger.warning("Thomann category discovery failed for %s: %s", base_url, exc)
            return []
        host = urlparse(base_url).netloc
        locale_re = re.compile(
            r"^/(se|de|intl|en|us|uk|fr|es|it|nl|pl|dk|fi|no|at|ch|be|pt|cz|hu|ro|ru|jp|"
            r"ca|au|br|mx|in|kr|cn|sg|hk|tw|ae|za|tr|gr|ie|sk|si|hr|lt|lv|ee|bg|ua|rs|ba|"
            r"mk|al|me|is|lu|mc|li|sm|ad|fo|gl|vg|tc|bm|cy|mt)(?=/|$)"
        )
        skip_seg = (
            "the_basket", "basket", "wish", "account", "login", "cart", "search",
            "newsletter", "service", "help", "agb", "imprint", "privacy", "sitemap",
            "manufacturer", "brand", "cms", "jobs", "press", "contact",
        )
        cats: dict[str, dict] = {}
        for href, text in re.findall(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE
        ):
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.netloc and host and parsed.netloc != host:
                continue
            if parsed.query or parsed.fragment:
                continue
            if "_p_" in full or "/p/" in full:
                continue  # product pages
            path = parsed.path
            m = locale_re.match(path)
            if m:
                path = path[m.end():]
            if not path.endswith(".html"):
                continue
            seg = path.rstrip("/").split("/")[-1]
            if not seg or any(s in seg for s in skip_seg):
                continue
            name = " ".join(re.sub(r"<[^>]+>", "", text).split()).strip()
            if not name:
                continue
            if full not in cats:
                cats[full] = {"name": name, "url": full}
            if len(cats) >= max_categories:
                break
        return list(cats.values())

    def normalize(self, raw_items: list[dict]) -> list[VendorEquipmentRecord]:
        records: list[VendorEquipmentRecord] = []
        for item in raw_items or []:
            name = item.get("name")
            if not name:
                continue
            try:
                rec = VendorEquipmentRecord(
                    name=name,
                    sku=item.get("sku"),
                    barcode=item.get("barcode"),
                    external_reference=item.get("sku") or item.get("external_reference"),
                    brand=item.get("brand"),
                    category=item.get("category"),
                    description=item.get("description"),
                    image_url=item.get("image_url"),
                    unit_cost=_coerce_float(item.get("unit_cost")),
                    currency=item.get("currency") or self.default_currency,
                    product_url=item.get("product_url"),
                    availability=item.get("availability"),
                    source_plugin=self.id,
                )
            except Exception as exc:  # noqa: BLE001 - skip malformed rows
                logger.debug("Skipping malformed Thomann row: %s", exc)
                continue
            records.append(rec)
        return records


# Register with the importer plugin registry on import.
IMPORTER_PLUGINS[ThomannScraperPlugin.id] = ThomannScraperPlugin
