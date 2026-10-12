"""Web scraper plugin for the Ubiquiti store (https://eu.store.ui.com).

UI.com is a server-rendered Next.js storefront. Product data is not in a clean
REST endpoint but is embedded as JSON inside the streamed React Server Component
(``self.__next_f.push(...)``) payloads. This plugin fetches the listing HTML and
recovers the product objects by brace-balanced JSON extraction, then maps them to
:class:`VendorEquipmentRecord`.

Because the data lives in HTML rather than a real API, this plugin is inherently
more fragile than the API/CSV importers: a UI.com front-end redesign can move or
rename the embedded fields. Treat the extracted fields as best-effort and review
the imported products before approving them.

ToS note: scraping UI.com may be disallowed by its terms of service. Only enable
this for sources you are permitted to crawl, and respect robots.txt / rate limits.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urljoin

import httpx

from app.domain.inventory.vendor_catalog import (
    IMPORTER_PLUGINS,
    BaseImporterPlugin,
    VendorEquipmentRecord,
)

logger = logging.getLogger(__name__)

_BASE_HOST = "eu.store.ui.com"
_REGION_PREFIX = "/eu/en"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _iter_json_objects(text: str):
    """Yield every brace-balanced JSON object found in ``text``.

    UI.com embeds product data inside ``self.__next_f.push([...])`` chunks. The
    objects are valid JSON, so a depth-counting scan recovers them without a
    full HTML parser.
    """
    for m in re.finditer(r"\{", text):
        i = m.start()
        depth = 0
        k = i
        while k < len(text):
            c = text[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blob = text[i : k + 1]
        try:
            obj = json.loads(blob)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(obj, dict):
            yield obj


@dataclass
class _Money:
    amount: float | None = None
    currency: str | None = None


def _as_money(value) -> _Money:
    if isinstance(value, dict):
        amount = value.get("amount")
        return _Money(
            amount=float(amount) if isinstance(amount, (int, float)) else None,
            currency=value.get("currency"),
        )
    if isinstance(value, (int, float)):
        return _Money(amount=float(value))
    return _Money()


def _first(*values):
    for v in values:
        if v:
            return v
    return None


class UiComScraperPlugin(BaseImporterPlugin):
    """Scrape products from a UI.com listing (category / collection / search) page."""

    id = "uicom_scraper"
    label = "Ubiquiti Store (UI.com) scraper"
    source_type = "scraper"
    # URL is fixed to the EU store; the user only supplies the listing paths.
    config_schema: ClassVar[list] = [
        {
            "key": "start_urls",
            "label": "UI.com listing URLs",
            "type": "textarea",
            "required": True,
            "help": (
                "One category, collection or search URL per line, e.g. "
                "https://eu.store.ui.com/eu/en/category/all-wifi"
            ),
        },
        {
            "key": "default_currency",
            "label": "Default currency",
            "type": "text",
            "default": "EUR",
            "help": "Used when a product has no currency of its own.",
        },
        {
            "key": "max_pages",
            "label": "Max pages per URL",
            "type": "number",
            "default": 5,
            "help": "Follow ?page=N pagination up to this many pages per start URL.",
        },
    ]
    default_field_map: ClassVar[dict] = {}

    def __init__(self, field_map: dict | None = None, config: dict | None = None):
        super().__init__(field_map, config)
        raw_urls = str(self.config.get("start_urls") or "")
        self.start_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
        self.max_pages = int(self.config.get("max_pages") or 5)
        self.default_currency = self.config.get("default_currency") or "EUR"

    # ── fetching ─────────────────────────────────────────────────────────────

    def fetch(self) -> list[dict]:
        products: dict[str, dict] = {}
        for base in self.start_urls:
            for html in self._fetch_pages(base):
                for obj in _iter_json_objects(html):
                    if not self._is_product(obj):
                        continue
                    record = self._to_record_dict(obj)
                    if record and record.get("sku"):
                        products[record["sku"]] = record
        return list(products.values())

    def _fetch_pages(self, base: str):
        seen: set[str] = set()
        url = base
        for _ in range(self.max_pages):
            if url in seen:
                break
            seen.add(url)
            try:
                resp = httpx.get(url, headers=_HEADERS, timeout=60, follow_redirects=True)
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001 - scraping is best-effort
                logger.warning("UI.com scrape failed for %s: %s", url, exc)
                break
            yield resp.text
            nxt = self._next_page_url(resp.text, url)
            if not nxt or nxt == url:
                break
            url = nxt

    @staticmethod
    def _next_page_url(html: str, current: str) -> str | None:
        m = re.search(r"[?&]page=(\d+)", current)
        cur = int(m.group(1)) if m else 1
        nxt = cur + 1
        for href in re.findall(r'href="([^"]+)"', html):
            if re.search(rf"[?&]page={nxt}\b", href):
                return urljoin(current, href)
        return None

    # ── parsing ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_product(obj: dict) -> bool:
        return (
            isinstance(obj, dict)
            and isinstance(obj.get("title"), str)
            and bool(obj.get("slug"))
            and isinstance(obj.get("displaySku"), str)
            and "minDisplayPrice" in obj
        )

    def _to_record_dict(self, obj: dict) -> dict:
        money = _as_money(obj.get("minDisplayPrice"))
        amount = money.amount
        unit_cost = round(amount / 100.0, 2) if amount is not None else None
        currency = money.currency or self.default_currency

        thumbnail = obj.get("thumbnail")
        image_url = thumbnail.get("url") if isinstance(thumbnail, dict) else None

        slug = obj.get("slug")
        category = obj.get("organizationalCollectionSlug") or obj.get(
            "proCollectionSlug"
        )
        if category:
            product_url = f"https://{_BASE_HOST}{_REGION_PREFIX}/category/{category}/products/{slug}"
        else:
            product_url = f"https://{_BASE_HOST}{_REGION_PREFIX}/products/{slug}"

        status = obj.get("status")
        sold_out = bool(status) and "sold" in str(status).lower()

        sku = obj["displaySku"]
        return {
            "name": obj["title"],
            "sku": sku,
            "external_reference": sku,
            "description": obj.get("shortDescription"),
            "image_url": image_url,
            "unit_cost": unit_cost,
            "currency": currency,
            "category": category,
            "product_url": product_url,
            "stock_quantity": 0 if sold_out else None,
            "availability": status,
        }

    # ── normalisation ─────────────────────────────────────────────────────────

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
                    external_reference=item.get("external_reference") or item.get("sku"),
                    description=item.get("description"),
                    image_url=item.get("image_url"),
                    unit_cost=item.get("unit_cost"),
                    currency=item.get("currency") or self.default_currency,
                    category=item.get("category"),
                    product_url=item.get("product_url"),
                    stock_quantity=item.get("stock_quantity"),
                    availability=item.get("availability"),
                    source_plugin=self.id,
                )
            except Exception as exc:  # noqa: BLE001 - skip malformed rows
                logger.debug("Skipping malformed vendor row: %s", exc)
                continue
            records.append(rec)
        return records


# Register with the importer plugin registry on import.
IMPORTER_PLUGINS[UiComScraperPlugin.id] = UiComScraperPlugin
