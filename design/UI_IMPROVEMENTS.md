# Stockwire UI Improvement Opportunities

These opportunities are based on the design system in `design/` and the current frontend baseline. They are intended to be explored and prototyped in Penpot before implementation.

## 1. Consistent token usage

**Current state:** Some colors are hardcoded across components and pages.
**Improvement:** Use the design tokens everywhere. The validation script (`scripts/validate_design_tokens.py`) can catch drift between `design/tokens/tokens.json`, `frontend/src/css/app.css`, and `frontend/quasar.config.js`.

**Quick wins:**
- Replace hardcoded `#3F873F` with `--ec-primary`.
- Replace hardcoded `#E9F1EE` with `--ec-text-primary`.
- Use `--ec-text-secondary` for muted labels.

## 2. Header consolidation

**Current state:** Header styling has many override rules to handle Quasar theme classes.
**Improvement:** Simplify `MainLayout.vue` and `app.css` so the header reads directly from `--ec-header-bg` and `--ec-header-text`. This reduces CSS specificity battles.

**Penpot experiment:** Create a single Header component with dark/light variants and test it on every page template.

## 3. Empty states

**Current state:** Empty list views can feel bare.
**Improvement:** Add branded empty states using:
- The cable motif (`design/assets/cable-motif.svg`) as a subtle background.
- A clear headline in `Heading / H3`.
- A primary CTA button.

**Pages to address:** Inventory, Jobs, Maintenance, Crew, Venues.

## 4. Scan experience

**Current state:** Scan page is functional but could be more tactile.
**Improvement:**
- Increase touch targets to at least 64px.
- Add haptic-compatible feedback states (visual + optional vibration).
- Show device/product thumbnail after a successful scan.
- Use `Scanner / Target` and `Scan Feedback / Success` components from the library.

## 5. Dashboard density

**Current state:** Dashboard shows stats and recent activity.
**Improvement:**
- Add a **warehouse snapshot** card showing highlighted bins from LED integration.
- Show **offline queue status** when pending mutations exist.
- Add a **today's crew availability** mini-card.
- Use the **Active Card** variant with the green left rail for cards that need attention.

## 6. Job planning visibility

**Current state:** Jobs are primarily a list/table.
**Improvement:**
- Add a **calendar view** toggle.
- Highlight jobs with missing requirements or crew conflicts.
- Show a **packing progress bar** on the job detail page.
- Surface **missing certifications** for assigned crew.

## 7. Mobile table adaptation

**Current state:** Tables can overflow on small screens.
**Improvement:**
- Use Quasar's `grid` table mode on phones.
- Convert dense tables to card lists on mobile.
- Ensure horizontal padding follows `--ec-space-sm` (8px) on mobile.

## 8. Settings grouping

**Current state:** Settings has many tabs and fields.
**Improvement:**
- Group related settings into **Cards** instead of one long form.
- Add **integration health indicators** (connected / disconnected chips).
- Show inline validation hints using `Body / Muted`.

## 9. Route planner enhancements

**Current state:** Route planner shows stops and a map export.
**Improvement:**
- Show estimated drive time per stop.
- Warn when a job's equipment exceeds vehicle capacity.
- Add an "optimize route" action (external service).

## 10. Accessibility hardening

**Current state:** Focus-visible is partially covered.
**Improvement:**
- Ensure all interactive elements have a visible focus ring.
- Verify 4.5:1 contrast for all body text.
- Add a `prefers-reduced-motion` variant for animations.

## How to use Penpot for these

1. Open the `Stockwire Library` in Penpot (see `design/penpot/IMPORT_GUIDE.md`).
2. Create a new file for each improvement area (e.g., `Stockwire / Dashboard Improvements`).
3. Enable the shared library.
4. Build variants using the components and tokens.
5. Share the Penpot link or export PNGs for review.
6. Once approved, implement the changes in the Quasar frontend and update tokens if needed.
