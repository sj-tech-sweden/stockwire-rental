"""
Tool definitions and execution handlers for the AI assistant.

Tools are defined in OpenAI function-calling format and executed
against the Stockwire database via SQLAlchemy.
"""

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.inventory.models import Product, InventoryCategory
from app.domain.customers.models import Customer
from app.domain.jobs.models import Job, JobRequirement

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
                    "product_type": {"type": "string", "description": "Filter by type: equipment, accessory, consumable, case, bundle, rental"},
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
                    "status": {"type": "string", "description": "Filter by status: draft, confirmed, completed"},
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
]


def execute_tool(name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool call and return the result as a dict."""
    handlers = {
        "check_inventory_stock": _check_stock,
        "get_rental_rates": _get_rates,
        "list_customers": _list_customers,
        "search_products": _search_products,
        "list_jobs": _list_jobs,
        "list_categories": _list_categories,
        "update_product_manufacturer": _update_manufacturer,
        "update_product_category": _update_category,
        "batch_update_manufacturers": _batch_update_manufacturers,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(arguments, db)
    except Exception as e:
        return {"error": str(e)}


def _find_product(query: str, db: Session) -> Product | None:
    q = f"%{query}%"
    return db.scalar(
        select(Product).where(
            (Product.name.ilike(q)) | (Product.sku.ilike(q))
        )
    )


def _check_stock(args: dict, db: Session) -> dict:
    item_name = args.get("item_name", "")
    product = _find_product(item_name, db)
    if not product:
        return {"error": f"Product not found: {item_name}"}
    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "total_devices": product.total_devices,
        "in_store_devices": product.in_store_devices,
        "on_site_devices": product.on_site_devices,
        "damaged_devices": product.damaged_devices,
        "available": product.in_store_devices,
        "is_rental": product.is_rental_product,
        "eventory_available": product.eventory_available_qty,
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
        select(Customer).where(
            (Customer.name.ilike(q)) | (Customer.email.ilike(q))
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
    limit = min(int(args.get("limit") or 10), 50)

    stmt = select(Job).order_by(Job.id.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)

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
