"""
Tool definitions and execution handlers for the AI assistant.

Tools are defined in OpenAI function-calling format and executed
against the Stockwire database via SQLAlchemy.
"""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.customers.models import Company
from app.domain.inventory.availability import calculate_product_availability
from app.domain.inventory.models import (
    DefectReport,
    Device,
    InventoryAuditLog,
    InventoryCategory,
    Product,
    VendorProduct,
)
from app.domain.jobs.models import Job, JobRequirement

PRODUCT_TYPES = ["equipment", "accessory", "consumable", "case", "bundle", "rental"]
JOB_STATUSES = ["draft", "confirmed", "in_progress", "completed", "cancelled"]
DEVICE_STATUSES = ["in_store", "on_site", "maintenance", "damaged"]
DEFECT_SEVERITIES = ["low", "medium", "high", "critical"]

WRITE_TOOLS = {
    "update_product_manufacturer",
    "update_product_category",
    "batch_update_manufacturers",
    "add_item_to_job",
    "update_job_manifest",
    "create_customer",
    "update_customer",
    "flag_damaged_device",
    "update_device_status",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory_stock",
            "description": "Check availability and stock levels for a product. Always use the full product name or SKU code, not just a number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Full product name or SKU code (e.g. 'Pelican 1510' or 'EVT-001-12345')"},
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_date_range_availability",
            "description": "Check a product's minimum available stock across an inclusive date range, accounting for overlapping active jobs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Exact product name or SKU"},
                    "start_date": {"type": "string", "format": "date", "description": "First rental date (inclusive)"},
                    "end_date": {"type": "string", "format": "date", "description": "Last rental date (inclusive)"},
                },
                "required": ["item_name", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rental_rates",
            "description": "Get rental pricing for a product. Always use the full product name or SKU code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Full product name or SKU code (e.g. 'Pelican 1510' or 'EVT-001-12345')"},
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_customers",
            "description": "Search for customers or suppliers by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Name to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by name, category, or type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "category": {"type": "string", "description": "Filter by category name"},
                    "product_type": {"type": "string", "enum": PRODUCT_TYPES, "description": "Filter by product type"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_jobs",
            "description": "List recent jobs with optional status filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": JOB_STATUSES, "description": "Filter by job status"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "List all product categories in the inventory tree.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_manufacturer",
            "description": "Update the manufacturer for a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Full product name or SKU code"},
                    "manufacturer": {"type": "string", "description": "New manufacturer name"},
                },
                "required": ["item_name", "manufacturer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_category",
            "description": "Update the category for a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Full product name or SKU code"},
                    "category": {"type": "string", "description": "New category name"},
                },
                "required": ["item_name", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_update_manufacturers",
            "description": "Update manufacturer for multiple products at once. Useful for bulk categorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_names": {"type": "array", "items": {"type": "string"}, "description": "List of product names or SKUs"},
                    "manufacturer": {"type": "string", "description": "Manufacturer name to set"},
                },
                "required": ["product_names", "manufacturer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_manifest",
            "description": "Inspect job or quote line items, checked-out equipment, cases, and case contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_code": {"type": "string", "description": "Exact job code"},
                },
                "required": ["job_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_item_to_job",
            "description": "Add a product line item to a job or quote manifest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_code": {"type": "string", "description": "Exact job code"},
                    "item_name": {"type": "string", "description": "Exact product name or SKU"},
                    "quantity": {"type": "integer", "minimum": 1, "description": "Required quantity"},
                    "label": {"type": "string", "description": "Optional manifest line label"},
                    "notes": {"type": "string", "description": "Optional notes"},
                },
                "required": ["job_code", "item_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_job_manifest",
            "description": "Update or remove a job manifest line item by requirement ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_code": {"type": "string", "description": "Exact job code"},
                    "requirement_id": {"type": "integer", "description": "Manifest line item ID"},
                    "action": {"type": "string", "enum": ["update", "remove"]},
                    "quantity": {"type": "integer", "minimum": 1, "description": "New required quantity for update"},
                    "label": {"type": "string", "description": "Replacement line label"},
                    "notes": {"type": "string", "description": "Replacement line notes"},
                },
                "required": ["job_code", "requirement_id", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_customer",
            "description": "Create a customer company record with contact and address details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "city": {"type": "string"},
                    "postal_code": {"type": "string"},
                    "country": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer",
            "description": "Update a customer's company and contact details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "city": {"type": "string"},
                    "postal_code": {"type": "string"},
                    "country": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_damaged_device",
            "description": "Report damage to a device by serial number or asset tag and mark it as damaged and under maintenance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Exact device serial number or asset tag"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": DEFECT_SEVERITIES},
                },
                "required": ["identifier", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_device_status",
            "description": "Change a device's operational state by serial number or asset tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Exact device serial number or asset tag"},
                    "status": {"type": "string", "enum": DEVICE_STATUSES},
                },
                "required": ["identifier", "status"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool call and return the result as a dict."""
    handlers = {
        "check_inventory_stock": _check_stock,
        "check_date_range_availability": _check_date_range_availability,
        "get_rental_rates": _get_rates,
        "list_customers": _list_customers,
        "search_products": _search_products,
        "list_jobs": _list_jobs,
        "list_categories": _list_categories,
        "update_product_manufacturer": _update_manufacturer,
        "update_product_category": _update_category,
        "batch_update_manufacturers": _batch_update_manufacturers,
        "get_job_manifest": _get_job_manifest,
        "add_item_to_job": _add_item_to_job,
        "update_job_manifest": _update_job_manifest,
        "create_customer": _create_customer,
        "update_customer": _update_customer,
        "flag_damaged_device": _flag_damaged_device,
        "update_device_status": _update_device_status,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(arguments, db)
    except Exception as e:  # noqa: BLE001 - tool handlers can fail outside SQLAlchemy.
        try:
            db.rollback()
        except SQLAlchemyError as rollback_error:
            return {"error": f"{e}; database rollback failed: {rollback_error}"}
        return {"error": str(e)}


def _find_product(query: str, db: Session) -> Product | None:
    value = query.strip()
    if not value:
        return None

    sku_match = db.scalar(select(Product).where(Product.sku == value))
    if sku_match:
        return sku_match

    exact_matches = db.scalars(
        select(Product)
        .where(Product.name.ilike(value))
        .order_by(Product.name, Product.sku)
        .limit(2)
    ).all()
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise _ambiguous_product_error(value, exact_matches)

    partial_matches = db.scalars(
        select(Product)
        .where(or_(Product.name.ilike(f"%{value}%"), Product.sku.ilike(f"%{value}%")))
        .order_by(Product.name, Product.sku)
        .limit(6)
    ).all()
    if len(partial_matches) == 1:
        return partial_matches[0]
    if len(partial_matches) > 1:
        raise _ambiguous_product_error(value, partial_matches)
    return None


def _ambiguous_product_error(query: str, products: Sequence[Product]) -> ValueError:
    examples = ", ".join(
        f"{product.name} (SKU: {product.sku})" for product in products[:5]
    )
    suffix = " and more" if len(products) > 5 else ""
    return ValueError(
        f"Multiple products match '{query}': {examples}{suffix}. Please specify exact SKU."
    )


def _check_stock(args: dict, db: Session) -> dict:
    item_name = args.get("item_name", "")
    product = _find_product(item_name, db)
    if not product:
        return {"error": f"Product not found: {item_name}"}
    total_devices = db.scalar(
        select(func.count()).select_from(Device).where(Device.product_id == product.id)
    ) or 0
    in_store_devices = db.scalar(
        select(func.count())
        .select_from(Device)
        .where(
            Device.product_id == product.id,
            Device.status.in_(("available", "reserved", "maintenance")),
        )
    ) or 0
    on_site_devices = db.scalar(
        select(func.count())
        .select_from(Device)
        .where(Device.product_id == product.id, Device.status == "in_use")
    ) or 0
    damaged_devices = db.scalar(
        select(func.count())
        .select_from(Device)
        .where(Device.product_id == product.id, Device.condition == "damaged")
    ) or 0
    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "total_devices": int(total_devices),
        "in_store_devices": int(in_store_devices),
        "on_site_devices": int(on_site_devices),
        "damaged_devices": int(damaged_devices),
        "available": int(in_store_devices),
        "is_rental": product.is_rental_product,
        "eventory_available": product.eventory_available_qty,
    }


def _check_date_range_availability(args: dict, db: Session) -> dict:
    item_name = str(args.get("item_name") or "")
    product = _find_product(item_name, db)
    if product is None:
        return {"error": f"Product not found: {item_name}"}
    try:
        start_date = date.fromisoformat(str(args.get("start_date") or ""))
        end_date = date.fromisoformat(str(args.get("end_date") or ""))
    except ValueError:
        return {"error": "start_date and end_date must be valid ISO dates (YYYY-MM-DD)"}

    availability = calculate_product_availability(
        db, [product.id], start_date, end_date
    )[0]
    return {
        **availability,
        "sku": product.sku,
        "name": product.name,
    }


def _get_rates(args: dict, db: Session) -> dict:
    item_name = args.get("item_name", "")
    product = _find_product(item_name, db)
    if not product:
        return {"error": f"Product not found: {item_name}"}
    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "daily_rate": float(product.daily_rate or 0),
        "replace_cost": float(product.replace_cost or 0),
        "is_rental": product.is_rental_product,
        "rental_price": float(product.rental_price or 0) if product.is_rental_product else None,
    }


def _list_customers(args: dict, db: Session) -> dict:
    query = args.get("query", "")
    q = f"%{query}%"
    customers = db.scalars(
        select(Company).where(
            (Company.name.ilike(q)) | (Company.email.ilike(q))
        ).limit(10)
    ).all()
    return {
        "customers": [
            {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
            for c in customers
        ],
        "count": len(customers),
    }


def _search_products(args: dict, db: Session) -> dict:
    query = args.get("query", "")
    category = args.get("category", "")
    product_type = args.get("product_type", "")
    if product_type and product_type not in PRODUCT_TYPES:
        return {"error": f"product_type must be one of: {', '.join(PRODUCT_TYPES)}"}

    stmt = select(Product)
    if query:
        q = f"%{query}%"
        stmt = stmt.where((Product.name.ilike(q)) | (Product.sku.ilike(q)))
    if category:
        stmt = stmt.where(Product.category.ilike(f"%{category}%"))
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)

    products = db.scalars(stmt.limit(10)).all()
    return {
        "products": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "product_type": p.product_type,
                "daily_rate": float(p.daily_rate or 0),
            }
            for p in products
        ],
        "count": len(products),
    }


def _list_jobs(args: dict, db: Session) -> dict:
    status_filter = args.get("status", "")
    if status_filter and status_filter not in JOB_STATUSES:
        return {"error": f"status must be one of: {', '.join(JOB_STATUSES)}"}
    limit = min(max(int(args.get("limit") or 10), 1), 50)

    stmt = select(Job).order_by(Job.id.desc())
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    stmt = stmt.limit(limit)

    jobs = db.scalars(stmt).all()
    return {
        "jobs": [
            {
                "id": j.id,
                "job_code": j.job_code,
                "status": j.status,
                "start_date": str(j.start_date) if j.start_date else None,
                "end_date": str(j.end_date) if j.end_date else None,
            }
            for j in jobs
        ],
        "count": len(jobs),
    }


def _list_categories(args: dict, db: Session) -> dict:
    categories = db.scalars(
        select(InventoryCategory).where(InventoryCategory.is_active.is_(True)).order_by(InventoryCategory.sort_order)
    ).all()

    tree = []
    for cat in categories:
        tree.append({
            "id": cat.id,
            "name": cat.name,
            "parent_id": cat.parent_id,
        })

    return {"categories": tree, "count": len(tree)}


def _update_manufacturer(args: dict, db: Session) -> dict:
    item_name = args.get("item_name", "")
    manufacturer = args.get("manufacturer", "")
    if not item_name or not manufacturer:
        return {"error": "item_name and manufacturer are required"}
    product = _find_product(item_name, db)
    if not product:
        return {"error": f"Product not found: {item_name}"}
    product.manufacturer = manufacturer.strip()
    db.commit()
    return {"success": True, "product_id": product.id, "sku": product.sku, "name": product.name, "manufacturer": product.manufacturer}


def _update_category(args: dict, db: Session) -> dict:
    item_name = args.get("item_name", "")
    category = args.get("category", "")
    if not item_name or not category:
        return {"error": "item_name and category are required"}
    product = _find_product(item_name, db)
    if not product:
        return {"error": f"Product not found: {item_name}"}
    product.category = category.strip()
    db.commit()
    return {"success": True, "product_id": product.id, "sku": product.sku, "name": product.name, "category": product.category}


def _batch_update_manufacturers(args: dict, db: Session) -> dict:
    product_names = args.get("product_names", [])
    manufacturer = args.get("manufacturer", "")
    if not product_names or not manufacturer:
        return {"error": "product_names and manufacturer are required"}
    results = []
    for name in product_names:
        product = _find_product(name, db)
        if product:
            product.manufacturer = manufacturer.strip()
            results.append({"sku": product.sku, "name": product.name, "success": True})
        else:
            results.append({"name": name, "success": False, "error": "Not found"})
    db.commit()
    return {"updated": len([r for r in results if r["success"]]), "results": results}


def _find_job(job_code: str, db: Session) -> Job | None:
    return db.scalar(select(Job).where(Job.job_code == job_code.strip()))


def _get_job_manifest(args: dict, db: Session) -> dict:
    job_code = str(args.get("job_code") or "").strip()
    if not job_code:
        return {"error": "job_code is required"}
    job = _find_job(job_code, db)
    if job is None:
        return {"error": f"Job not found: {job_code}"}

    requirements = db.scalars(
        select(JobRequirement)
        .where(JobRequirement.job_id == job.id)
        .order_by(JobRequirement.id)
    ).all()
    line_items = []
    for requirement in requirements:
        product = db.get(Product, requirement.product_id) if requirement.product_id else None
        vendor_product = (
            db.get(VendorProduct, requirement.vendor_product_id)
            if requirement.vendor_product_id
            else None
        )
        line_items.append(
            {
                "requirement_id": requirement.id,
                "product_id": requirement.product_id,
                "sku": product.sku if product else (vendor_product.sku if vendor_product else None),
                "name": product.name if product else (vendor_product.name if vendor_product else None),
                "product_type": product.product_type if product else None,
                "quantity_required": requirement.quantity_required,
                "quantity_picked": requirement.quantity_picked,
                "label": requirement.label,
                "notes": requirement.notes,
            }
        )

    audit_rows = db.scalars(
        select(InventoryAuditLog)
        .where(
            InventoryAuditLog.job_id == job.id,
            InventoryAuditLog.device_id.is_not(None),
            InventoryAuditLog.action.in_(("job_out", "job_in")),
            InventoryAuditLog.success.is_(True),
        )
        .order_by(InventoryAuditLog.created_at.desc(), InventoryAuditLog.id.desc())
    ).all()
    latest_audit_by_device: dict[int, InventoryAuditLog] = {}
    for row in audit_rows:
        if row.device_id is not None:
            latest_audit_by_device.setdefault(row.device_id, row)

    packed_devices: list[Device] = []
    for device_id, audit in latest_audit_by_device.items():
        if audit.action == "job_out":
            device = db.get(Device, device_id)
            if device:
                packed_devices.append(device)

    cases_by_id: dict[int, dict] = {}
    packed_equipment = []
    for device in packed_devices:
        product = db.get(Product, device.product_id)
        if product is None:
            continue
        packed_item = {
            "device_id": device.id,
            "asset_tag": device.asset_tag,
            "serial_number": device.serial_number,
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "product_type": product.product_type,
        }
        if product.product_type == "case":
            contents = db.scalars(
                select(Device).where(Device.case_device_id == device.id).order_by(Device.id)
            ).all()
            case_contents = []
            for content in contents:
                content_product = db.get(Product, content.product_id)
                case_contents.append(
                    {
                        "device_id": content.id,
                        "asset_tag": content.asset_tag,
                        "serial_number": content.serial_number,
                        "product_id": content.product_id,
                        "product_name": (
                            content_product.name if content_product else None
                        ),
                    }
                )
            cases_by_id[device.id] = {
                **packed_item,
                "contents": case_contents,
            }
        else:
            packed_item["case_device_id"] = device.case_device_id
            packed_equipment.append(packed_item)

    return {
        "job": {
            "id": job.id,
            "job_code": job.job_code,
            "status": job.status,
            "start_date": str(job.start_date) if job.start_date else None,
            "end_date": str(job.end_date) if job.end_date else None,
            "company_name": job.company_name,
            "venue_name": job.venue_name,
        },
        "line_items": line_items,
        "cases": list(cases_by_id.values()),
        "packed_equipment": packed_equipment,
    }


def _add_item_to_job(args: dict, db: Session) -> dict:
    job_code = str(args.get("job_code") or "").strip()
    item_name = str(args.get("item_name") or "").strip()
    quantity = args.get("quantity")
    if not job_code or not item_name:
        return {"error": "job_code and item_name are required"}
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return {"error": "quantity must be a positive integer"}

    job = _find_job(job_code, db)
    if job is None:
        return {"error": f"Job not found: {job_code}"}
    product = _find_product(item_name, db)
    if product is None:
        return {"error": f"Product not found: {item_name}"}

    requirement = JobRequirement(
        job_id=job.id,
        product_id=product.id,
        quantity_required=quantity,
        label=(str(args.get("label") or "").strip() or None),
        notes=(str(args.get("notes") or "").strip() or None),
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return {
        "success": True,
        "job_code": job.job_code,
        "requirement_id": requirement.id,
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "quantity_required": requirement.quantity_required,
    }


def _update_job_manifest(args: dict, db: Session) -> dict:
    job_code = str(args.get("job_code") or "").strip()
    action = args.get("action")
    requirement_id = args.get("requirement_id")
    if not job_code or action not in {"update", "remove"}:
        return {"error": "job_code and a valid action (update or remove) are required"}
    if isinstance(requirement_id, bool) or not isinstance(requirement_id, int):
        return {"error": "requirement_id must be an integer"}

    job = _find_job(job_code, db)
    if job is None:
        return {"error": f"Job not found: {job_code}"}
    requirement = db.get(JobRequirement, requirement_id)
    if requirement is None or requirement.job_id != job.id:
        return {"error": f"Manifest item {requirement_id} was not found on job {job_code}"}

    if action == "remove":
        db.delete(requirement)
        db.commit()
        return {"success": True, "action": "remove", "requirement_id": requirement_id}

    updates = False
    if "quantity" in args:
        quantity = args["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            return {"error": "quantity must be a positive integer"}
        requirement.quantity_required = quantity
        updates = True
    for field in ("label", "notes"):
        if field in args:
            value = str(args[field] or "").strip() or None
            setattr(requirement, field, value)
            updates = True
    if not updates:
        return {"error": "Provide quantity, label, or notes to update"}

    db.commit()
    db.refresh(requirement)
    return {
        "success": True,
        "action": "update",
        "job_code": job.job_code,
        "requirement_id": requirement.id,
        "quantity_required": requirement.quantity_required,
        "label": requirement.label,
        "notes": requirement.notes,
    }


def _create_customer(args: dict, db: Session) -> dict:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"error": "name is required"}

    email = str(args.get("email") or "").strip() or None
    if email:
        existing = db.scalar(select(Company).where(Company.email.ilike(email)))
        if existing:
            return {
                "error": (
                    f"A customer with email {email} already exists "
                    f"(customer_id: {existing.id}); use update_customer."
                )
            }

    customer = Company(
        name=name,
        email=email,
        phone=(str(args.get("phone") or "").strip() or None),
        address=(str(args.get("address") or "").strip() or None),
        city=(str(args.get("city") or "").strip() or None),
        postal_code=(str(args.get("postal_code") or "").strip() or None),
        country=(str(args.get("country") or "").strip() or None),
        notes=(str(args.get("notes") or "").strip() or None),
        is_customer=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {
        "success": True,
        "customer_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }


def _update_customer(args: dict, db: Session) -> dict:
    customer_id = args.get("customer_id")
    if isinstance(customer_id, bool) or not isinstance(customer_id, int):
        return {"error": "customer_id must be an integer"}
    customer = db.get(Company, customer_id)
    if customer is None or not customer.is_customer:
        return {"error": f"Customer not found: {customer_id}"}

    fields = ("name", "email", "phone", "address", "city", "postal_code", "country", "notes")
    changed = False
    for field in fields:
        if field in args:
            value = str(args[field] or "").strip() or None
            if field == "name" and value is None:
                return {"error": "name cannot be empty"}
            setattr(customer, field, value)
            changed = True
    if not changed:
        return {"error": "At least one customer field is required"}

    db.commit()
    db.refresh(customer)
    return {
        "success": True,
        "customer_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }


def _find_device(identifier: str, db: Session) -> Device | None:
    value = identifier.strip()
    if not value:
        return None
    matches = db.scalars(
        select(Device)
        .where(or_(Device.serial_number == value, Device.asset_tag == value))
        .order_by(Device.id)
        .limit(2)
    ).all()
    if len(matches) > 1:
        raise ValueError(f"Multiple devices match identifier '{value}'; use the asset tag.")
    return matches[0] if matches else None


def _flag_damaged_device(args: dict, db: Session) -> dict:
    identifier = str(args.get("identifier") or "").strip()
    title = str(args.get("title") or "").strip()
    severity = str(args.get("severity") or "medium").strip().lower()
    if not identifier or not title:
        return {"error": "identifier and title are required"}
    if severity not in DEFECT_SEVERITIES:
        return {"error": f"severity must be one of: {', '.join(DEFECT_SEVERITIES)}"}

    device = _find_device(identifier, db)
    if device is None:
        return {"error": f"Device not found: {identifier}"}
    defect = DefectReport(
        device_id=device.id,
        title=title,
        description=(str(args.get("description") or "").strip() or None),
        status="open",
        severity=severity,
    )
    device.condition = "damaged"
    device.status = "maintenance"
    db.add(defect)
    db.commit()
    db.refresh(defect)
    return {
        "success": True,
        "defect_report_id": defect.id,
        "device_id": device.id,
        "asset_tag": device.asset_tag,
        "serial_number": device.serial_number,
        "status": device.status,
        "condition": device.condition,
        "severity": defect.severity,
    }


def _update_device_status(args: dict, db: Session) -> dict:
    identifier = str(args.get("identifier") or "").strip()
    state = str(args.get("status") or "").strip().lower()
    if not identifier or state not in DEVICE_STATUSES:
        return {"error": f"identifier and status ({', '.join(DEVICE_STATUSES)}) are required"}
    if state == "damaged":
        return _flag_damaged_device(
            {
                "identifier": identifier,
                "title": args.get("title") or "Device marked damaged",
                "description": args.get("description") or "Marked damaged by Stockwire Assistant.",
                "severity": args.get("severity") or "medium",
            },
            db,
        )

    device = _find_device(identifier, db)
    if device is None:
        return {"error": f"Device not found: {identifier}"}
    device.status = {
        "in_store": "available",
        "on_site": "in_use",
        "maintenance": "maintenance",
    }[state]
    db.commit()
    return {
        "success": True,
        "device_id": device.id,
        "asset_tag": device.asset_tag,
        "serial_number": device.serial_number,
        "status": device.status,
        "condition": device.condition,
    }
