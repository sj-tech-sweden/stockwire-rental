#!/usr/bin/env python3
"""HireHop inventory JSON importer -> products + devices

Creates product and device JSON outputs (or optionally POSTs to an API).

Usage:
  python hirehop_import.py --input /path/inventory.json --outdir ./out --mapping hirehop_mapping.json

Options:
  --api-url URL     Optional API base to POST created items (/products, /devices).
  --api-key KEY     Optional API key header value (X-API-Key).
  --dry-run         Don't POST, just write JSON outputs.
  --limit N         Only process first N products (for testing).

The script is intentionally conservative: it produces two files in the output
directory: `products_output.json` and `devices_output.json`. Each product
includes a reference `source_id` pointing to the original HireHop `ID`.

The mapping file controls how fields map from the HireHop structure to
target product/device fields. A default mapping for HireHop is included.
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import requests
except Exception:
    requests = None


def extract(obj, path):
    """Extract nested value using dot-separated path. Returns None if not found."""
    if obj is None:
        return None
    parts = path.split('.')
    cur = obj
    for p in parts:
        if cur is None:
            return None
        # support list indexes like items.0.field
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


def map_fields(src, mapping):
    out = {}
    for tgt, src_path in (mapping or {}).items():
        val = extract(src, src_path)
        out[tgt] = val
    return out


def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)
    return path


def post_item(api_url, api_key, path, payload):
    if not requests:
        raise RuntimeError('requests package required for API mode')
    url = api_url.rstrip('/') + '/' + path.lstrip('/')
    headers = {}
    if api_key:
        headers['X-API-Key'] = api_key
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()


def load_mapping(path):
    if not path:
        return {}
    with open(path, 'r', encoding='utf8') as fh:
        return json.load(fh)


def process(input_path, mapping, outdir, api_url=None, api_key=None, dry_run=True, limit=None):
    mapping = mapping or {}
    prod_map = mapping.get('product', {})
    device_map = mapping.get('device', {})

    with open(input_path, 'r', encoding='utf8') as fh:
        data = json.load(fh)

    products_out = []
    devices_out = []
    processed = 0

    for item in data:
        if limit and processed >= limit:
            break
        # skip obviously empty entries
        if not item or not isinstance(item, dict):
            continue

        source_id = item.get('ID')
        product = map_fields(item, prod_map)
        product['source_id'] = source_id
        products_out.append(product)

        # handle serialnumbers
        serials = item.get('serialnumbers') or []

        if serials:
            for s in serials:
                # in HireHop export the useful data is often under `cell`
                cell = s.get('cell') if isinstance(s, dict) else None
                try:
                    qty = int(float(extract(cell, device_map.get('qty', 'QTY')) or 1))
                except (ValueError, TypeError):
                    qty = 1
                for i in range(max(1, qty)):
                    dev = map_fields(cell or s, device_map)
                    dev['product_source_id'] = source_id
                    # attach source serial entry id for traceability
                    if isinstance(s, dict) and s.get('id'):
                        dev['source_serial_id'] = s.get('id')
                    # if qty >1 and there is no unique serial/barcode per device, leave blank
                    if qty > 1:
                        # if QTY>1 but a unique serial exists, still keep it on first device only
                        if i > 0:
                            dev.pop('serial', None)
                            dev.pop('barcode', None)
                    devices_out.append(dev)
        else:
            # no serials: create placeholder devices based on product-level stock/available if present
            # try to infer quantity from product fields like 'IS_BOX' or 'STOCK' if numeric
            qty_guess = 0
            try:
                qty_guess = int(item.get('STOCK')) if isinstance(item.get('STOCK'), (int, str)) and str(item.get('STOCK')).isdigit() else 0
            except Exception:
                qty_guess = 0
            if qty_guess <= 0:
                # create one device with minimal data so product exists
                devices_out.append({'product_source_id': source_id})
            else:
                for _ in range(qty_guess):
                    devices_out.append({'product_source_id': source_id})

        processed += 1

    ensure_outdir(outdir)
    products_file = os.path.join(outdir, 'products_output.json')
    devices_file = os.path.join(outdir, 'devices_output.json')

    with open(products_file, 'w', encoding='utf8') as fh:
        json.dump(products_out, fh, indent=2, ensure_ascii=False)
    with open(devices_file, 'w', encoding='utf8') as fh:
        json.dump(devices_out, fh, indent=2, ensure_ascii=False)

    print(f'Wrote {len(products_out)} products to {products_file}')
    print(f'Wrote {len(devices_out)} devices to {devices_file}')

    if api_url and not dry_run:
        print('Uploading to API...')
        for p in products_out:
            post_item(api_url, api_key, '/products', p)
        for d in devices_out:
            post_item(api_url, api_key, '/devices', d)
        print('Upload complete')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', '-i', required=True)
    p.add_argument('--mapping', '-m', default=None)
    p.add_argument('--outdir', '-o', default='./out')
    p.add_argument('--api-url', default=None)
    p.add_argument('--api-key', default=None)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--limit', type=int, default=None)
    args = p.parse_args()

    mapping = load_mapping(args.mapping) if args.mapping else None
    process(args.input, mapping, args.outdir, api_url=args.api_url, api_key=args.api_key, dry_run=args.dry_run, limit=args.limit)


if __name__ == '__main__':
    main()
