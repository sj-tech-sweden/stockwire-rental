"""Vendor catalog import subsystem.

Pluggable importers normalise an external vendor source (API or CSV) into a
list of :class:`VendorEquipmentRecord`, which are then upserted into the
separate ``vendor_products`` table. The architecture is deliberately
configurable: a generic API/CSV plugin can ingest any source via a ``field_map``
supplied in the request, and concrete vendor plugins can be added by subclassing
:class:`BaseImporterPlugin` and registering them in ``IMPORTER_PLUGINS``.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import httpx
from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.customers.models import Company
from app.domain.inventory.models import VendorProduct
from app.domain.inventory.schemas import VendorProductRead

logger = logging.getLogger(__name__)

# Above this normalised-name similarity we treat two products as the same item
# (mirrors app.domain.purchasing.service.NAME_MATCH_THRESHOLD).
_CLUSTER_NAME_THRESHOLD = 0.85


def _cluster_norm(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _cluster_name_ratio(a: str | None, b: str | None) -> float:
    na, nb = _cluster_norm(a), _cluster_norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def _cluster_reference_keys(vp: VendorProduct) -> set[str]:
    """Identifiers tying a vendor product to a physical item (case-insensitive).

    Mirrors the matching used by the purchasing comparison engine
    (``external_reference``, ``sku``, ``supplier_item_number``,
    ``vendor_item_number``) so the catalog clusters the same way the PO builder
    already recognises cross-supplier duplicates.
    """
    keys: set[str] = set()
    for val in (
        vp.external_reference,
        vp.sku,
        vp.supplier_item_number,
        vp.vendor_item_number,
    ):
        v = (val or "").strip().lower()
        if v:
            keys.add(v)
    return keys


def cluster_vendor_products(
    db: Session,
    vendor_id: int | None = None,
    search: str | None = None,
    active_only: bool = False,
    category: str | None = None,
    brand: str | None = None,
) -> list[dict]:
    """Group vendor products that represent the same physical item.

    Two products join a cluster when they share a reference key, or (as a
    fallback, mirroring the purchasing engine) when at least one of them has no
    reference key and their names are a strong fuzzy match. Returns a list of
    cluster dicts, each with the representative ``id``/``name`` and the member
    vendor products (including ``vendor_name``).
    """
    stmt = select(VendorProduct)
    if vendor_id is not None:
        stmt = stmt.where(VendorProduct.vendor_id == vendor_id)
    if active_only:
        stmt = stmt.where(VendorProduct.is_active.is_(True))
    if category:
        stmt = stmt.where(VendorProduct.category == category)
    if brand:
        stmt = stmt.where(VendorProduct.brand == brand)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (VendorProduct.name.ilike(like))
            | (VendorProduct.sku.ilike(like))
            | (VendorProduct.brand.ilike(like))
            | (VendorProduct.external_reference.ilike(like))
            | (VendorProduct.vendor_item_number.ilike(like))
            | (VendorProduct.supplier_item_number.ilike(like))
        )
    products = db.scalars(stmt).all()
    n = len(products)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    keysets = [_cluster_reference_keys(p) for p in products]
    has_keys = [bool(k) for k in keysets]
    for i in range(n):
        for j in range(i + 1, n):
            if keysets[i] & keysets[j]:
                union(i, j)
            elif (not has_keys[i] or not has_keys[j]) and _cluster_name_ratio(
                products[i].name, products[j].name
            ) >= _CLUSTER_NAME_THRESHOLD:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    clusters: list[dict] = []
    for idxs in groups.values():
        members = [products[i] for i in idxs]
        rep = sorted(
            members, key=lambda m: (-len(_cluster_reference_keys(m)), m.id)
        )[0]
        all_keys = sorted({k for m in members for k in _cluster_reference_keys(m)})
        member_dtos = []
        for m in members:
            dto = VendorProductRead.model_validate(m).model_dump()
            dto["vendor_name"] = m.vendor.name if isinstance(m.vendor, Company) else None
            member_dtos.append(dto)
        clusters.append(
            {
                "id": rep.id,
                "name": rep.name,
                "member_count": len(members),
                "keys": all_keys,
                "members": member_dtos,
            }
        )
    clusters.sort(key=lambda c: (c["name"] or "").lower())
    return clusters



@dataclass
class VendorEquipmentRecord:
    """Normalised product coming from a vendor source."""

    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    image_url: Optional[str] = None
    unit_cost: Optional[float] = None
    external_reference: Optional[str] = None
    vendor_item_number: Optional[str] = None
    supplier_item_number: Optional[str] = None
    product_url: Optional[str] = None
    weight: Optional[float] = None
    country_of_origin: Optional[str] = None
    intrastat_code: Optional[str] = None
    pieces_per_carton: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    incoming_quantity: Optional[int] = None
    incoming_deliveries: Optional[list] = field(default=None)
    currency: Optional[str] = None
    stock_quantity: Optional[int] = None
    availability: Optional[str] = None
    source_plugin: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _extract(item: dict, path: str) -> Any:
    """Resolve a dotted path (or plain key) from a dict.

    XML leaf nodes that carry both text and attributes are represented as a
    dict with a ``#text`` key plus ``@attr`` keys. When such a node is the
    resolved value we return its text so field maps like ``price.net`` yield
    the price rather than the surrounding attribute dict.
    """
    if item is None:
        return None
    current: Any = item
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            # Drill into the first element (e.g. the first picture of a list).
            if not current:
                return None
            first = current[0]
            current = first.get(part) if isinstance(first, dict) else None
        else:
            return None
        if current is None:
            return None
    if isinstance(current, dict) and "#text" in current:
        return current["#text"]
    return current


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    # European decimal notation uses a comma (e.g. "3,88"); normalise to "3.88".
    text = text.replace(",", ".")
    # Drop any thousands separators that remain (e.g. "1.234,56" -> after the
    # comma swap becomes "1.234.56", so remove all but the last dot).
    if text.count(".") > 1:
        last_dot = text.rfind(".")
        text = text[:last_dot].replace(".", "") + text[last_dot:]
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in (".", "-", "-."):
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(_coerce_float(value)))
    except (TypeError, ValueError):
        return None


def _coerce_date(value: Any) -> Optional[date]:
    """Parse supplier delivery-date strings.

    Aurdel encodes incoming-stock ETAs as ``YY-MM-DD`` (e.g. ``26-10-23`` ->
    2026-10-23). The sentinels ``00-01-07`` and ``99-01-15`` mean "no ETA" and
    are returned as ``None`` so they don't pollute the data.
    """
    if value is None or value == "":
        return None
    text = str(value).strip()
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})$", text)
    if not m:
        return None
    yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yy in (0, 99):
        return None
    year = 2000 + yy if yy <= 68 else 1900 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def _normalise_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


# Maps a normalised attribute to the source header/field names that may carry it.
# Used to auto-detect the field mapping for CSV/JSON sources whose column names
# differ from the canonical attribute names.
ATTRIBUTE_ALIASES: dict[str, list[str]] = {
    "name": ["name", "title", "productname", "itemname", "product", "item", "description"],
    "sku": [
        "sku", "internalid", "productid", "id", "code", "article", "articleno",
        "articlenumber", "partnumber", "partno", "model", "itemno",
    ],
    "external_reference": [
        "ean", "eanno", "ean13", "barcode", "barcode", "reference", "ref",
        "externalid", "externalreference",
    ],
    "brand": ["brand", "manufacturer", "make", "supplier"],
    "category": ["category", "type", "group", "department"],
    "description": ["description", "desc", "details", "longdescription", "info", "summary"],
    "unit_cost": [
        "price", "cost", "unitprice", "unit_cost", "priceeach", "netprice", "net",
        "unitcost", "listprice", "salesprice",
    ],
    "image_url": ["image", "imageurl", "photo", "thumbnail", "picture", "img"],
    "dimensions": ["dimensions", "dimension", "size", "spec", "specification"],
    "currency": ["currency", "currencycode", "ccy", "cur", "currencycode"],
    "stock_quantity": [
        "stock", "quantity", "qty", "instock", "stockquantity", "available",
        "inventory", "units", "onhand", "stockqty",
    ],
    "availability": ["availability", "status", "instock", "availabilitystatus", "state"],
}


def infer_field_map(headers: list[str]) -> dict[str, str]:
    """Best-effort mapping from raw record keys to VendorEquipmentRecord attrs."""
    normalised_headers = {_normalise_key(h): h for h in headers}
    mapping: dict[str, str] = {}
    for attr, aliases in ATTRIBUTE_ALIASES.items():
        for alias in aliases:
            header = normalised_headers.get(alias)
            if header and header not in mapping.values():
                mapping[attr] = header
                break
    return mapping


class BaseImporterPlugin(ABC):
    id: str = "base"
    label: str = "Base"
    source_type: str = "api"
    # Declares the config fields the UI should render for this plugin. Each entry:
    #   key, label, type ("text"|"url"|"secret"|"number"|"select"), required,
    #   default, options (for select), help, fixed (URL predefined by plugin).
    config_schema: list = []
    # Default field mapping offered to the user (empty -> backend auto-detects).
    default_field_map: dict = {}

    def __init__(self, field_map: dict | None = None, config: dict | None = None):
        self.field_map = field_map or {}
        self.config = config or {}

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Return raw records (dicts) from the source."""

    def normalize(self, raw_items: list[dict]) -> list[VendorEquipmentRecord]:
        """Map raw records into normalised :class:`VendorEquipmentRecord`."""
        records: list[VendorEquipmentRecord] = []
        valid_fields = VendorEquipmentRecord.__dataclass_fields__.keys()
        for item in raw_items or []:
            values: dict[str, Any] = {}
            for attr, path in self.field_map.items():
                if attr not in valid_fields:
                    continue
                values[attr] = _extract(item, path)
            name = values.get("name")
            if not name:
                continue
            if "unit_cost" in values:
                values["unit_cost"] = _coerce_float(values.get("unit_cost"))
            if "stock_quantity" in values:
                values["stock_quantity"] = _coerce_int(values.get("stock_quantity"))
            if "weight" in values:
                values["weight"] = _coerce_float(values.get("weight"))
            if "pieces_per_carton" in values:
                values["pieces_per_carton"] = _coerce_int(values.get("pieces_per_carton"))
            if "expected_delivery_date" in values:
                values["expected_delivery_date"] = _coerce_date(values.get("expected_delivery_date"))
            if "incoming_quantity" in values:
                values["incoming_quantity"] = _coerce_int(values.get("incoming_quantity"))
            # Apply a per-import default currency when none was provided.
            if values.get("currency") in (None, ""):
                values["currency"] = self.config.get("default_currency")
            values["source_plugin"] = self.id
            record = VendorEquipmentRecord(**{k: values.get(k) for k in valid_fields})
            # Let each plugin build its own product/deeplink URL; most sources
            # have no such field so the base implementation returns None.
            record.product_url = self.build_product_url(record)
            records.append(record)
        return records

    def build_product_url(self, record: VendorEquipmentRecord) -> str | None:
        """Return a deeplink to the product on the vendor's webshop, if known.

        Subclasses override this because the URL scheme is vendor-specific.
        The base implementation has no URL.
        """
        return None

    @classmethod
    def discover_categories(cls, base_url: str) -> list[dict]:
        """Return a list of ``{"name", "url"}`` category links discoverable from
        ``base_url``.

        The base implementation returns nothing; scrapers that expose a browsable
        category tree override this so the UI can offer "pick categories" instead
        of requiring the user to paste listing URLs by hand.
        """
        return []

    def run(self) -> list[VendorEquipmentRecord]:
        return self.normalize(self.fetch())


class GenericApiPlugin(BaseImporterPlugin):
    id = "generic_api"
    label = "Generic API"
    source_type = "api"
    config_schema = [
        {"key": "url", "label": "API URL", "type": "url", "required": True},
        {"key": "default_currency", "label": "Default currency", "type": "text", "default": "SEK"},
    ]

    def fetch(self) -> list[dict]:
        url = self.config.get("url")
        if not url:
            raise ValueError("Missing 'url' in config")
        headers = self.config.get("headers") or {}
        resp = httpx.get(url, headers=headers, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "data", "results", "records"):
                if isinstance(data.get(key), list):
                    return data[key]
        return [data] if isinstance(data, dict) else []

    def normalize(self, raw_items: list[dict]) -> list[VendorEquipmentRecord]:
        if not self.field_map and raw_items:
            headers = list(raw_items[0].keys())
            self.field_map = infer_field_map(headers)
        return super().normalize(raw_items)


class GenericCsvPlugin(BaseImporterPlugin):
    id = "generic_csv"
    label = "Generic CSV"
    source_type = "csv"
    config_schema = [
        {"key": "url", "label": "CSV URL", "type": "url", "required": True},
        {"key": "default_currency", "label": "Default currency", "type": "text", "default": "SEK"},
    ]

    def fetch(self) -> list[dict]:
        url = self.config.get("url")
        if not url:
            raise ValueError("Missing 'url' in config")
        resp = httpx.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        return [dict(row) for row in reader]

    def normalize(self, raw_items: list[dict]) -> list[VendorEquipmentRecord]:
        if not self.field_map and raw_items:
            headers = list(raw_items[0].keys())
            self.field_map = infer_field_map(headers)
        return super().normalize(raw_items)


def _local(tag: str) -> str:
    """Return the local name of an XML tag (strip ``{namespace}`` prefix + whitespace)."""
    name = tag.split("}", 1)[-1] if "}" in tag else tag
    return name.strip()


def _element_to_nested_dict(el: ET.Element) -> Any:
    """Recursively convert an XML element to nested dicts (repeated tags -> list).

    Element attributes are captured under ``@name`` keys so the field map can
    reference them (e.g. an ``<item id="…">`` becomes ``"@id"``).
    """
    children = list(el)
    attrs = {f"@{_local(k)}": v for k, v in el.attrib.items()}
    if not children:
        text = (el.text or "").strip()
        if attrs:
            attrs["#text"] = text
            return attrs
        return text
    result: dict[str, Any] = dict(attrs)
    for child in children:
        value = _element_to_nested_dict(child)
        tag = _local(child.tag)
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value
    return result


def _flatten_dict(d: dict, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in d.items():
        composed = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten_dict(value, f"{composed}."))
        else:
            flat[composed] = value
    return flat


def _find_item_elements(root: ET.Element) -> list[ET.Element]:
    """Locate the repeating product/item element in a price file.

    Picks the tag that repeats, has element children, and whose instances share
    a single parent tag. Among those, it ranks by the number of *distinct* child
    tags an instance has (a true product record is richly structured), so a noisy
    leaf container such as ``subcategory`` (which repeats more and also has a
    single parent) is not mistaken for the product.
    """
    from collections import defaultdict

    parent_tags: dict[str, set] = defaultdict(set)
    has_children: set[str] = set()
    element_lists: dict[str, list] = defaultdict(list)

    def walk(el: ET.Element, parent_local: str | None) -> None:
        tag = _local(el.tag)
        if parent_local is not None:
            parent_tags[tag].add(parent_local)
        if list(el):
            has_children.add(tag)
        element_lists[tag].append(el)
        for child in el:
            walk(child, tag)

    walk(root, None)

    # A feed with a single product still has a usable product element: when the
    # root wraps exactly one child element, that child *is* the product. This
    # keeps single-item previews/feeds (and unit tests) working instead of
    # falling through to a repeating leaf such as <description>.
    children = list(root)
    if len(children) == 1 and list(children[0]):
        return [children[0]]

    def variety(els: list) -> int:
        return max((len({_local(c.tag) for c in e}) for e in els), default=0)

    candidates = [
        (tag, variety(els), len(els))
        for tag, els in element_lists.items()
        if len(els) >= 2 and len(parent_tags.get(tag, set())) == 1 and tag in has_children
    ]
    if not candidates:
        candidates = [
            (tag, variety(els), len(els))
            for tag, els in element_lists.items()
            if len(els) >= 2 and tag in has_children
        ]
    if not candidates:
        return [root] if list(root) else []
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best = candidates[0][0]
    return element_lists[best]


def parse_xml_items(xml_text: str) -> list[dict]:
    """Parse an XML price file into a list of dicts usable by the field map.

    Each record contains both its nested structure and flattened dotted keys so the
    field map can reference either simple tag names (``ItemNo``) or paths
    (``Price.Net``).
    """
    root = ET.fromstring(xml_text)
    items: list[dict] = []
    for el in _find_item_elements(root):
        nested = _element_to_nested_dict(el)
        if not isinstance(nested, dict):
            continue
        merged = dict(nested)
        merged.update(_flatten_dict(nested))
        items.append(merged)
    return items


class AurdelPricesPlugin(BaseImporterPlugin):
    """Importer for Aurdel's customer price API (``/Prices/getPrice``).

    The endpoint returns an XML price file. This plugin builds the request
    exactly per the published OpenAPI spec and parses the XML response.

    Required config: ``customerid`` (e.g. ``ADSE-C005985``, including the
    reseller prefix), ``companyid`` (e.g. ``ADSE``; if only two characters are
    supplied the API prepends ``AD``). ``apikey`` or ``customerpassword`` for
    auth. Optional: ``database`` (default ``item``), ``filetype`` and
    ``language`` (left empty to use the server's default format — requesting
    ``extended`` returns an empty list for customers without extended data),
    ``itemid`` (comma list), ``default_currency`` (default ``SEK``),
    ``url`` (override base URL).
    """

    id = "aurdel_prices"
    label = "Aurdel Prices"

    def build_product_url(self, record: VendorEquipmentRecord) -> str | None:
        # Aurdel's webshop deeplink is https://aurdel.com/se/<article number>,
        # where the article number is the item id exposed as @id / sku.
        article = record.supplier_item_number or record.sku
        return f"https://aurdel.com/se/{article}" if article else None

    def normalize(self, raw_items: list[dict]) -> list[VendorEquipmentRecord]:
        records = super().normalize(raw_items)
        # Capture *every* advertised delivery, not just the first. The XML may
        # carry several <date quantity="N">YY-MM-DD</date> entries per item.
        by_sku: dict[str, list[dict]] = {}
        for item in raw_items or []:
            sku = _extract(item, "sku") or _extract(item, "@id")
            if not sku:
                continue
            # Navigate to the raw <date> node(s) WITHOUT the #text unwrap that
            # _extract applies at the leaf, so we keep the @quantity attribute.
            node = item
            for part in ("stock", "delivery", "date"):
                if isinstance(node, dict):
                    node = node.get(part)
                elif isinstance(node, list):
                    node = node[0].get(part) if node else None
                else:
                    node = None
                if node is None:
                    break
            entries: list[dict] = []
            for d in node if isinstance(node, list) else [node]:
                if not isinstance(d, dict):
                    continue
                dt = _coerce_date(d.get("#text"))
                qty = _coerce_int(d.get("@quantity"))
                if dt is None:
                    continue
                entries.append(
                    {"expected_delivery_date": dt.isoformat(), "incoming_quantity": qty}
                )
            if entries:
                by_sku[sku] = entries
        for rec in records:
            rec.incoming_deliveries = by_sku.get(rec.sku)
        return records

    source_type = "api"
    # URL is fixed by the plugin; users never edit it.
    config_schema = [
        {"key": "customerid", "label": "Customer ID", "type": "text", "required": True},
        {
            "key": "companyid",
            "label": "Company ID",
            "type": "text",
            "required": True,
            "help": "2 or 4 letters; a 2-letter code gets 'AD' prepended (e.g. SE -> ADSE).",
        },
        {"key": "apikey", "label": "API key", "type": "secret", "required": False},
        {"key": "customerpassword", "label": "Customer password", "type": "secret", "required": False},
        {
            "key": "database",
            "label": "Database",
            "type": "select",
            "options": ["item", "stock", "stockandprice", "manufacturer", "specifications"],
            "default": "item",
            "help": "Use 'item' (default) unless you specifically need stock/price variants.",
        },
        {
            "key": "filetype",
            "label": "File type",
            "type": "select",
            "options": ["legacy", "extended"],
            "help": "Leave empty to use the server default. 'extended' returns an empty list for customers without extended data.",
        },
        {
            "key": "language",
            "label": "Language",
            "type": "select",
            "options": ["all", "da", "en-us", "fi", "nb-no", "sv"],
            "help": "Only applies to the 'extended' file type. Leave empty to use the server default.",
        },
        {
            "key": "default_currency",
            "label": "Default currency",
            "type": "text",
            "default": "SEK",
            "help": "Used when a row has no currency of its own.",
        },
    ]
    default_field_map = {
        # Aurdel's item XML: <item id="…"> … <description><short>/<long>, <manufacturer><description>,
        # <ean>, <price currencycode="…"><net>, <stock quantity="…">. Attributes are referenced as "@name".
        "name": "description.short",
        "sku": "@id",
        "external_reference": "ean",
        "vendor_item_number": "manufacturer.@id",
        "supplier_item_number": "@id",
        "unit_cost": "price.net",
        "brand": "manufacturer.description",
        "category": "categories.category.subcategory.description",
        "description": "description.long",
        "image_url": "pictures.list.picture.url",
        "currency": "price.@currencycode",
        "stock_quantity": "stock.@quantity",
        "weight": "weight",
        "country_of_origin": "countryoforigin",
        "intrastat_code": "intrastat",
        "pieces_per_carton": "piecespercarton",
        "expected_delivery_date": "stock.delivery.date.#text",
        "incoming_quantity": "stock.delivery.date.@quantity",
    }

    def __init__(self, field_map: dict | None = None, config: dict | None = None):
        super().__init__(field_map, config)
        # The API expects a 4-letter company id (e.g. "ADSE"); if the user
        # supplies the short 2-letter code, we prepend "AD".
        companyid = self.config.get("companyid")
        if companyid and len(companyid) == 2:
            self.config["companyid"] = f"AD{companyid}"

    def fetch(self) -> list[dict]:
        base_url = (self.config.get("url") or "https://api.aurdel.com").rstrip("/")
        if not self.config.get("customerid") or not self.config.get("companyid"):
            raise ValueError("Missing 'customerid'/'companyid' in config")
        apikey = self.config.get("apikey")
        customerpassword = self.config.get("customerpassword")

        def build_params(with_optional: bool) -> dict:
            params: dict = {
                "database": self.config.get("database") or "item",
                "customerid": self.config.get("customerid"),
                "companyid": self.config.get("companyid"),
            }
            if with_optional:
                filetype = self.config.get("filetype")
                if filetype:
                    params["filetype"] = filetype
                language = self.config.get("language")
                if language:
                    params["language"] = language
            itemid = self.config.get("itemid")
            if itemid:
                params["itemid"] = itemid
            # Customer password takes precedence over the api key per the spec.
            if customerpassword:
                params["customerpassword"] = customerpassword
            elif apikey:
                params["apikey"] = apikey
            clean = {k: (v.strip() if isinstance(v, str) else v) for k, v in params.items()}
            return {k: v for k, v in clean.items() if v not in (None, "")}

        headers = dict(self.config.get("headers") or {})
        headers.setdefault("Accept", "application/xml")

        # First attempt honours the user's filetype/language selection. If that
        # yields an empty price list (customers without extended-format data
        # return an empty <PriceList> for filetype=extended), automatically retry
        # without those optional params so the import still works with stored
        # configs that include them.
        items = self._request(base_url, build_params(True), headers)
        if not items and (self.config.get("filetype") or self.config.get("language")):
            logger.info("Aurdel: empty result with filetype/language; retrying without them")
            items = self._request(base_url, build_params(False), headers)
        if not items:
            raise RuntimeError(
                "Aurdel returned no price rows for this customer/company. "
                "Check customerid/companyid/database, or try a different Database value."
            )
        return items

    def _request(self, base_url: str, params: dict, headers: dict) -> list[dict]:
        resp = httpx.get(
            f"{base_url}/Prices/getPrice",
            params=params,
            headers=headers,
            timeout=300,
            follow_redirects=True,
        )
        if resp.status_code == 503:
            raise RuntimeError(
                "Aurdel price service unavailable (503). It is offline 12:00–16:00 Sweden time."
            )
        if resp.status_code >= 400:
            detail = resp.text[:1000] if resp.text else resp.reason_phrase
            raise RuntimeError(f"Aurdel price request failed ({resp.status_code}): {detail}")
        content_type = resp.headers.get("content-type", "")
        text = resp.text
        logger.info("Aurdel getPrice -> %s, content-type=%s, bytes=%d", resp.status_code, content_type, len(text))
        if "xml" in content_type or text.lstrip().startswith("<"):
            stripped = text.lstrip()
            if stripped.lower().startswith("<error"):
                raise RuntimeError(f"Aurdel returned an error: {text[:1000]}")
            return parse_xml_items(text)
        if text.strip().startswith("{") or text.strip().startswith("["):
            return resp.json()
        return []


IMPORTER_PLUGINS: dict[str, type[BaseImporterPlugin]] = {
    GenericApiPlugin.id: GenericApiPlugin,
    GenericCsvPlugin.id: GenericCsvPlugin,
    AurdelPricesPlugin.id: AurdelPricesPlugin,
}


def register_importer_plugin(plugin_cls: type[BaseImporterPlugin]) -> None:
    """Register an importer plugin class so ``get_plugin`` can resolve it."""
    IMPORTER_PLUGINS[plugin_cls.id] = plugin_cls


def get_plugin(plugin_id: str, field_map: dict | None, config: dict | None) -> BaseImporterPlugin:
    plugin_cls = IMPORTER_PLUGINS.get(plugin_id)
    if plugin_cls is None:
        raise ValueError(f"Unknown importer plugin: {plugin_id}")
    return plugin_cls(field_map=field_map, config=config)


_MAX_NUMERIC_12_2 = Decimal("9999999999.99")


def _clamp_unit_cost(value):
    """Clamp a unit cost to the ``Numeric(12, 2)`` column range."""
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except Exception:
        return None
    if d > _MAX_NUMERIC_12_2:
        logger.warning("Clamping oversized unit_cost %s to %s", value, _MAX_NUMERIC_12_2)
        return _MAX_NUMERIC_12_2
    if d < -_MAX_NUMERIC_12_2:
        logger.warning("Clamping undersized unit_cost %s to %s", value, -_MAX_NUMERIC_12_2)
        return -_MAX_NUMERIC_12_2
    return d


def upsert_vendor_products(
    db: Session,
    records: list[VendorEquipmentRecord],
    vendor_id: Optional[int],
    source_plugin: Optional[str],
    progress_callback: Optional[callable] = None,
    batch_size: int = 500,
) -> dict:
    """Upsert normalised records into ``vendor_products``.

    Matching preference: ``external_reference`` (scoped to the source plugin),
    then ``sku`` (scoped to the vendor). Existing rows have their editable
    fields refreshed; new rows are created.

    ``progress_callback(processed, total, created, updated)`` is invoked after
    each batch so long-running imports can report progress.
    """
    created = 0
    updated = 0
    total = len(records)

    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        for rec in batch:
            existing: Optional[VendorProduct] = None
            if rec.external_reference:
                existing = db.scalar(
                    select(VendorProduct).where(
                        VendorProduct.external_reference == rec.external_reference,
                        VendorProduct.source_plugin == (source_plugin or rec.source_plugin),
                    )
                )
            if existing is None and rec.sku:
                existing = db.scalar(
                    select(VendorProduct).where(
                        VendorProduct.sku == rec.sku,
                        VendorProduct.vendor_id == vendor_id,
                    )
                )
            unit_cost = _clamp_unit_cost(rec.unit_cost)
            if existing is not None:
                existing.name = rec.name
                existing.sku = rec.sku
                existing.barcode = rec.barcode
                existing.brand = rec.brand
                existing.category = rec.category
                existing.description = rec.description
                existing.dimensions = rec.dimensions
                existing.image_url = rec.image_url
                existing.unit_cost = unit_cost
                existing.currency = rec.currency
                existing.stock_quantity = rec.stock_quantity
                existing.availability = rec.availability
                existing.vendor_id = vendor_id
                existing.external_reference = rec.external_reference
                existing.vendor_item_number = rec.vendor_item_number
                existing.supplier_item_number = rec.supplier_item_number
                existing.product_url = rec.product_url
                existing.weight = rec.weight
                existing.country_of_origin = rec.country_of_origin
                existing.intrastat_code = rec.intrastat_code
                existing.pieces_per_carton = rec.pieces_per_carton
                existing.expected_delivery_date = rec.expected_delivery_date
                existing.incoming_quantity = rec.incoming_quantity
                existing.incoming_deliveries = rec.incoming_deliveries
                existing.source_plugin = source_plugin or rec.source_plugin
                existing.is_active = True
                existing.last_synced_at = _utcnow()
                updated += 1
            else:
                vp = VendorProduct(
                    name=rec.name,
                    sku=rec.sku,
                    barcode=rec.barcode,
                    brand=rec.brand,
                    category=rec.category,
                    description=rec.description,
                    dimensions=rec.dimensions,
                    image_url=rec.image_url,
                    unit_cost=unit_cost,
                    currency=rec.currency,
                    stock_quantity=rec.stock_quantity,
                    availability=rec.availability,
                    vendor_id=vendor_id,
                    external_reference=rec.external_reference,
                    vendor_item_number=rec.vendor_item_number,
                    supplier_item_number=rec.supplier_item_number,
                    product_url=rec.product_url,
                    weight=rec.weight,
                    country_of_origin=rec.country_of_origin,
                    intrastat_code=rec.intrastat_code,
                    pieces_per_carton=rec.pieces_per_carton,
                    expected_delivery_date=rec.expected_delivery_date,
                    incoming_quantity=rec.incoming_quantity,
                    incoming_deliveries=rec.incoming_deliveries,
                    source_plugin=source_plugin or rec.source_plugin,
                    last_synced_at=_utcnow(),
                    is_active=True,
                )
                db.add(vp)
                created += 1
        db.commit()
        if progress_callback:
            progress_callback(min(i + batch_size, total), total, created, updated)

    return {"created": created, "updated": updated}


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
