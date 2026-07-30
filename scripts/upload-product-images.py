#!/usr/bin/env python3
"""
Bulk upload product images from a folder (recursively).

Filenames are matched to products by SKU (exact) or name (fuzzy).
Images are uploaded to the storage API with category 'product-image'.

Usage:
    python3 scripts/upload-product-images.py /path/to/images --api-url https://your-api --token YOUR_API_KEY

    # Dry run first:
    python3 scripts/upload-product-images.py /path/to/images --api-url https://your-api --token YOUR_API_KEY --dry-run
"""

import argparse
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def api_request(api_url, token, method, path, data=None, content_type=None):
    headers = {"X-API-Key": token}
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(f"{api_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30, context=SSL_CTX) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 401:
            print(f"\nError: 401 Unauthorized from {api_url}{path}", file=sys.stderr)
            print("Your API key is invalid or the endpoint requires admin access.", file=sys.stderr)
            sys.exit(1)
        raise


def api_upload(api_url, token, product_id, filepath):
    boundary = "----FormBoundary"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="entity_type"\r\n\r\nproduct\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="entity_id"\r\n\r\n{product_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="category"\r\n\r\nproduct-image\r\n'
        f"--{boundary}--\r\n"
    ).encode()

    headers = {
        "X-API-Key": token,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = Request(f"{api_url}/api/v1/storage/files", data=body, headers=headers, method="POST")
    with urlopen(req, timeout=60, context=SSL_CTX) as resp:
        return json.loads(resp.read())


def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[åä]", "a", text)
    text = re.sub(r"[ö]", "o", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def load_products(api_url, token):
    return api_request(api_url, token, "GET", "/api/v1/inventory/products")


def find_matching_product(filename, products):
    normalized = normalize(Path(filename).stem)
    for p in products:
        if normalize(p.get("sku", "")) == normalized:
            return p
    for p in products:
        if normalize(p.get("name", "")) == normalized:
            return p
    for p in products:
        sku = normalize(p.get("sku", ""))
        if sku and (normalized in sku or sku in normalized):
            return p
    for p in products:
        name = normalize(p.get("name", ""))
        if name and (normalized in name or name in normalized):
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description="Bulk upload product images")
    parser.add_argument("folder", help="Path to folder with product images")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--token", default="", help="Service API key (or set TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Don't upload, just show matches")
    args = parser.parse_args()

    token = args.token or os.environ.get("TOKEN", "")
    if not token:
        print("Error: Provide --token or set TOKEN env var", file=sys.stderr)
        sys.exit(1)

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    images = sorted(f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in extensions)
    if not images:
        print(f"No image files found in {folder}")
        sys.exit(1)

    print(f"Found {len(images)} images")
    print("Loading products...")
    products = load_products(args.api_url, token)
    print(f"Loaded {len(products)} products\n")

    matched = uploaded = 0
    unmatched = []

    for img in images:
        product = find_matching_product(img.name, products)
        if not product:
            unmatched.append(str(img.relative_to(folder)))
            continue
        matched += 1
        prefix = "[DRY RUN] " if args.dry_run else ""
        print(f"{prefix}Match: {img.name} -> {product.get('sku', '?')} ({product.get('name', '?')})")
        if not args.dry_run:
            try:
                api_upload(args.api_url, token, product["id"], str(img))
                uploaded += 1
                print(f"  Uploaded OK")
            except HTTPError as e:
                body = e.read().decode() if e.fp else str(e)
                print(f"  Upload failed ({e.code}): {body[:200]}")
            except Exception as e:
                print(f"  Upload error: {e}")

    print(f"\n{'='*50}")
    print(f"Matched: {matched}/{len(images)} | Uploaded: {uploaded}")
    if unmatched:
        print(f"Unmatched ({len(unmatched)}):")
        for name in unmatched[:20]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
