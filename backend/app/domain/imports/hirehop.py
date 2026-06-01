"""HireHop import helpers for backend integration.

Provides functions to convert HireHop JSON exports into product and device
objects suitable for persistence or further processing by backend import
flows. Designed to be imported and used by other backend code (not only CLI).
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent / 'hirehop_mapping.json'


def _extract(obj: Any, path: str):
    if obj is None:
        return None
    parts = path.split('.') if path else []
    cur = obj
    for p in parts:
        if cur is None:
            return None
        if p.isdigit():
            idx = int(p)
            if not isinstance(cur, list) or idx >= len(cur):
                return None
            cur = cur[idx]
        else:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
    return cur


def _map_fields(src: Dict, mapping: Dict[str, str]) -> Dict:
    out = {}
    for tgt, src_path in (mapping or {}).items():
        out[tgt] = _extract(src, src_path)
    return out


def _extract_flexible(primary: Any, secondary: Any, path: str):
    """Try a path on primary and secondary sources, and with/without a `cell.` prefix.

    This keeps imports resilient when mapping files use either `QTY`/`SERIAL` or
    `cell.QTY`/`cell.SERIAL` style keys.
    """
    if not path:
        return None

    # 1) try as-is
    for src in (primary, secondary):
        val = _extract(src, path)
        if val is not None:
            return val

    # 2) try alternate path (toggle cell. prefix)
    alt = path[5:] if path.startswith('cell.') else f'cell.{path}'
    for src in (primary, secondary):
        val = _extract(src, alt)
        if val is not None:
            return val

    return None


def _coerce_qty(value: Any) -> int:
    if value is None or value == '':
        return 1
    try:
        as_int = int(float(value))
        return as_int if as_int > 0 else 1
    except (TypeError, ValueError):
        return 1


def process_hirehop_data(data: List[Dict], mapping: Dict = None, limit: int = None) -> Tuple[List[Dict], List[Dict]]:
    """Process a list of HireHop items into products and devices.

    Returns (products_out, devices_out).
    """
    mapping = mapping or {}
    prod_map = mapping.get('product', {})
    device_map = mapping.get('device', {})

    products_out: List[Dict] = []
    devices_out: List[Dict] = []
    processed = 0

    for item in data:
        if limit and processed >= limit:
            break
        if not item or not isinstance(item, dict):
            continue

        source_id = item.get('ID')
        product = _map_fields(item, prod_map)

        # Safety fallback: ensure core product fields remain populated even when
        # mapping keys are missing or changed in upstream presets.
        if not product.get('title') and item.get('TITLE') is not None:
            product['title'] = item.get('TITLE')
        if not product.get('name') and item.get('TITLE') is not None:
            product['name'] = item.get('TITLE')
        if product.get('replace_cost') is None and item.get('REPLACE_COST') is not None:
            product['replace_cost'] = item.get('REPLACE_COST')
        if product.get('weight') is None and item.get('WEIGHT') is not None:
            product['weight'] = item.get('WEIGHT')
        if product.get('category_id') is None and item.get('CATEGORY_ID') is not None:
            product['category_id'] = item.get('CATEGORY_ID')
        if product.get('is_box') is None and item.get('IS_BOX') is not None:
            product['is_box'] = item.get('IS_BOX')
        if not product.get('brand') and _extract(item, 'fields.tillverkare.value') is not None:
            product['brand'] = _extract(item, 'fields.tillverkare.value')
        if not product.get('manufacturer') and _extract(item, 'fields.tillverkare.value') is not None:
            product['manufacturer'] = _extract(item, 'fields.tillverkare.value')

        crumbs = item.get('crumbs') or []
        if not product.get('category_path') and isinstance(crumbs, list):
            crumb_names = [str(crumb.get('NAME') or '').strip() for crumb in crumbs if isinstance(crumb, dict)]
            crumb_names = [name for name in crumb_names if name]
            if crumb_names:
                product['category_path'] = crumb_names

        product['source_id'] = source_id
        # HireHop stores dimensions in meters; convert to centimeters
        for dim_field in ('height_cm', 'width_cm', 'depth_cm'):
            val = product.get(dim_field)
            if val is not None:
                try:
                    product[dim_field] = round(float(val) * 100, 2) or None
                except (TypeError, ValueError):
                    product[dim_field] = None
        products_out.append(product)

        serials = item.get('serialnumbers') or []
        if serials:
            for s in serials:
                serial_obj = s if isinstance(s, dict) else {}
                cell = serial_obj.get('cell') if isinstance(serial_obj, dict) else None

                qty_path = device_map.get('qty', 'QTY')
                qty = _coerce_qty(_extract_flexible(cell, serial_obj, qty_path))
                serial_row_id = serial_obj.get('id') if isinstance(serial_obj, dict) else None

                for i in range(max(1, qty)):
                    dev = {}
                    for tgt, src_path in (device_map or {}).items():
                        dev[tgt] = _extract_flexible(cell, serial_obj, src_path)

                    dev['product_source_id'] = source_id
                    if serial_row_id:
                        if qty > 1:
                            dev['source_serial_id'] = f'{serial_row_id}:{i + 1}'
                        else:
                            dev['source_serial_id'] = str(serial_row_id)
                    if qty > 1 and i > 0:
                        dev.pop('serial', None)
                        dev.pop('barcode', None)
                    devices_out.append(dev)
        else:
            qty_guess = 0
            try:
                raw_stock = item.get('STOCK')
                qty_guess = int(raw_stock) if isinstance(raw_stock, (int, str)) and str(raw_stock).isdigit() else 0
            except Exception:
                qty_guess = 0
            if qty_guess <= 0:
                devices_out.append({'product_source_id': source_id})
            else:
                for _ in range(qty_guess):
                    devices_out.append({'product_source_id': source_id})

        processed += 1

    return products_out, devices_out


def load_mapping(path: str) -> Dict:
    import json

    with open(path, 'r', encoding='utf8') as fh:
        return json.load(fh)


def import_from_file(path: str, mapping_path: str = None, limit: int = None) -> Tuple[List[Dict], List[Dict]]:
    import json

    with open(path, 'r', encoding='utf8') as fh:
        data = json.load(fh)
    mapping = load_mapping(mapping_path) if mapping_path else None
    return process_hirehop_data(data, mapping=mapping, limit=limit)
