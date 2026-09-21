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

**Status:** Started. Added `.ec-page-title`, `.ec-card`, `.ec-chip--success`, `.ec-chip--danger`, and `:no-data-label` messages. Grouped organization/profile fields and integration health into styled cards with status chips.

## 10. Route planner enhancements

**Current state:** Route planner shows stops and a map export.
**Improvement:**
- Show estimated drive time per stop.
- Warn when a job's equipment exceeds vehicle capacity.
- Add an "optimize route" action (external service).

**Status:** Done.
- Added per-stop cargo weight/volume to `RouteStopRead` (`cargo_weight_kg`, `cargo_volume_m3`) computed from job requirements, so the route detail carries the data needed for capacity checks.
- **Capacity warning:** a route may carry multiple vehicles, and **all vehicles on a route serve all stops** (a vehicle that only needs a subset of stops should be put on its own separate route). The vehicles share the load, so a stop is only flagged when its cargo exceeds the **combined** capacity of every assigned vehicle (trailers use `max_payload_kg`; effective volume from `max_volume_m3` or interior dimensions) — never per-vehicle. The warning tooltip states **whether weight, volume, or both** are exceeded. With zero vehicles the stop shows a neutral "no vehicle assigned" hint; with multiple vehicles a "All N vehicles serve this stop" chip is shown. **Per-stop vehicle assignment UI was removed** — vehicles are assigned at the route level only.
- **Estimated drive time per stop:** new backend module `app/domain/route_planner/routing.py` geocodes venue addresses (Nominatim/OSM) and calls OSRM for per-leg duration/distance. New `GET /routes/{id}/drive-times` returns leg times; the UI shows a chip per stop (`X min · Y km`). Degrades gracefully (`available=False` + note) when routing is disabled or addresses/coordinates are missing.
- **Optimize route:** new `POST /routes/{id}/optimize` reorders stops via nearest-neighbour on an OSRM duration matrix (origin optional). UI adds an "Optimize route" button (disabled for <2 stops) plus an optional start-address input that **defaults to the company address** from company settings (the user can override or clear it); drive times refresh after optimizing.
- **Route preview:** new `GET /routes/{id}/locations` resolves coordinates for the optional origin and each stop (stored venue coords first, then geocoding) and reports whether each was resolved. The "Preview route" button renders an **interactive Leaflet map** (OSM tiles, no API key) with the **start marked green** ("S"), **equipment pickup zones marked dark** ("P"), and each stop marked with a **distinct colored numbered pin**, plus hover tooltips and a color legend; stop list colors match the map so it's easy to see which stop is which. The map is **locked by default** (pan/zoom disabled to avoid accidental movement) with an **unlock button** and **reset-view button**. Unresolved addresses are flagged in the list below.
- **Zone geolocation + equipment pickup points:** inventory `zones` gained `latitude`/`longitude` plus a **structured address** (`address_line1`, `address_line2`, `postal_code`, `city`, `country`) consistent with venues/companies. Coordinates are **auto-filled by geocoding the address on save** (backend `_maybe_geocode_zone`, same as venues) only when no coordinates are set, so manually entered coordinates are never overwritten; the user can still edit lat/lon. A sub-zone with no coordinates **inherits them (and the address) from its parent** (effective fields resolved on read). The route planner auto-derives **pickup zones from the jobs' equipment** (devices' storage zones) and inserts them as **leading waypoints** before the delivery stops in both drive-time and optimize calculations (`GET /drive-times` and `/locations` now return `pickup_zones`). The zone editor (`ZoneDialog`, which merges the former `LocationDialog` and `ZonePropertiesDialog`) exposes all zone fields — name/code, coordinates + structured address, dimensions, position, rotation, color, type/parent, identifiers, and quick presets — fully translated, and renders a **Google Maps embed preview** (same pattern as venues/companies/jobs) of the zone's location, falling back to the inherited parent coordinates when the zone has none.
- Backend config (`app/config.py`): `routing_enabled`, `routing_provider`, `routing_osrm_url`, `routing_nominatim_url`, `routing_timeout_seconds`.
- i18n keys (en/sv): `cargoWeight`, `cargoVolume`, `overCapacity`, `overCapacityDetail`, `noVehicleForStop`, `driveTime`, `driveDistance`, `driveTimeUnavailable`, `fromStart`, `optimizeRoute`, `optimizing`, `optimizedRoute`, `originAddress`, `previewRoute`, `routePreview`, `previewNoMap`, `start`, `unresolvedAddress`, `previewUnresolvedHint`.
- NOTE: Drive-time/optimize depend on external OpenStreetMap services (Nominatim + OSRM). **Venues now store `latitude`/`longitude`** (nullable; set manually in the venue dialog or auto-filled on save when the address geocodes). Routing prefers stored coordinates and only falls back to live geocoding of the address. A haversine straight-line matrix is used as a fallback when the OSRM table endpoint is unreachable, so optimization still works once coordinates exist. If a venue has neither coordinates nor a geocodable address, the optimize/drive-time endpoints return a clear 409/“unavailable” message. Migration `0079_venue_coordinates` adds the two columns.

## 11. Accessibility hardening

**Current state:** Focus-visible is partially covered.
**Improvement:**
- Ensure all interactive elements have a visible focus ring.
- Verify 4.5:1 contrast for all body text.
- Add a `prefers-reduced-motion` variant for animations.

**Status:** Partially done / revised.
- Added a `prefers-reduced-motion: reduce` media query that disables animations and transitions for users who request reduced motion.
- Replaced low-contrast Quasar `text-grey-*` muted captions with `.ec-text-muted` (which uses `--ec-text-secondary`) in `FinancePage.vue`, `CrewPage.vue`, `ProfilePage.vue`, `WarehouseLedsPage.vue`, and `ProjectsPage.vue`.
- Added `scripts/verify_contrast.py` to check WCAG contrast ratios for design tokens against both dark and light surfaces. All token pairs pass the required thresholds.
- NOTE: A broad global `:focus-visible` override was added then reverted. It stacked multiple focus boxes on complex components like `q-field` (the browser/Quasar default outline plus the custom one). Focus styling is now left to Quasar's built-in defaults, which already provide visible focus indicators.

## 12. Scan experience — tactile polish

**Current state:** Scan page is functional but could be more tactile.
**Improvement:**
- Increase touch targets to at least 64px.
- Add haptic-compatible feedback states (visual + optional vibration).
- Show device/product thumbnail after a successful scan.
- Use `Scanner / Target` and `Scan Feedback / Success` components from the library.

**Status:** Done.
- Created `frontend/src/components/ScannerTarget.vue` and `frontend/src/components/ScanFeedback.vue` matching the library specs (`design/penpot/components.md` §Scanner).
- `ScanPage.vue` now renders the `ScannerTarget` component; on a scan result a `ScanFeedback` (success/error) with optional product/device thumbnail is shown with a pulse animation.
- Added tactile feedback: visual pulse on the target plus `navigator.vibrate()` haptics on success/error (gracefully no-op when unsupported).
- Increased touch targets: primary scan submit button and scan action toggles to 64px min-height; toggles to 56px.
- Unified off-brand banner colors (`bg-teal-8`/`bg-amber-8`/`bg-positive`/`bg-negative`) with the brand-aligned `ec-banner--success/warning/info/danger` utility classes (also applied to `FieldScanDialog.vue`).

## How to use Penpot for these

1. Open the `Stockwire Library` in Penpot (see `design/penpot/IMPORT_GUIDE.md`).
2. Create a new file for each improvement area (e.g., `Stockwire / Dashboard Improvements`).
3. Enable the shared library.
4. Build variants using the components and tokens.
5. Share the Penpot link or export PNGs for review.
6. Once approved, implement the changes in the Quasar frontend and update tokens if needed.
