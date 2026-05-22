# Brand and UI System (Quasar)

Last reviewed: 2026-05-22

## Brand direction

Observed identity cues:

- Deep dark background
- Bright cable-green accent
- Technical, clean, industrial tone
- Curved cable motif as a signature element

Reference profile values used in this system:

- Typography families: `Myriad Pro` and `Raleway SemiBold`
- Profile primary blue token: `#4F80FF`

## Design principles

- Functional first: operational UI with strong readability
- Brand-led accents: green used for active state, scan success, and key CTA
- Calm surfaces: dark neutrals for dense data views
- Motion with meaning: route transitions and scan feedback only

## Current UI baseline (already delivered)

- Expanded i18n coverage in key inventory and settings workflows.
- Better parity between synced/manual rental product affordances in inventory UI.
- Baseline settings for integrations, storage, and auth-management workflows.

## Quasar token proposal

Use these as CSS vars and map to Quasar brand config.

- Brand primary: #3F873F
- Brand primary-600: #2D9148
- Brand success: #3F873F
- Brand warning: #F7B84B
- Brand danger: #E65656
- Surface-900: #0C1114
- Surface-800: #11181D
- Surface-700: #182228
- Text-primary: #E9F1EE
- Text-secondary: #A8BAB1
- Border-subtle: #243138

## Typography

Integrated profile pair:

- Headings/UI emphasis: Raleway SemiBold (600)
- Body/data dense text: Myriad Pro (400)
- Numeric/scan IDs: Myriad Pro (400)

If the profile is revised, replace in one place:

- Quasar boot typography config
- global CSS font variables

## Component style guidance

- Buttons: rounded-md, high-contrast labels, strong hover/focus ring
- Cards: elevated dark surfaces with subtle border and green active rail
- Tables: zebra with compact density option and cards on mobile phones using q-table grid
- Scanner panels: extra-large input targets, persistent camera trigger, haptic-compatible feedback states

## Remaining UI priorities

- Light mode hardening and contrast verification across all pages.
- Mobile-first overflow and table/card adaptation completion.
- Defect and zone workflow UX consistency with inventory patterns.

## Theming modes

- dark (default)
- light
- auto (prefers-color-scheme)

## Accessibility baseline

- Minimum contrast 4.5:1 for body text
- keyboard-first nav for all admin workflows
- focus-visible styling mandatory
- reduced-motion variant for animations

## Related docs

- `docs/ROADMAP_FROM_ISSUES.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/STORAGE_FILES_GUIDE.md`
