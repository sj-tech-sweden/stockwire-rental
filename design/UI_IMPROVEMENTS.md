# Stockwire UI Improvement Opportunities

These opportunities are based on the design system in `design/` and the current frontend baseline. They are intended to be explored and prototyped in Penpot before implementation.

## 1. Consistent token usage

**Current state:** Some colors are hardcoded across components and pages.
**Improvement:** Use the design tokens everywhere. The validation script (`scripts/validate_design_tokens.py`) can catch drift between `design/tokens/tokens.json`, `frontend/src/css/app.css`, and `frontend/quasar.config.js`.

**Status:** In progress. Added reusable utility classes in `frontend/src/css/app.css` and aligned Quasar brand colors with the tokens.

**Quick wins:**
- Replace hardcoded `#3F873F` with `--ec-primary` — done in `InventoryPage.vue`, `ScanPage.vue`, `ZoneCrossSectionDialog.vue`, and `SetupPage.vue`.
- Replace hardcoded `#E9F1EE` with `--ec-text-primary` — done in `frontend/src/css/app.css`.
- Use `--ec-text-secondary` for muted labels — done for Quasar field labels/hints, `SetupPage.vue` muted text, and `ScanPage.vue` pending step text.

## 2. Inventory overview and empty states

**Current state:** Inventory overview tab shows stacked text lines. Tables fall back to default Quasar empty labels.
**Improvement:**
- Convert overview metrics into a card grid using `.ec-metric-label` / `.ec-metric-value`.
- Add friendly `:no-data-label` messages to Products, Rentals, and Devices tables.
- Use consistent page title styling.

**Status:** Done for the Inventory page. Added i18n keys `noProducts`, `noRentalProducts`, and `noDevices` in English and Swedish.

## 3. Header consolidation

**Current state:** Header styling has many override rules to handle Quasar theme classes.
**Improvement:** Simplify `MainLayout.vue` and `app.css` so the header reads directly from `--ec-header-bg` and `--ec-header-text`. This reduces CSS specificity battles.

**Status:** Done. Removed inline header style and MutationObserver from `MainLayout.vue`; header colors now derive from `--ec-header-bg` and `--ec-header-text` set per theme in `frontend/src/css/app.css`.

**Penpot experiment:** Create a single Header component with dark/light variants and test it on every page template.

## 4. Empty states

**Current state:** Empty list views can feel bare.
**Improvement:** Add branded empty states using:
- The cable motif (`design/assets/cable-motif.svg`) as a subtle background.
- A clear headline in `Heading / H3`.
- A primary CTA button.

**Status:** Started. Added `.ec-empty-state` utility class and applied it to empty lists on the Dashboard, Scan, Inventory, Maintenance, Route Planner, Activity, Company detail, and Job detail pages. Added `:no-data-label` messages to tables on Inventory, Jobs, Settings, Maintenance, Crew, Venues, Companies, Persons, Projects, Finance, and Activity pages.

**Pages to address:** (none for table empty states). Consider richer branded empty-state illustrations in Penpot for a future polish pass.

## 5. Scan experience

**Current state:** Scan page is functional but could be more tactile.
**Improvement:**
- Increase touch targets to at least 64px.
- Add haptic-compatible feedback states (visual + optional vibration).
- Show device/product thumbnail after a successful scan.
- Use `Scanner / Target` and `Scan Feedback / Success` components from the library.

**Status:** Started. Added `.ec-scanner-target` utility class and applied it to the Scan page header area.

## 6. Dashboard density

**Current state:** Dashboard shows stats and recent activity.
**Improvement:**
- Add a **warehouse snapshot** card showing highlighted bins from LED integration.
- Show **offline queue status** when pending mutations exist.
- Add a **today's crew availability** mini-card.
- Use the **Active Card** variant with the green left rail for cards that need attention.

**Status:** Done.
- Added `.ec-card--active` utility class in `frontend/src/css/app.css` for the green left-rail attention variant.
- Added a new dashboard row in `HomePage.vue` with three cards:
  - **Warehouse snapshot:** shows online LED controller count and up to 6 active highlighted bins/zones from `useWarehouseLedsStore`.
  - **Offline queue status:** shows online/offline badge and pending mutation count from `services/offline/orbitSync`; uses the active variant when offline or pending.
  - **Today's crew availability:** shows active crew member count and a sample list from `useCrewStore`.
- Added i18n keys for the new cards in `en.js` and `sv.js`.

## 7. Job planning visibility

**Current state:** Jobs are primarily a list/table.
**Improvement:**
- Add a **summary metric row** showing total jobs and counts by status.
- Add friendly **empty state** messages for the jobs table.
- Add a **calendar view** toggle.
- Highlight jobs with missing requirements or crew conflicts.
- Show a **packing progress bar** on the job detail page.
- Surface **missing certifications** for assigned crew.

**Status:** In progress.
- Jobs page has a status summary card row and contextual empty-state labels.
- Added i18n key `noJobs` in English and Swedish.
- Added a **Table / Calendar** view toggle on `JobsPage.vue`; calendar view uses `QDate` with event dots for job start dates and a side panel listing jobs for the selected date.

## 8. Mobile table adaptation

**Current state:** Tables can overflow on small screens.
**Improvement:**
- Use Quasar's `grid` table mode on phones.
- Convert dense tables to card lists on mobile.
- Ensure horizontal padding follows `--ec-space-sm` (8px) on mobile.

**Status:** Done. Added `useCompactGrid(1024)` and custom `item` card templates to remaining tables in `FinancePage.vue`, `CrewPage.vue`, `ProfilePage.vue`, and `WarehouseLedsPage.vue`. `ProjectsPage.vue` switched to `useCompactGrid` for consistency. Existing adapted pages include `ActivityPage.vue`, `CompaniesPage.vue`, `DefectsPage.vue`, `AuthPage.vue`, `InventoryPage.vue`, `JobsPage.vue`, `MaintenancePage.vue`, `PersonsPage.vue`, `ScanPage.vue`, `SettingsPage.vue`, and `VenuesPage.vue`.

## 9. Settings grouping

**Current state:** Settings has many tabs and fields.
**Improvement:**
- Group related settings into **Cards** instead of one long form.
- Add **integration health indicators** (connected / disconnected chips).
- Show inline validation hints using `Body / Muted`.

**Status:** Done.
- Added `.ec-page-title`, `.ec-card`, `.ec-card-title`, `.ec-chip--success/--danger/--warning/--info`, `.ec-text-muted`, and `:no-data-label` messages.
- Grouped the long single-card tabs into multiple `ec-card`s, each with an `.ec-card-title`:
  - **Auth:** Users · API Keys · Single Sign-On (OIDC/SAML provider blocks are now nested `ec-card`s).
  - **Company:** Organization & branding · Address & contact.
  - **Inventory:** Location types · Product brand/manufacturer defaults · Category prefill.
  - **Email:** header card + Resend · SMTP connection · Sender info (form preserved).
  - **Integrations:** one top-level `ec-card` per integration — **Eventory**, **Production Planner**, **Twenty**, **Stockwire** — instead of a single wrapper card. Eventory and Stockwire (which support multiple instances) use nested `ec-card--inset` cards for each instance. OIDC/SAML providers in the SSO tab are also nested `ec-card--inset` cards.
- **LLM:** split into *Endpoint* and *Model & Configuration* cards.
- **About:** split into *System information* and *Updates & maintenance* cards (plus the header card).
- Integration health: a persistent status chip now appears for **every** integration (Eventory, Production Planner, Twenty, Stockwire) via a new `integrationHealth()` helper — `Connected` (green) when a test passed, `Failed` (red) when it failed, `Not tested` (amber) when enabled but untested, and `Disabled` (neutral) when toggled off. The Warehouse LEDs device status badge uses `ec-chip--success/--danger`.
- Inline validation/muted hints: replaced all `text-grey-6/7/8` caption classes with the token-aligned `.ec-text-muted` (Body / Muted) across `SettingsPage.vue`, `NotificationsSettings.vue`, and `CalendarFeedsSettings.vue`.

## 10. Route planner enhancements

**Current state:** Route planner shows stops and a map export.
**Improvement:**
- Show estimated drive time per stop.
- Warn when a job's equipment exceeds vehicle capacity.
- Add an "optimize route" action (external service).

**Status:** Started. Added `.ec-page-title`, `.ec-card`, `.ec-empty-state`, and a route status metric row (total, planned, in progress, completed). Empty states for no routes, no stops, and no selection now use the design system.

## 11. Accessibility hardening

**Current state:** Focus-visible is partially covered.
**Improvement:**
- Ensure all interactive elements have a visible focus ring.
- Verify 4.5:1 contrast for all body text.
- Add a `prefers-reduced-motion` variant for animations.

**Status:** Done.
- Expanded global `:focus-visible` styles in `frontend/src/css/app.css` to cover links, buttons, inputs, selects, textareas, tabbable elements, Quasar buttons, items, tabs, radios, checkboxes, toggles, btn-toggles, expansion items, fields, sliders, chips, pagination, stepper tabs, carousel controls, tree nodes, and menu items.
- Added a `prefers-reduced-motion: reduce` media query that disables animations and transitions for users who request reduced motion.
- Replaced low-contrast Quasar `text-grey-*` muted captions with `.ec-text-muted` (which uses `--ec-text-secondary`) in `FinancePage.vue`, `CrewPage.vue`, `ProfilePage.vue`, `WarehouseLedsPage.vue`, and `ProjectsPage.vue`.
- Added `scripts/verify_contrast.py` to check WCAG contrast ratios for design tokens against both dark and light surfaces. All token pairs pass the required thresholds.

## How to use Penpot for these

1. Open the `Stockwire Library` in Penpot (see `design/penpot/IMPORT_GUIDE.md`).
2. Create a new file for each improvement area (e.g., `Stockwire / Dashboard Improvements`).
3. Enable the shared library.
4. Build variants using the components and tokens.
5. Share the Penpot link or export PNGs for review.
6. Once approved, implement the changes in the Quasar frontend and update tokens if needed.
