# Quotes + Vendor Catalog — Implementation Plan

Status: Implementation in progress on `feat/quotes-vendor-catalog` — Phases 1–6 implemented (backend + frontend + tests). Not yet committed.

## Goal

Add a **quotes generator** (for equipment **and** labour installation jobs) inside Stockwire, plus a **pluggable vendor-equipment import** subsystem that builds a separate, quotable product catalog — with a deferred web scraper.

## Locked decisions

| Area | Decision |
|---|---|
| Build where | Inside Stockwire (reuse `pdf_service` report engine + existing data) |
| Quote contents | Equipment **+ labour** + purchased/sold items (unified) |
| Tax | VAT only (25%, configurable) |
| Quote document | **Editable `ReportTemplate`** (designed in ReportsPage), generated via the report engine |
| Sync | **Twenty only** (Eventory stays the *operational* job/rental sync; quote document not sent to Eventory) |
| Quote entity | Job + `status="quotation"` (`quote_no = job_code`); **no new quote table** |
| Vendor catalog | **Separate** `vendor_products` table (buy/sell items, distinct from owned stock) |
| Vendor items | Cost + **default markup**, **editable per quote row** |
| Importer | **Plugin architecture** (generic configurable + specific vendor plugins) |
| Import review | **Preview + approve** first; auto-update later |
| Scraper | **Deferred** (API + CSV first) |

## Data model

- `JobCrewRequirement.hours` (nullable float) + migration/schema/form → labour line = `hourly_rate × quantity × hours` (fallback: job-duration × quantity).
- `JobRequirement`: add nullable `vendor_product_id` (→ `vendor_products`) **and** editable `unit_price` (Numeric). A row is rental (via `product_id`) **or** purchase (via `vendor_product_id`); `unit_price` defaults from the source and is editable per row (markup applied for vendor rows).
- **New `vendor_products`**: `sku`, `name`, `brand`, `category`, `description`, `dimensions`, `image_url`, `unit_cost` (purchase cost), `currency` (price currency, with a per-import `default_currency` fallback), `stock_quantity`, `availability` (for cross-supplier comparison), `vendor_id` (→ `companies`), `external_reference`, `source_plugin`, `last_synced_at`, `raw_payload` (JSON for re-mapping).
- **Settings**: `quotes.default_markup_pct` (e.g. 30%) + optional per-vendor override; `quotes.vat_rate` (default 0.25).

## Quote generation (report engine, editable)

- `pdf_service.resolve_context("job")` extended to emit, per `JobRequirement`: source type (rental/purchase), resolved name/sku, `quantity`, `unit_price`, line total, and `unit_cost` (for margin on purchase rows); plus `crew_requirements` lines (rate × qty × hours); plus a `quote` block: `quote_no`, `quote_date`, `subtotal`, `vat_rate`, `vat_amount`, `total`.
- **Seed a default "Quote" `ReportTemplate`** in the existing template store, renderable/editable in ReportsPage (line-items table bound to the context). "Generate quote" = `generate_report(entity_type="job", template="quote")` → PDF.

## Quote builder UX (rental + installation unified)

- On `JobDetailPage` (or a Quote tab): a line-item picker that searches **both** owned `Products` (rental) and `vendor_products` (buy/sell); add rows; edit `unit_price`/markup per row; manage `crew_requirements` (with `hours`).
- Buttons: **Generate quote** (PDF, sets `status="quotation"`) and **Sync quote to Twenty**.

## Twenty sync (reuse existing infra)

- Extend the existing `integrations/sync_engine` + `outbound.py` (already syncs jobs/companies/persons to Twenty) so that a job in `quotation` status also pushes the **quote PDF (bytes) + `quote_no` + totals** to Twenty — e.g. as an activity note/attachment on the synced opportunity/company. No new scheduler needed; piggybacks on `auto_sync.py` and outbound background tasks.

## Importer plugin architecture (vendor catalog)

- `BaseImporterPlugin` (`id`, `label`, `source_type` `api`/`csv`, `fetch`, `normalize → VendorEquipmentRecord`, `field_map`).
- `GenericApiPlugin` / `GenericCsvPlugin`: fully configurable via `field_map` in `AppSetting` JSON (same pattern as the Eventory/Twenty integration config) → any source with no code change.
- **Specific vendor plugins** subclass the base; registered in a simple plugin registry (new file = new plugin).
  - `AurdelPricesPlugin` (`aurdel_prices`): fetches Aurdel's `/Prices/getPrice` XML price file using `customerid`/`companyid`/`apikey`/`customerpassword`/`database`/`filetype`/`language` from config; parses the XML into normalised records. **`customerid` must include the reseller prefix** (e.g. `ADSE-C005985`), while `companyid` is just the 4-letter reseller code (e.g. `ADSE`). `filetype`/`language` are sent only when the user chooses them — leaving them blank uses the server's default format (requesting `filetype=extended` returns an empty `<PriceList>` for customers without extended data, so the plugin auto-retries without them). Auth note: the published OpenAPI spec lists the password param name with a trailing space (`customerpassword `) — the plugin sends the trimmed key.
- **CSV/API field-map auto-detection:** when a source's `field_map` is left empty, the generic plugins infer a mapping from the response headers/keys using a built-in alias table (`products-100.csv` imports out-of-the-box: Name→name, Price→unit_cost, Currency→currency, Stock→stock_quantity, Availability→availability, EAN/Internal ID→sku/external_reference).
- **Redirect-safe fetch:** `httpx.get` in the generic plugins and the Aurdel plugin use `follow_redirects=True` (handles Google Drive `303` link sharing).
- Endpoints: `POST /vendor-products/preview` (run plugin → normalized rows), `POST /vendor-products/apply` (upsert approved rows; match by `external_reference`/SKU → update, else create).
- **Per-plugin config schema:** each plugin declares `config_schema` (list of field descriptors: `key`, `label`, `type` `text|url|secret|number|select`, `required`, `default`, `options`, `help`). The `/vendor-catalog/plugins` endpoint returns this so the UI renders the right fields dynamically. Plugins with a fixed endpoint (e.g. Aurdel) omit `url` from the schema and hardcode it — the user never edits it; only those that genuinely need a user-supplied URL (generic CSV/API) include a `url` field.
- UI: **Vendor catalogs** admin page — pick a plugin, fill in its **plugin-specific fields** (rendered from `config_schema`; e.g. Aurdel shows Customer ID, Company ID, API key/password, Database/File type/Language selects, Default currency), tweak `field_map` (pre-filled with the plugin's `default_field_map`), preview/edit/approve, import; manage vendor companies. Products table exposes currency, stock and availability columns for supplier comparison.

## Phased delivery

1. `JobCrewRequirement.hours` (+ migration/schema/form) and `JobRequirement` (`vendor_product_id`, `unit_price`) + settings keys.
2. Quote context extension in `pdf_service` + seed default Quote `ReportTemplate`.
3. Quote builder UX on `JobDetailPage` (unified rental/purchase/labour, editable price/markup).
4. `vendor_products` model + importer plugin base, generic + first specific vendor plugins, preview/apply endpoints, Vendor catalogs UI.
5. Twenty quote-sync via existing `sync_engine`/`outbound`.
6. i18n (en/sv), tests, ruff.

## Deferred / out-of-scope (basic plans for later)

- **Web scraper plugin:** add `ScraperPlugin` (`source_type="scraper"`). Server-side fetch of target URL(s); parse HTML with `lxml`/`BeautifulSoup`/`trafilatura`; extract product cards via CSS/XPath selectors stored in the plugin config (like `field_map`) → `VendorEquipmentRecord`. Reuses normalize/upsert + preview/approve. *Risks:* layout changes break selectors, anti-bot/Cloudflare blocking, **ToS/legal review required** before enabling. Build only after API+CSV proven.
- **Scheduled vendor-catalog auto-sync:** extend the existing `integrations/auto_sync.py` scheduler (already a 60s-check loop that runs the Twenty CRM sync) with a `_run_vendor_catalog_sync` stage. Each configured source with `auto_sync_interval` runs its plugin on schedule and upserts `vendor_products` (auto, after the initial preview/approve establishes mapping). Add a per-source "Auto-sync enabled + interval" toggle in the Vendor catalogs UI; notify on failures.
- **Eventory quote sync:** explicitly **not** done (quote document → Twenty only; Eventory remains the operational job/rental pack-list sync).
- **Best-purchase / supplier comparison (next step):** once multiple vendors supply overlapping items (matched by SKU/EAN/`external_reference`, or fuzzy name match), add a "Best purchase" action on a quote/job:
  - Take the job's `JobRequirement` purchase rows (+ any selected rental-equivalent buy items) and, for each needed item, find candidate `vendor_products` across vendors with `availability != "out"`/`stock_quantity > 0`.
  - Produce two recommendations: (a) **single-cheapest supplier** — one vendor that can supply the most lines at the lowest total (in a common currency, with FX conversion if needed), and (b) **multi-supplier optimiser** — for each line pick the cheapest in-stock vendor, sum totals, and report how many suppliers are required.
  - Output: a comparison table (vendor × line: unit cost, currency, stock, availability, line total) plus a recommended purchase basket (vendor + item + qty + cost), reusable as a purchase order draft. Cross-currency totals need a small FX-rate table/setting (or assume the per-import `default_currency` where possible). No UI committed yet — design after the catalog has ≥2 vendors populated.
- **Vendor-catalog product merging (cross-supplier clustering):** the Vendor-catalog UI should cluster/merge distinct `vendor_products` that represent the same physical item into a single product card, so incoming/restock data **and** prices across suppliers are visible together. Matching is the same reference-key logic already used by the purchasing comparison/PO builder (`external_reference`, `sku`, `supplier_item_number`, `vendor_item_number`, with fuzzy-name fallback) — e.g. an item stored as `sku="U7-Lite"` by one supplier and `external_reference="U7-Lite"` by another currently appear as two separate catalog rows and should collapse into one card listing both suppliers' price/stock/ETA. Backlog item from the PO-build review: "add merging in the vendor catalog to easily see that data there."

## Notes / risks

- Keeping vendor items in a separate `vendor_products` table (your choice) means the quote line-item resolver must handle both FKs; the report context and builder do this.
- `unit_price` is the single source of truth for the quote line (defaults computed at add-time, then editable); satisfies "default markup, editable per row" without a separate quote-line table.
- All of this lands on `feat/quotes-vendor-catalog`, independent of `label-printing`.
