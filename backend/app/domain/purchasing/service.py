"""Best-purchase / supplier-comparison engine.

Given a job whose requirements already link a chosen ``vendor_product`` (the
user's current purchase selection), find alternative suppliers for the same
physical item across the vendor catalog and recommend:

* a **single-cheapest supplier** — one vendor that can supply the most lines at
  the lowest total (converted into a common report currency), and
* a **multi-supplier optimiser** — for every line pick the cheapest in-stock
  vendor and sum the totals, reporting how many suppliers are required.

The recommended basket (multi-supplier optimiser by default) can be persisted
as a :class:`~app.domain.purchasing.models.PurchaseDraft`.
"""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Statuses under which a PO can still be edited / received against. Kept in one
# place so lookup, add-lines and any other "open PO" checks stay consistent.
OPEN_PO_STATUSES = ("draft", "partial")

from app.domain.customers.models import Company, Customer
from app.domain.inventory.models import (
    Device,
    Product,
    ProductSupplier,
    VendorProduct,
)
from app.domain.jobs.models import Job, JobRequirement
from app.domain.purchasing.models import (
    PurchaseDraft,
    PurchaseDraftLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.domain.purchasing.schemas import POLineUpdateRequest
from app.domain.settings.models import AppSetting

FX_RATES_KEY = "fx_rates"
DEFAULT_BASE = "SEK"
# Above this normalised-name similarity we treat two products as the same item.
NAME_MATCH_THRESHOLD = 0.85


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _name_ratio(a: str | None, b: str | None) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def _is_in_stock(vp: VendorProduct) -> bool:
    out = bool(vp.availability) and vp.availability.strip().lower() == "out"
    depleted = vp.stock_quantity is not None and vp.stock_quantity <= 0
    return not (out or depleted)


def load_fx_rates(db: Session) -> dict[str, Any] | None:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == FX_RATES_KEY))
    if not setting or not setting.value_json:
        return None
    try:
        data = json.loads(setting.value_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    rates = data.get("rates") or {}
    return {
        "base": str(data.get("base", DEFAULT_BASE)).upper() or DEFAULT_BASE,
        "rates": {str(k).upper(): float(v) for k, v in rates.items() if v is not None},
    }


def convert(
    amount: Any,
    currency: str | None,
    fx: dict[str, Any] | None,
    report_currency: str | None,
) -> tuple[Decimal | None, bool]:
    """Convert ``amount`` from ``currency`` into the report currency.

    Returns ``(base_amount, fx_missing)``. ``fx_missing`` is True when a rate
    for ``currency`` is not configured (the candidate is then excluded from
    totals but still surfaced in the comparison table).
    """
    if amount is None:
        return None, False
    try:
        amt = Decimal(str(amount))
    except (ValueError, TypeError):
        return None, False
    currency = (currency or "").strip().upper() or None
    fx = fx if isinstance(fx, dict) else {}
    fx_base = (fx.get("base") or DEFAULT_BASE).upper()
    target = (report_currency or fx_base).upper()
    if not currency or currency == target:
        return amt.quantize(Decimal("0.0001")), False
    # Normalise rate keys so "eur" / "EUR" both match the candidate currency.
    rates = {str(k).upper(): v for k, v in (fx.get("rates") or {}).items()}

    # Step 1: express the amount in `currency` relative to the FX base.
    if currency == fx_base:
        in_base = amt
    else:
        rate = rates.get(currency)
        if rate is None:
            return None, True
        try:
            in_base = amt * Decimal(str(rate))
        except (ValueError, TypeError, ArithmeticError):
            return None, True

    # Step 2: convert the FX base amount into the requested report currency.
    if target == fx_base:
        result = in_base
    else:
        rate = rates.get(target)
        if rate is None:
            return None, True
        try:
            result = in_base / Decimal(str(rate))
        except (ValueError, TypeError, ArithmeticError, ZeroDivisionError):
            return None, True

    return result.quantize(Decimal("0.0001")), False


def _reference_keys(vp: VendorProduct) -> set[str]:
    """Identifiers that tie a vendor product to a physical item.

    A manually-added item may store the manufacturer article number in ``sku``
    while an imported one stores it in ``external_reference``, so we match on all
    of them (and the supplier/vendor item numbers) to recognise the same product
    offered by different suppliers.
    """
    keys: set[str] = set()
    for val in (
        vp.external_reference,
        vp.sku,
        vp.supplier_item_number,
        vp.vendor_item_number,
    ):
        v = (val or "").strip()
        if v:
            keys.add(v)
    return keys


def _find_candidates(
    db: Session, selected_vp: VendorProduct
) -> tuple[list[tuple[VendorProduct, str]], str | None]:
    """Return ``(matches, alt_method)`` for the selected vendor product.

    ``matches`` always includes the selected product itself (method "selected");
    alternatives are matched by a shared identifier (``external_reference``,
    ``sku`` or supplier/vendor item number) first, falling back to a fuzzy
    product-name match when no cross-vendor identifier matches exist.
    """
    results: list[tuple[VendorProduct, str]] = [(selected_vp, "selected")]
    seen: set[int] = {selected_vp.id}
    alt_method: str | None = None

    keys = _reference_keys(selected_vp)
    if keys:
        matches = db.scalars(
            select(VendorProduct).where(
                VendorProduct.is_active.is_(True),
                (
                    VendorProduct.external_reference.in_(keys)
                    | VendorProduct.sku.in_(keys)
                    | VendorProduct.supplier_item_number.in_(keys)
                    | VendorProduct.vendor_item_number.in_(keys)
                ),
            )
        ).all()
        for vp in matches:
            if vp.id in seen:
                continue
            seen.add(vp.id)
            results.append((vp, "external_reference"))
        if len(results) > 1:
            alt_method = "external_reference"

    if alt_method is None:
        target = selected_vp.name
        others = db.scalars(
            select(VendorProduct).where(VendorProduct.is_active.is_(True))
        ).all()
        for vp in others:
            if vp.id in seen:
                continue
            if _name_ratio(vp.name, target) >= NAME_MATCH_THRESHOLD:
                seen.add(vp.id)
                results.append((vp, "name_fuzzy"))
        if len(results) > 1:
            alt_method = "name_fuzzy"

    return results, alt_method


def compute_best_purchase(
    db: Session, job_id: int, report_currency: str | None = None
) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job not found")

    fx = load_fx_rates(db)
    requirements = db.scalars(
        select(JobRequirement)
        .where(
            JobRequirement.job_id == job_id,
            JobRequirement.vendor_product_id.isnot(None),
            JobRequirement.quantity_required > 0,
        )
        .order_by(JobRequirement.id)
    ).all()
    if not requirements:
        raise ValueError(
            "No vendor-linked requirements on this job. Link a vendor product to a "
            "requirement first, then run Best purchase."
        )

    lines: list[dict[str, Any]] = []
    currencies_seen: set[str] = set()

    for req in requirements:
        selected_vp = req.vendor_product
        if selected_vp is None:
            continue
        qty = req.quantity_required
        product: Product | None = req.product
        product_name = product.name if product else selected_vp.name

        matches, alt_method = _find_candidates(db, selected_vp)

        candidates: list[dict[str, Any]] = []
        for vp, method in matches:
            in_stock = _is_in_stock(vp)
            cur = (vp.currency or "").strip().upper() or None
            if cur:
                currencies_seen.add(cur)
            base_amount, fx_missing = convert(vp.unit_cost, vp.currency, fx, report_currency)
            candidates.append(
                {
                    "vendor_product_id": vp.id,
                    "vendor_id": vp.vendor_id,
                    "vendor_name": vp.vendor.name if isinstance(vp.vendor, Company) else None,
                    "sku": vp.sku,
                    "name": vp.name,
                    "unit_cost": float(vp.unit_cost) if vp.unit_cost is not None else None,
                    "currency": vp.currency,
                    "stock_quantity": vp.stock_quantity,
                    "availability": vp.availability,
                    "in_stock": in_stock,
                    "is_selected": vp.id == selected_vp.id,
                    "matched_by": method,
                    "converted_unit_cost": float(base_amount) if base_amount is not None else None,
                    "fx_missing": fx_missing,
                    "expected_delivery_date": (
                        vp.expected_delivery_date.isoformat() if vp.expected_delivery_date else None
                    ),
                    "incoming_quantity": vp.incoming_quantity,
                    "incoming_deliveries": vp.incoming_deliveries,
                }
            )

        restock_dates = [
            c["expected_delivery_date"] for c in candidates if c.get("expected_delivery_date")
        ]
        next_restock = min(restock_dates) if restock_dates else None

        lines.append(
            {
                "requirement_id": req.id,
                "product_id": req.product_id,
                "product_name": product_name,
                "qty": qty,
                "selected_vendor_product_id": selected_vp.id,
                "matched_by": alt_method or "selected",
                "candidates": candidates,
                "next_restock_date": next_restock,
            }
        )

    # Decide the report currency: explicit > single distinct currency > FX base.
    distinct_currencies = {c for c in currencies_seen if c}
    if report_currency:
        report_currency = report_currency.strip().upper()
    elif len(distinct_currencies) == 1:
        report_currency = next(iter(distinct_currencies))
    else:
        report_currency = ((fx or {}).get("base") or DEFAULT_BASE).upper()

    # Re-run conversion now that report_currency is fixed (affects single-currency case).
    for line in lines:
        for c in line["candidates"]:
            base_amount, fx_missing = convert(c["unit_cost"], c["currency"], fx, report_currency)
            c["converted_unit_cost"] = float(base_amount) if base_amount is not None else None
            c["fx_missing"] = fx_missing

    single_supplier = _recommend_single_supplier(lines)
    multi_supplier = _recommend_multi_supplier(lines)

    return {
        "job_id": job_id,
        "report_currency": report_currency,
        "fx_base": (fx or {}).get("base", DEFAULT_BASE),
        "lines": lines,
        "single_supplier": single_supplier,
        "multi_supplier": multi_supplier,
    }


def _recommend_single_supplier(lines: list[dict[str, Any]]) -> dict[str, Any] | None:
    vendor_ids = sorted(
        {c["vendor_id"] for line in lines for c in line["candidates"] if c["vendor_id"]}
    )
    candidates: list[dict[str, Any]] = []
    for vid in vendor_ids:
        total = Decimal(0)
        covered = 0
        unmet: list[str] = []
        for line in lines:
            opts = [
                c
                for c in line["candidates"]
                if c["vendor_id"] == vid and c["in_stock"] and c["converted_unit_cost"] is not None
            ]
            if not opts:
                unmet.append(line["product_name"])
                continue
            best = min(opts, key=lambda c: c["converted_unit_cost"])
            total += Decimal(str(best["converted_unit_cost"])) * line["qty"]
            covered += 1
        vendor_name = next(
            (
                c["vendor_name"]
                for line in lines
                for c in line["candidates"]
                if c["vendor_id"] == vid
            ),
            None,
        )
        candidates.append(
            {
                "vendor_id": vid,
                "vendor_name": vendor_name,
                "total": float(total.quantize(Decimal("0.01"))),
                "lines_covered": covered,
                "total_lines": len(lines),
                "unmet_lines": unmet,
            }
        )

    if not candidates:
        return None
    candidates.sort(key=lambda v: (-v["lines_covered"], v["total"]))
    return candidates[0]


def _recommend_multi_supplier(lines: list[dict[str, Any]]) -> dict[str, Any]:
    multi_total = Decimal(0)
    basket: list[dict[str, Any]] = []
    unmet: list[str] = []
    supplier_ids: set[int | None] = set()

    for line in lines:
        opts = [
            c
            for c in line["candidates"]
            if c["in_stock"] and c["converted_unit_cost"] is not None
        ]
        if not opts:
            unmet.append(line["product_name"])
            continue
        best = min(opts, key=lambda c: c["converted_unit_cost"])
        line_total = (Decimal(str(best["converted_unit_cost"])) * line["qty"]).quantize(
            Decimal("0.01")
        )
        multi_total += line_total
        supplier_ids.add(best["vendor_id"])
        basket.append(
            {
                "vendor_id": best["vendor_id"],
                "vendor_name": best["vendor_name"],
                "vendor_product_id": best["vendor_product_id"],
                "requirement_id": line["requirement_id"],
                "product_id": line["product_id"],
                "product_name": line["product_name"],
                "qty": line["qty"],
                "unit_cost": best["unit_cost"],
                "currency": best["currency"],
                "converted_unit_cost": best["converted_unit_cost"],
                "line_total": float(line_total),
            }
        )

    return {
        "total": float(multi_total.quantize(Decimal("0.01"))),
        "supplier_count": len({s for s in supplier_ids if s is not None}),
        "unmet_lines": unmet,
        "basket": basket,
    }


def _make_draft_line(line: dict[str, Any], cand: dict[str, Any], line_total: Decimal) -> PurchaseDraftLine:
    return PurchaseDraftLine(
        vendor_id=cand["vendor_id"],
        vendor_product_id=cand["vendor_product_id"],
        requirement_id=line["requirement_id"],
        product_id=line["product_id"],
        vendor_name=cand["vendor_name"],
        product_name=line["product_name"],
        qty=line["qty"],
        unit_cost=Decimal(str(cand["unit_cost"])) if cand["unit_cost"] is not None else None,
        currency=cand["currency"],
        converted_unit_cost=(
            Decimal(str(cand["converted_unit_cost"])) if cand["converted_unit_cost"] is not None else None
        ),
        line_total=line_total,
        is_selected_cheapest=True,
    )


def create_purchase_draft(
    db: Session, job_id: int, result: dict[str, Any], strategy: str = "multi"
) -> PurchaseDraft:
    """Persist the recommended basket as a purchase draft (PO draft)."""
    draft = PurchaseDraft(job_id=job_id, report_currency=result["report_currency"])
    total = Decimal(0)

    if strategy == "single" and result.get("single_supplier"):
        ss = result["single_supplier"]
        vid = ss["vendor_id"]
        unmet = ss["unmet_lines"]
        for line in result["lines"]:
            opts = [
                c
                for c in line["candidates"]
                if c["vendor_id"] == vid and c["in_stock"] and c["converted_unit_cost"] is not None
            ]
            if not opts:
                continue
            best = min(opts, key=lambda c: c["converted_unit_cost"])
            line_total = (Decimal(str(best["converted_unit_cost"])) * line["qty"]).quantize(
                Decimal("0.01")
            )
            total += line_total
            draft.lines.append(_make_draft_line(line, best, line_total))
        draft.total_base = total.quantize(Decimal("0.01"))
        draft.supplier_count = 1
        draft.meta_json = json.dumps({"strategy": "single", "unmet_lines": unmet})
    else:
        for b in result["multi_supplier"]["basket"]:
            line_total = Decimal(str(b["line_total"]))
            total += line_total
            draft.lines.append(
                PurchaseDraftLine(
                    vendor_id=b["vendor_id"],
                    vendor_product_id=b["vendor_product_id"],
                    requirement_id=b["requirement_id"],
                    product_id=b["product_id"],
                    vendor_name=b["vendor_name"],
                    product_name=b["product_name"],
                    qty=b["qty"],
                    unit_cost=Decimal(str(b["unit_cost"])) if b["unit_cost"] is not None else None,
                    currency=b["currency"],
                    converted_unit_cost=(
                        Decimal(str(b["converted_unit_cost"]))
                        if b["converted_unit_cost"] is not None
                        else None
                    ),
                    line_total=line_total,
                    is_selected_cheapest=True,
                )
            )
        draft.total_base = total.quantize(Decimal("0.01"))
        draft.supplier_count = result["multi_supplier"]["supplier_count"]
        draft.meta_json = json.dumps(
            {
                "strategy": "multi",
                "unmet_lines": result["multi_supplier"]["unmet_lines"],
                "single_supplier": result.get("single_supplier"),
            }
        )

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


# --------------------------------------------------------------------------- #
# Purchase orders
# --------------------------------------------------------------------------- #

PO_SEQUENCE_KEY = "po_sequence"


def next_po_number(db: Session) -> str:
    """Return the next purchase-order number, e.g. ``PO-000123``."""
    setting = db.scalar(select(AppSetting).where(AppSetting.key == PO_SEQUENCE_KEY))
    if setting is None:
        setting = AppSetting(key=PO_SEQUENCE_KEY, value_json="0")
        db.add(setting)
    try:
        n = int(setting.value_json or "0") + 1
    except (ValueError, TypeError):
        n = 1
    setting.value_json = str(n)
    db.commit()
    return f"PO-{n:06d}"


def _collect_job_buy_lines(db: Session, job_ids: list[int]) -> list[dict[str, Any]]:
    """Aggregate vendor-linked buy requirements across the given jobs."""
    lines: list[dict[str, Any]] = []
    for job_id in job_ids:
        job = db.get(Job, job_id)
        if job is None:
            continue
        reqs = db.scalars(
            select(JobRequirement)
            .where(
                JobRequirement.job_id == job_id,
                JobRequirement.vendor_product_id.isnot(None),
                JobRequirement.quantity_required > 0,
            )
            .order_by(JobRequirement.id)
        ).all()
        for req in reqs:
            vp: VendorProduct | None = req.vendor_product
            if vp is None:
                continue
            lines.append(
                {
                    "vendor_id": vp.vendor_id,
                    "vendor_product_id": vp.id,
                    "product_id": req.product_id,
                    "requirement_id": req.id,
                    "job_id": job.id,
                    "description": None,
                    "sku": vp.sku,
                    "name": vp.name,
                    "qty": req.quantity_required,
                    "unit_cost": vp.unit_cost,
                    "currency": vp.currency,
                    "is_manual": False,
                    "is_restock": False,
                }
            )
    return lines


def _collect_restock_lines(db: Session) -> list[dict[str, Any]]:
    products = db.scalars(select(Product)).all()
    lines: list[dict[str, Any]] = []
    for p in products:
        if p.min_stock_level is None:
            continue
        # Current stock is represented by Device records for this product.
        current = db.scalar(
            select(func.count(Device.id)).where(Device.product_id == p.id)
        ) or 0
        if current >= p.min_stock_level:
            continue
        ps = db.scalars(
            select(ProductSupplier)
            .where(
                ProductSupplier.product_id == p.id,
                ProductSupplier.is_primary.is_(True),
            )
            .order_by(ProductSupplier.id)
        ).first()
        if ps is None:
            ps = db.scalars(
                select(ProductSupplier)
                .where(ProductSupplier.product_id == p.id)
                .order_by(ProductSupplier.id)
            ).first()
        vendor_company_id = ps.supplier_company_id if ps else None
        # Products that only have a vendor-catalog match (e.g. imported from a
        # scraper) may lack a ProductSupplier row; fall back to the vendor
        # catalog item's vendor so they can still be restocked.
        vp = _resolve_vendor_product_for_product(db, p)
        if vendor_company_id is None and vp and vp.vendor_id:
            vendor_company_id = vp.vendor_id
        # If no Company resolves we can still restock using the linked Customer
        # as the named supplier, so the line is never silently dropped.
        supplier_name = None
        if vendor_company_id is None and ps and ps.supplier_id:
            cust = db.get(Customer, ps.supplier_id)
            supplier_name = cust.name if cust else None
        if vendor_company_id is None and not supplier_name:
            continue
        qty = int(p.min_order_qty) if p.min_order_qty else 1
        needed = max(0, int(p.min_stock_level) - int(current))
        qty = max(qty, needed)
        # Resolve the matching vendor catalog item so the restock line carries
        # the supplier's actual unit cost and currency (ProductSupplier has no
        # currency of its own). Falls back to the supplier link's cost.
        unit_cost = (vp.unit_cost if vp and vp.unit_cost is not None else (ps.unit_cost if ps else None))
        currency = (vp.currency if vp and vp.currency else None)
        lines.append(
            {
                "vendor_id": vendor_company_id,
                "vendor_product_id": vp.id if vp else None,
                "product_id": p.id,
                "requirement_id": None,
                "job_id": None,
                "description": None,
                "sku": p.sku,
                "name": p.name,
                "qty": qty,
                "unit_cost": unit_cost,
                "currency": currency,
                "is_manual": False,
                "is_restock": True,
                "supplier_name": supplier_name,
            }
        )
    return lines


def _best_vendor_catalog_match(vps: list, product: "Any", name_match: bool = True) -> "Any | None":
    """Pick the best vendor catalog match for ``product`` by SKU, external
    reference, or exact (case-insensitive) name.

    When several candidates match a strategy, prefer one that carries a unit
    cost so an unlinked product still inherits a real price when there is a
    confident (exact) match available. ``name_match`` gates the name bucket so a
    coincidental name twin never prices a product with no supplier relationship.
    """
    buckets: list[list] = []
    if product.sku:
        buckets.append([vp for vp in vps if vp.sku and vp.sku == product.sku])
    if product.external_reference:
        buckets.append(
            [vp for vp in vps if vp.external_reference and vp.external_reference == product.external_reference]
        )
    if product.name and name_match:
        buckets.append(
            [vp for vp in vps if vp.name and vp.name.strip().lower() == product.name.strip().lower()]
        )
    for bucket in buckets:
        if not bucket:
            continue
        priced = [vp for vp in bucket if vp.unit_cost is not None]
        return priced[0] if priced else bucket[0]
    return None


def _resolve_vendor_product_for_product(
    db: Session, product: "Any"
) -> "Any | None":
    """Find a vendor catalog item (VendorProduct) that represents ``product``.

    Used to attach a restock/manual line's real unit cost and currency. Prefers
    the vendor catalog item explicitly linked through ``ProductSupplier`` (which
    is how scraper-linked products are associated), then falls back to an exact
    match on SKU, external reference, or name (preferring a priced item).
    """
    suppliers = db.scalars(
        select(ProductSupplier)
        .where(ProductSupplier.product_id == product.id)
        .order_by(ProductSupplier.is_primary.desc(), ProductSupplier.id)
    ).all()
    # Prefer any supplier that explicitly links to a vendor catalog item, not
    # just the primary one.
    for ps in suppliers:
        if ps.vendor_product_id:
            vp = db.get(VendorProduct, ps.vendor_product_id)
            if vp:
                return vp
    vps = db.scalars(select(VendorProduct).where(VendorProduct.is_active.is_(True))).all()
    return _best_vendor_catalog_match(vps, product, name_match=bool(suppliers))


def _fill_from_vendor_product(db: Session, vendor_product_id: "Any", fields: dict) -> dict:
    """Backfill supplier/price/currency/name/sku from a linked vendor catalog item.

    Used when a (restock/manual) line carries a ``vendor_product_id`` but is
    missing the supplier company, unit cost, currency, name or sku — so the PO
    line inherits the real catalog pricing instead of staying blank.
    """
    if not vendor_product_id:
        return fields
    vp = db.get(VendorProduct, vendor_product_id)
    if vp is None:
        return fields
    if fields.get("vendor_id") is None:
        fields["vendor_id"] = vp.vendor_id
    if fields.get("unit_cost") is None:
        fields["unit_cost"] = vp.unit_cost
    if fields.get("currency") is None:
        fields["currency"] = vp.currency
    if not fields.get("name"):
        fields["name"] = vp.name
    if not fields.get("sku"):
        fields["sku"] = vp.sku
    return fields


def _make_po(
    db: Session,
    supplier_company_id: int | None,
    lines: list[dict[str, Any]],
    report_currency: str | None,
    meta: dict[str, Any],
    freight_overrides: dict[int, float] | None = None,
) -> PurchaseOrder:
    fx = load_fx_rates(db)
    currencies = {l["currency"] for l in lines if l.get("currency")}
    if report_currency:
        report_currency = report_currency.strip().upper()
    elif len(currencies) == 1:
        report_currency = next(iter(currencies))
    else:
        report_currency = ((fx or {}).get("base") or DEFAULT_BASE).upper()

    supplier_name = None
    comp = None
    if supplier_company_id:
        comp = db.get(Company, supplier_company_id)
        supplier_name = comp.name if comp else None
    # Fall back to a carried supplier name for vendor-less restock/manual lines
    # (e.g. a product only linked to a Customer, not a Company).
    if not supplier_name:
        supplier_name = next(
            (l.get("supplier_name") for l in lines if l.get("supplier_name")), None
        )
    po = PurchaseOrder(
        po_number=next_po_number(db),
        supplier_company_id=supplier_company_id,
        status="draft",
        report_currency=report_currency,
        meta_json=json.dumps(meta, default=str),
    )
    po.supplier_name = supplier_name
    total = Decimal(0)
    for l in lines:
        line, line_total = _make_line(l, fx, report_currency)
        if line_total is not None:
            total += line_total
        po.lines.append(line)

    # Freight: explicit override (in report currency) takes precedence, otherwise
    # fall back to the supplier's default shipping cost converted to base.
    freight_base = Decimal(0)
    if supplier_company_id and freight_overrides and supplier_company_id in freight_overrides:
        freight_base = Decimal(str(freight_overrides[supplier_company_id]))
    elif comp is not None and comp.freight_cost is not None:
        fconv, _ = convert(comp.freight_cost, comp.freight_currency, fx, report_currency)
        freight_base = fconv if fconv is not None else Decimal(str(comp.freight_cost))
    po.total_base = total.quantize(Decimal("0.01"))
    po.freight_base = freight_base.quantize(Decimal("0.0001"))
    po.freight_cost = freight_base.quantize(Decimal("0.01"))
    po.freight_currency = report_currency
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


def _make_line(
    l: dict[str, Any], fx: dict[str, Any] | None, report_currency: str
) -> tuple[PurchaseOrderLine, Decimal | None]:
    """Build a ``PurchaseOrderLine`` and its base-currency total from a line dict."""
    unit = l.get("unit_cost")
    conv, _ = convert(unit, l.get("currency"), fx, report_currency)
    # When FX conversion is unavailable, keep the line in its original currency
    # rather than silently folding the raw amount into the report currency.
    line_total = (conv * Decimal(l["qty"])) if conv is not None else None
    line = PurchaseOrderLine(
        vendor_id=l["vendor_id"],
        vendor_product_id=l["vendor_product_id"],
        product_id=l["product_id"],
        requirement_id=l["requirement_id"],
        job_id=l["job_id"],
        description=l.get("description"),
        sku=l.get("sku"),
        name=l.get("name"),
        qty=l["qty"],
        unit_cost=Decimal(str(unit)) if unit is not None else None,
        currency=l.get("currency"),
        converted_unit_cost=conv,
        line_total=line_total,
        is_manual=l.get("is_manual", False),
        is_restock=l.get("is_restock", False),
    )
    return line, line_total


def create_pos_from_draft(db: Session, draft_id: int) -> list[PurchaseOrder]:
    draft = db.get(PurchaseDraft, draft_id)
    if draft is None:
        raise ValueError("Purchase draft not found")
    if not draft.lines:
        raise ValueError("Draft has no lines")
    grouped: dict[int, list[dict[str, Any]]] = {}
    for dl in draft.lines:
        supplier = dl.vendor_id
        grouped.setdefault(supplier, []).append(
            {
                "vendor_id": dl.vendor_id,
                "vendor_product_id": dl.vendor_product_id,
                "product_id": dl.product_id,
                "requirement_id": dl.requirement_id,
                "job_id": None,
                "description": None,
                "sku": None,
                "name": dl.product_name,
                "qty": dl.qty,
                "unit_cost": dl.unit_cost,
                "currency": dl.currency,
                "is_manual": False,
                "is_restock": False,
            }
        )
    pos: list[PurchaseOrder] = []
    for supplier, lines in grouped.items():
        pos.append(
            _make_po(
                db,
                supplier,
                lines,
                draft.report_currency,
                {"source": "draft", "draft_id": draft.id},
            )
        )
    return pos


def create_combined_pos(
    db: Session,
    job_ids: list[int],
    include_restock: bool = False,
    extra_items: list[Any] | None = None,
) -> list[PurchaseOrder]:
    extra_items = extra_items or []
    lines = _collect_job_buy_lines(db, job_ids)
    if include_restock:
        lines.extend(_collect_restock_lines(db))
    for item in extra_items:
        if not item.vendor_company_id and not item.vendor_product_id:
            raise ValueError("Manual items must specify a vendor or a vendor product")
        fields = {
            "vendor_id": item.vendor_company_id,
            "vendor_product_id": item.vendor_product_id,
            "product_id": item.product_id,
            "name": item.name,
            "sku": item.sku,
            "unit_cost": Decimal(str(item.unit_cost)) if item.unit_cost is not None else None,
            "currency": item.currency,
        }
        fields = _fill_from_vendor_product(db, item.vendor_product_id, fields)
        lines.append(
            {
                "vendor_id": fields["vendor_id"],
                "vendor_product_id": item.vendor_product_id,
                "product_id": item.product_id,
                "requirement_id": None,
                "job_id": None,
                "description": item.description,
                "sku": fields.get("sku"),
                "name": fields.get("name") or item.name,
                "qty": item.qty,
                "unit_cost": fields.get("unit_cost"),
                "currency": fields.get("currency"),
                "is_manual": True,
                "is_restock": False,
            }
        )
    if not lines:
        raise ValueError("Nothing to order: no vendor-linked requirements, restock items or manual items")

    grouped: dict[int, list[dict[str, Any]]] = {}
    for l in lines:
        grouped.setdefault(l["vendor_id"], []).append(l)

    pos: list[PurchaseOrder] = []
    for supplier, group in grouped.items():
        pos.append(
            _make_po(
                db,
                supplier,
                group,
                None,
                {
                    "source": "combined",
                    "job_ids": job_ids,
                    "include_restock": include_restock,
                    "manual_items": len(extra_items),
                },
            )
        )
    return pos


def preview_purchase_lines(
    db: Session, job_ids: list[int], include_restock: bool = False
) -> dict[str, Any]:
    """Return proposed order lines with alternative supplier candidates.

    Each job requirement yields one entry listing every matching vendor product
    (the selected one plus alternatives found by EAN or fuzzy name) so the UI can
    let the user pick which supplier to order each item from.
    """
    fx = load_fx_rates(db)
    result: list[dict[str, Any]] = []
    for job_id in job_ids:
        job = db.get(Job, job_id)
        if job is None:
            continue
        reqs = db.scalars(
            select(JobRequirement)
            .where(
                JobRequirement.job_id == job_id,
                JobRequirement.vendor_product_id.isnot(None),
                JobRequirement.quantity_required > 0,
            )
            .order_by(JobRequirement.id)
        ).all()
        for req in reqs:
            vp: VendorProduct | None = req.vendor_product
            if vp is None:
                continue
            matches, _ = _find_candidates(db, vp)
            candidates: list[dict[str, Any]] = []
            for m, method in matches:
                base_amt, fx_missing = convert(m.unit_cost, m.currency, fx, None)
                candidates.append(
                    {
                        "vendor_product_id": m.id,
                        "vendor_id": m.vendor_id,
                        "vendor_name": m.vendor.name if isinstance(m.vendor, Company) else None,
                        "name": m.name,
                        "sku": m.sku,
                        "unit_cost": float(m.unit_cost) if m.unit_cost is not None else None,
                        "currency": m.currency,
                        "in_stock": _is_in_stock(m),
                        "stock_quantity": m.stock_quantity,
                        "converted_unit_cost": float(base_amt) if base_amt is not None else None,
                        "fx_missing": fx_missing,
                        "matched_by": method,
                        "is_selected": m.id == vp.id,
                        "expected_delivery_date": (
                            m.expected_delivery_date.isoformat() if m.expected_delivery_date else None
                        ),
                        "incoming_quantity": m.incoming_quantity,
                        "incoming_deliveries": m.incoming_deliveries,
                    }
                )
            restock_dates = [
                c["expected_delivery_date"] for c in candidates if c.get("expected_delivery_date")
            ]
            next_restock = min(restock_dates) if restock_dates else None

            result.append(
                {
                    "requirement_id": req.id,
                    "job_id": job.id,
                    "product_id": req.product_id,
                    "product_name": req.product.name if req.product else vp.name,
                    "qty": req.quantity_required,
                    "selected_vendor_product_id": vp.id,
                    "next_restock_date": next_restock,
                    "candidates": candidates,
                }
            )
    if include_restock:
        for r in _collect_restock_lines(db):
            result.append(
                {
                    "requirement_id": None,
                    "job_id": None,
                    "product_id": r["product_id"],
                    "product_name": r["name"],
                    "qty": r["qty"],
                    "selected_vendor_product_id": r["vendor_product_id"],
                    "is_restock": True,
                    "next_restock_date": None,
                    "candidates": [
                        {
                            "vendor_product_id": r["vendor_product_id"],
                            "vendor_id": r["vendor_id"],
                            "vendor_name": (
                                db.get(Company, r["vendor_id"]).name
                                if r["vendor_id"] else None
                            ),
                            "name": r["name"],
                            "sku": r["sku"],
                            "unit_cost": float(r["unit_cost"]) if r["unit_cost"] is not None else None,
                            "currency": r["currency"],
                            "in_stock": True,
                            "stock_quantity": None,
                            "converted_unit_cost": (
                                float(r["unit_cost"]) if r["unit_cost"] is not None else None
                            ),
                            "fx_missing": False,
                            "matched_by": "restock",
                            "is_selected": True,
                        }
                    ],
                }
            )
    currencies_seen = {
        c["currency"] for r in result for c in r.get("candidates", []) if c.get("currency")
    }
    if len(currencies_seen) == 1:
        report_currency = next(iter(currencies_seen))
    elif fx and fx.get("base"):
        report_currency = fx["base"]
    elif currencies_seen:
        report_currency = next(iter(currencies_seen))
    else:
        report_currency = None

    # Candidates were first converted against the FX base; re-convert them against
    # the chosen report currency so all displayed amounts share one base.
    for line in result:
        for c in line.get("candidates", []):
            conv, fx_missing = convert(c["unit_cost"], c["currency"], fx, report_currency)
            c["converted_unit_cost"] = float(conv) if conv is not None else None
            c["fx_missing"] = fx_missing

    # Freight per supplier (in the report currency) so the suggestion engine can
    # compare single-supplier vs multi-supplier baskets including shipping.
    freight: dict[int, dict[str, Any]] = {}
    vendor_ids = {
        c["vendor_id"] for r in result for c in r.get("candidates", []) if c.get("vendor_id")
    }
    for vid in vendor_ids:
        comp = db.get(Company, vid)
        if comp is None:
            continue
        fconv = None
        if comp.freight_cost is not None:
            fconv, _ = convert(comp.freight_cost, comp.freight_currency, fx, report_currency)
        freight[vid] = {
            "cost": float(comp.freight_cost) if comp.freight_cost is not None else None,
            "currency": comp.freight_currency,
            "base": float(fconv) if fconv is not None else None,
        }
    return {"report_currency": report_currency, "lines": result, "freight": freight}


def _resolve_selection_line(
    db: Session, requirement_id: int, vendor_product_id: int, qty: int | None
) -> dict[str, Any]:
    req = db.get(JobRequirement, requirement_id)
    if req is None:
        raise ValueError(f"Requirement {requirement_id} not found")
    vp = db.get(VendorProduct, vendor_product_id)
    if vp is None:
        raise ValueError(f"Vendor product {vendor_product_id} not found")
    return {
        "vendor_id": vp.vendor_id,
        "vendor_product_id": vp.id,
        "product_id": req.product_id,
        "requirement_id": req.id,
        "job_id": req.job_id,
        "description": None,
        "sku": vp.sku,
        "name": vp.name,
        "qty": qty or req.quantity_required,
        "unit_cost": vp.unit_cost,
        "currency": vp.currency,
        "is_manual": False,
        "is_restock": False,
    }


def build_purchase_orders(
    db: Session,
    lines: list[dict[str, Any]],
    extra_items: list[Any] | None = None,
    include_restock: bool = False,
    freight: dict[int, float] | None = None,
) -> list[PurchaseOrder]:
    """Create one PO per supplier from explicit per-line supplier selections."""
    extra_items = extra_items or []
    resolved: list[dict[str, Any]] = []
    for sel in lines:
        resolved.append(
            _resolve_selection_line(
                db, sel["requirement_id"], sel["vendor_product_id"], sel.get("qty")
            )
        )
    if include_restock:
        resolved.extend(_collect_restock_lines(db))
    for item in extra_items:
        supplier_name = getattr(item, "supplier_name", None)
        if not item.vendor_company_id and not item.vendor_product_id and not supplier_name:
            raise ValueError("Manual items must specify a vendor or a vendor product")
        resolved.append(
            {
                "vendor_id": item.vendor_company_id,
                "vendor_product_id": item.vendor_product_id,
                "product_id": item.product_id,
                "requirement_id": None,
                "job_id": None,
                "description": item.description,
                "sku": item.sku,
                "name": item.name,
                "qty": item.qty,
                "unit_cost": Decimal(str(item.unit_cost)) if item.unit_cost is not None else None,
                "currency": item.currency,
                "is_manual": not getattr(item, "is_restock", False),
                "is_restock": bool(getattr(item, "is_restock", False)),
                "supplier_name": supplier_name,
            }
        )
    if not resolved:
        raise ValueError("Nothing to order")
    grouped: dict[tuple, list[dict[str, Any]]] = {}
    for l in resolved:
        grouped.setdefault((l["vendor_id"], l.get("supplier_name")), []).append(l)
    pos: list[PurchaseOrder] = []
    for (vendor_id, _sname), group in grouped.items():
        pos.append(
            _make_po(
                db,
                vendor_id,
                group,
                None,
                {"source": "build", "manual_items": len(extra_items), "include_restock": include_restock},
                freight_overrides=freight,
            )
        )
    return pos


def create_pos_from_job(
    db: Session,
    job_id: int,
    selections: list[dict[str, Any]] | None = None,
) -> list[PurchaseOrder]:
    """Create PO(s) directly from a job's vendor-linked requirements.

    When ``selections`` is provided (a list of ``{requirement_id,
    vendor_product_id, qty}``) it overrides which supplier each line is ordered
    from; otherwise the requirement's already-linked vendor product is used.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job not found")
    if selections:
        return build_purchase_orders(db, selections)
    reqs = db.scalars(
        select(JobRequirement)
        .where(
            JobRequirement.job_id == job_id,
            JobRequirement.vendor_product_id.isnot(None),
            JobRequirement.quantity_required > 0,
        )
        .order_by(JobRequirement.id)
    ).all()
    if not reqs:
        raise ValueError("Job has no vendor-linked requirements")
    selected = [
        {
            "requirement_id": req.id,
            "vendor_product_id": req.vendor_product_id,
            "qty": req.quantity_required,
        }
        for req in reqs
    ]
    return build_purchase_orders(db, selected)


def add_lines_to_po(
    db: Session,
    po_id: int,
    lines: list[dict[str, Any]],
    extra_items: list[Any] | None = None,
    freight: dict[int, float] | None = None,
) -> PurchaseOrder:
    """Append lines (and optional manual items) to an existing draft PO.

    All added lines must belong to the PO's supplier; if a selected supplier
    differs the call is rejected so a PO never mixes suppliers.
    """
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise ValueError("Purchase order not found")
    if po.status not in OPEN_PO_STATUSES:
        raise ValueError("Can only add lines to a draft or partial PO")

    extra_items = extra_items or []
    resolved: list[dict[str, Any]] = []
    for sel in lines:
        resolved.append(
            _resolve_selection_line(
                db, sel["requirement_id"], sel["vendor_product_id"], sel.get("qty")
            )
        )
    for item in extra_items:
        if not item.vendor_company_id and not item.vendor_product_id:
            raise ValueError("Manual items must specify a vendor or a vendor product")
        fields = {
            "vendor_id": item.vendor_company_id,
            "vendor_product_id": item.vendor_product_id,
            "product_id": item.product_id,
            "name": item.name,
            "sku": item.sku,
            "unit_cost": Decimal(str(item.unit_cost)) if item.unit_cost is not None else None,
            "currency": item.currency,
        }
        fields = _fill_from_vendor_product(db, item.vendor_product_id, fields)
        resolved.append(
            {
                "vendor_id": fields["vendor_id"],
                "vendor_product_id": item.vendor_product_id,
                "product_id": item.product_id,
                "requirement_id": None,
                "job_id": None,
                "description": item.description,
                "sku": fields.get("sku"),
                "name": fields.get("name") or item.name,
                "qty": item.qty,
                "unit_cost": fields.get("unit_cost"),
                "currency": fields.get("currency"),
                "is_manual": not getattr(item, "is_restock", False),
                "is_restock": bool(getattr(item, "is_restock", False)),
            }
        )
    for l in resolved:
        if l["vendor_id"] != po.supplier_company_id:
            raise ValueError(
                "All added lines must come from the PO's supplier "
                f"({po.supplier_company_id}); got supplier {l['vendor_id']}"
            )

    fx = load_fx_rates(db)
    total = po.total_base or Decimal(0)
    for l in resolved:
        line, line_total = _make_line(l, fx, po.report_currency)
        po.lines.append(line)
        if line_total is not None:
            total += line_total
    po.total_base = total.quantize(Decimal("0.01"))

    freight_base = po.freight_base or Decimal(0)
    supplier = po.supplier_company_id
    if supplier is not None and freight and supplier in freight:
        freight_base = Decimal(str(freight[supplier]))
    elif supplier is not None and po.freight_base in (None, Decimal(0)):
        comp = db.get(Company, supplier)
        if comp is not None and comp.freight_cost is not None:
            fconv, _ = convert(comp.freight_cost, comp.freight_currency, fx, po.report_currency)
            freight_base = fconv if fconv is not None else Decimal(str(comp.freight_cost))
    po.freight_base = freight_base.quantize(Decimal("0.0001"))
    po.freight_cost = freight_base.quantize(Decimal("0.01"))
    po.freight_currency = po.report_currency
    db.commit()
    db.refresh(po)
    return po


def _line_creates_device(db: Session, line) -> bool:
    """Whether receiving a PO line should mint individual Device records.

    A line becomes a tracked device when it has a linked warehouse product and
    is not sourced from a non-scannable (sale) job requirement. Sale articles
    (no linked product, or a sale requirement) are received into stock without
    creating Device rows.
    """
    if not line.product_id:
        return False
    if line.requirement_id is not None:
        req = db.get(JobRequirement, line.requirement_id)
        if req is not None and req.is_scannable is False:
            return False
    return True


def receive_po(db: Session, po_id: int, items: list) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise ValueError("Purchase order not found")
    if po.status == "received":
        raise ValueError("Purchase order already fully received")

    supplier_name = None
    if po.supplier_company_id:
        comp = db.get(Company, po.supplier_company_id)
        supplier_name = comp.name if comp else None

    requested = {int(item.line_id): item for item in items}
    today = datetime.now(UTC).date()
    for line in po.lines:
        if line.id not in requested:
            continue
        item = requested[line.id]
        target = max(0, min(int(item.received_qty), line.qty))
        # Never decrease the received count: a smaller value would desync the
        # recorded received_qty from already-minted Device/stock records.
        target = max(target, line.received_qty)
        delta = target - line.received_qty
        line.received_qty = target
        # Sale-article lines are received without minting Device records, but
        # any captured serial numbers are still recorded against the line so
        # they stay attached to the originating job.
        if item.serials:
            existing = list(line.serials or [])
            for s in item.serials:
                if s and s not in existing:
                    existing.append(s)
            line.serials = existing
        if delta <= 0:
            continue
        if not _line_creates_device(db, line):
            # Sale article (no linked product, or sourced from a non-scannable
            # job requirement): received into stock without Device records.
            continue
        # Stock is represented by Device records; receiving creates one device
        # per provided unit spec. When no per-unit specs are supplied
        # (legacy path) we auto-fill one device per received unit.
        specs = item.devices
        if specs is None:
            specs = [None] * delta
        elif 0 < len(specs) < delta:
            # Caller supplied some per-unit specs but fewer than delta: pad so
            # every received unit gets a Device and stock can never desync from
            # the recorded received quantity. An explicitly empty list ([]) still
            # means "no devices" (e.g. a non-scannable / sale article).
            specs = list(specs) + [None] * (delta - len(specs))
        for i in range(min(delta, len(specs))):
            spec = specs[i]
            asset_tag = (
                spec.asset_tag
                if spec and spec.asset_tag
                else f"{po.po_number}-{line.id}-{target}-{i + 1}"[:64]
            )
            db.add(
                Device(
                    product_id=line.product_id,
                    asset_tag=asset_tag,
                    serial_number=spec.serial_number if spec else None,
                    barcode=spec.barcode if spec else None,
                    status=spec.status if spec and spec.status else (item.default_status or "available"),
                    condition=spec.condition if spec and spec.condition else (item.default_condition or "new"),
                    location_zone_id=spec.location_zone_id if spec else item.default_location_zone_id,
                    purchase_date=item.purchase_date or today,
                    purchase_price=spec.purchase_price if spec and spec.purchase_price is not None else line.unit_cost,
                    purchased_from=supplier_name,
                    supplier_id=None,
                    notes=spec.notes if spec else item.notes,
                )
            )

    if all(l.received_qty >= l.qty for l in po.lines):
        po.status = "received"
    else:
        po.status = "partial"
    db.commit()
    db.refresh(po)
    return po


def recompute_po_line(db: Session, line: "PurchaseOrderLine", po: "PurchaseOrder") -> None:
    """Recompute a line's converted cost and total after an edit."""
    fx = load_fx_rates(db)
    conv, _ = convert(line.unit_cost, line.currency, fx, po.report_currency)
    line.converted_unit_cost = conv
    line.line_total = (conv * Decimal(line.qty)) if conv is not None else None


def recompute_po_totals(po: "PurchaseOrder") -> None:
    total = Decimal(0)
    for ln in po.lines:
        if ln.line_total is not None:
            total += Decimal(str(ln.line_total))
    po.total_base = total.quantize(Decimal("0.01"))


def update_po_line(
    db: Session, po_id: int, line_id: int, req: "POLineUpdateRequest"
) -> PurchaseOrderLine:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise ValueError("Purchase order not found")
    line = db.get(PurchaseOrderLine, line_id)
    if line is None or line.po_id != po.id:
        raise ValueError("Purchase order line not found")
    if line.received_qty and line.received_qty > 0:
        raise ValueError("Cannot edit a line that has already been received")
    if req.qty is not None:
        line.qty = max(1, int(req.qty))
    if req.unit_cost is not None:
        line.unit_cost = Decimal(str(req.unit_cost))
    if req.currency is not None:
        line.currency = req.currency.strip().upper() or None
    if req.name is not None:
        line.name = req.name or None
    if req.description is not None:
        line.description = req.description or None
    if req.sku is not None:
        line.sku = req.sku or None
    recompute_po_line(db, line, po)
    recompute_po_totals(po)
    db.commit()
    db.refresh(line)
    return line


def delete_po_line(db: Session, po_id: int, line_id: int) -> None:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise ValueError("Purchase order not found")
    line = db.get(PurchaseOrderLine, line_id)
    if line is None or line.po_id != po.id:
        raise ValueError("Purchase order line not found")
    if line.received_qty and line.received_qty > 0:
        raise ValueError("Cannot delete a line that has already been received")
    db.delete(line)
    recompute_po_totals(po)
    db.commit()
