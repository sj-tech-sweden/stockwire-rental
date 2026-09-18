# Stockwire Design System

This directory contains the source-of-truth design system for **Stockwire Rental**.
It is meant to be reused across:

- The Quasar frontend (`frontend/src/`)
- Penpot design projects (`design/penpot/`)
- Future brand/marketing materials
- Any other tool that can consume W3C design tokens

## Structure

```
design/
├── README.md                 # This file
├── tokens/
│   ├── tokens.json           # W3C Design Tokens Format (for Penpot / Tokens Studio)
│   ├── tokens.css            # CSS custom properties (drop-in for frontend)
│   └── quasar-brand.json     # Quasar `framework.config.brand` mapping
├── assets/
│   ├── logo.svg              # Stockwire wordmark + mark
│   ├── logo-mark.svg         # Cable mark only
│   ├── cable-motif.svg       # Curved cable signature element
│   └── components/           # Ready-made SVG component templates for Penpot
├── penpot/
│   ├── IMPORT_GUIDE.md       # How to import this system into Penpot
│   ├── components.md         # Component library spec
│   └── templates.md          # Page templates / wireframes
└── UI_IMPROVEMENTS.md        # Concrete improvement opportunities
```

## Brand direction

- Deep dark background
- Bright cable-green accent
- Technical, clean, industrial tone
- Curved cable motif as a signature element

See `docs/BRAND_UI_SYSTEM.md` for the original project documentation.

## Quick start

### For designers (Penpot)

1. Follow `penpot/IMPORT_GUIDE.md` to create a Penpot library.
2. Publish the file as a **Shared Library** in Penpot.
3. Enable the library in any new Stockwire project.

### For developers

1. Copy `tokens/tokens.css` values into `frontend/src/css/app.css`.
2. Use the CSS variables (`--ec-*`) or Quasar brand colors directly.
3. Keep this design system in sync when adding new tokens.

## Design principles

1. **Functional first** — operational UI with strong readability.
2. **Brand-led accents** — green used for active state, scan success, and key CTA.
3. **Calm surfaces** — dark neutrals for dense data views.
4. **Motion with meaning** — route transitions and scan feedback only.

## Keeping tokens in sync

When you change a value here, update the matching source in:

- `frontend/src/css/app.css`
- `frontend/quasar.config.js` (`framework.config.brand`)
- `docs/BRAND_UI_SYSTEM.md`

Run `python scripts/validate_design_tokens.py` to validate that these files do not drift.
