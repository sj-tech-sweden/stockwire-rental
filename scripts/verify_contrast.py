#!/usr/bin/env python3
"""Verify WCAG contrast ratios for Stockwire design-system color pairs.

Checks token colors from design/tokens/tokens.json against the dark and light
surfaces defined in frontend/src/css/app.css. Fails with a non-zero exit code
if any required contrast threshold is missed.
"""

import json
import re
import sys
from pathlib import Path


def parse_hex(value):
    """Return (r, g, b) integers from a hex color string."""
    value = value.strip().lstrip('#')
    if len(value) == 3:
        value = ''.join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    """Calculate WCAG 2.1 relative luminance for an sRGB color."""

    def channel(c):
        c_srgb = c / 255.0
        return c_srgb / 12.92 if c_srgb <= 0.03928 else ((c_srgb + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(color_a, color_b):
    """Return the WCAG contrast ratio between two hex colors."""
    lum_a = relative_luminance(parse_hex(color_a))
    lum_b = relative_luminance(parse_hex(color_b))
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def load_tokens():
    tokens_path = Path(__file__).parent.parent / 'design' / 'tokens' / 'tokens.json'
    with tokens_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def flatten_color_tokens(tokens, prefix='', inherited_type=None):
    """Extract hex color values from the nested tokens structure."""
    colors = {}
    group_type = tokens.get('$type', inherited_type) if isinstance(tokens, dict) else inherited_type
    for key, value in tokens.items():
        if key.startswith('$'):
            continue
        if isinstance(value, dict):
            if '$value' in value and group_type == 'color':
                colors[prefix + key] = value['$value']
            else:
                colors.update(flatten_color_tokens(value, prefix=f"{prefix}{key}.", inherited_type=group_type))
    return colors


def main():
    tokens = load_tokens()
    colors = flatten_color_tokens(tokens['stockwire'])

    # Theme surface and text colors from app.css (dark + light variants)
    dark_bg = colors['surface.900']
    dark_surface = colors['surface.700']
    dark_text_primary = colors['text.primary']
    dark_text_secondary = colors['text.secondary']

    light_bg = '#F3F9F3'
    light_surface = '#FFFFFF'
    light_text_primary = '#0F1720'
    light_text_secondary = '#586E6E'

    checks = [
        # (name, foreground, background, required_ratio)
        ('Dark primary text on dark background', dark_text_primary, dark_bg, 4.5),
        ('Dark primary text on dark surface', dark_text_primary, dark_surface, 4.5),
        ('Dark secondary text on dark background', dark_text_secondary, dark_bg, 4.5),
        ('Dark secondary text on dark surface', dark_text_secondary, dark_surface, 4.5),
        ('Light primary text on light background', light_text_primary, light_bg, 4.5),
        ('Light primary text on light surface', light_text_primary, light_surface, 4.5),
        ('Light secondary text on light background', light_text_secondary, light_bg, 4.5),
        ('Light secondary text on light surface', light_text_secondary, light_surface, 4.5),
        ('Brand green on dark surface', colors['color.brand.green'], dark_surface, 3.0),
        ('Brand green on light surface', colors['color.brand.green'], light_surface, 3.0),
        ('Danger on dark surface', colors['color.semantic.danger'], dark_surface, 3.0),
        ('Danger on light surface', colors['color.semantic.danger'], light_surface, 3.0),
    ]

    failures = []
    print('Contrast verification results:')
    print('-' * 70)
    for name, fg, bg, required in checks:
        ratio = contrast_ratio(fg, bg)
        status = 'PASS' if ratio >= required else 'FAIL'
        print(f"{status}: {name}: {ratio:.2f}:1 (required {required}:1)")
        if ratio < required:
            failures.append((name, ratio, required))
    print('-' * 70)

    if failures:
        print(f"FAILED: {len(failures)} contrast check(s) below the required ratio.")
        return 1

    print('All contrast checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
