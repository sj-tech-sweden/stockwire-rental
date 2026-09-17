#!/usr/bin/env python3
"""
Validate that the design tokens in design/tokens/tokens.json stay in sync with
the Quasar frontend CSS and config.

Usage:
    python scripts/validate_design_tokens.py

Returns non-zero if a mismatch is found.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS_FILE = ROOT / "design" / "tokens" / "tokens.json"
CSS_FILE = ROOT / "frontend" / "src" / "css" / "app.css"
QUASAR_CONFIG = ROOT / "frontend" / "quasar.config.js"

COLOR_MAP = {
    "stockwire.color.brand.green": "--ec-primary",
    "stockwire.color.brand.green-600": "--ec-primary-600",
    "stockwire.color.brand.green-dark": "--ec-accent",
    "stockwire.color.profile.primary-blue": "--ec-profile-blue",
    "stockwire.color.semantic.success": "--ec-success",
    "stockwire.color.semantic.warning": "--ec-warning",
    "stockwire.color.semantic.danger": "--ec-danger",
    "stockwire.color.semantic.info": "--ec-info",
    "stockwire.surface.900": "--ec-surface-900",
    "stockwire.surface.800": "--ec-surface-800",
    "stockwire.surface.700": "--ec-surface-700",
    "stockwire.text.primary": "--ec-text-primary",
    "stockwire.text.secondary": "--ec-text-secondary",
    "stockwire.border.subtle": "--ec-border-subtle",
}

QUASAR_BRAND_MAP = {
    "stockwire.color.brand.green": "primary",
    "stockwire.color.brand.green-dark": "accent",
    "stockwire.surface.900": "dark",
    "stockwire.color.semantic.success": "positive",
    "stockwire.color.semantic.danger": "negative",
    "stockwire.color.semantic.warning": "warning",
    "stockwire.color.semantic.info": "info",
}


def load_tokens():
    with TOKENS_FILE.open() as f:
        data = json.load(f)
    flat = {}

    def walk(node, prefix):
        for key, value in node.items():
            if key.startswith(("$", "@")):
                continue
            new_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                if "$value" in value:
                    flat[new_prefix] = value["$value"]
                else:
                    walk(value, new_prefix)

    walk(data, "")
    return flat


def load_css_vars():
    text = CSS_FILE.read_text()
    return {m.group(1): m.group(2) for m in re.finditer(r"(--[\w-]+):\s*([^;]+);", text)}


def load_quasar_brand():
    text = QUASAR_CONFIG.read_text()
    match = re.search(r"brand:\s*\{([^}]+)\}", text, re.DOTALL)
    if not match:
        return {}
    brand_text = match.group(1)
    return {
        m.group(1).strip(): m.group(2).strip()
        for m in re.finditer(r"(\w+):\s*['\"]?([^,'\"\n]+)['\"]?", brand_text)
    }


def main():
    tokens = load_tokens()
    css_vars = load_css_vars()
    quasar_brand = load_quasar_brand()

    errors = []

    for token_path, css_var in COLOR_MAP.items():
        expected = tokens.get(token_path, "").upper()
        actual = css_vars.get(css_var, "").strip().upper()
        if not expected:
            errors.append(f"Missing token: {token_path}")
            continue
        if actual != expected:
            errors.append(
                f"CSS mismatch for {token_path}: expected {expected}, found {actual} in {css_var}"
            )

    for token_path, quasar_key in QUASAR_BRAND_MAP.items():
        expected = tokens.get(token_path, "").upper()
        actual = quasar_brand.get(quasar_key, "").strip("'\"").upper()
        if actual != expected:
            errors.append(
                f"Quasar brand mismatch for {token_path}: expected {expected}, found {actual} in brand.{quasar_key}"
            )

    if errors:
        print("Design token validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("Design tokens are in sync with frontend CSS and Quasar config.")


if __name__ == "__main__":
    main()
