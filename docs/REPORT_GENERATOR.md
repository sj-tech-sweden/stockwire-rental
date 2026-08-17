# Report Generator

> Last reviewed: 2026-08-14

## Overview

The Report Generator enables users to create print-ready PDFs and web documents using pre-designed templates or custom layouts. It features a PDF background letterhead engine, a dual-mode template editor (visual block builder + code editor), and a catalog of predefined operational document templates.

**Frontend:** Settings > Reports tab, Job Detail > Export button  
**Backend:** `/api/v1/reports/*`

---

## Features

- **PDF Letterhead Engine** — Upload company letterhead PDFs and calibrate printable margins visually
- **Dual Template Editor** — Visual block builder alongside a raw JSON editor with live data preview
- **Predefined Templates** — 10 built-in templates for warehouse, asset management, and logistics documents
- **Report Generation** — Render templates against real job, device, or product data and export as PDF
- **Generation Logs** — Track all generated reports with audit trail

---

## Concepts

### Letterheads

A letterhead is a branded PDF background that gets merged behind generated report content:

- Uploaded as a single-page or multi-page PDF
- Has configurable margins (top, bottom, left, right in mm)
- One letterhead can be marked as the default
- Templates can reference a specific letterhead or use the default

### Report Templates

Templates define the structure and content of generated reports:

- Stored as JSON flowable definitions (`body_json`)
- Categorized as `warehouse`, `asset`, `logistics`, or `custom`
- Linked to a data source type (`job`, `device`, `product`, `inventory`)
- Built-in templates are read-only; custom templates can be created/edited

### Flowables

Flowables are the building blocks of a report template:

| Type | Description | Key Fields |
|---|---|---|
| `heading` | Section heading | `text`, `level` (1-3) |
| `paragraph` | Body text | `text`, `style` |
| `table` | Data table from array | `source`, `columns[]` |
| `key_value` | Label-value grid | `source`, `fields[]` |
| `spacer` | Vertical space | `height_mm` |
| `line` | Horizontal rule | `width_percent` |
| `barcode` | Barcode/QR code | `value`, `barcode_type` |
| `page_break` | Force new page | — |

### Data Sources

Each template targets a specific entity type. The PDF service resolves context data from the database:

| Data Source | Context Keys | Available Fields |
|---|---|---|
| `job` | `job`, `customer`, `venue` | job_code, description, status, dates, sales_price, customer name/email/phone, venue name/address |
| `device` | `device`, `product` | asset_tag, serial_number, status, condition, product name/sku/category/weight |
| `product` | `product` | name, sku, category, brand, daily_rate, weight_kg |
| `inventory` | `products` | Aggregate product list |

### Template Format (body_json)

Templates are stored as JSON with this structure:

```json
{
  "page_size": "A4",
  "margin_top_mm": 20,
  "margin_bottom_mm": 20,
  "margin_left_mm": 20,
  "margin_right_mm": 20,
  "flowables": [
    { "type": "heading", "text": "Case Manifest: {{ device.asset_tag }}", "level": 1 },
    { "type": "spacer", "height_mm": 5 },
    { "type": "key_value", "source": "device", "fields": [
      { "key": "asset_tag", "label": "Case ID" },
      { "key": "serial_number", "label": "Serial Number" }
    ]},
    { "type": "line" },
    { "type": "paragraph", "text": "Generated: {{ now }}", "style": "small" }
  ],
  "styles": {
    "heading1": { "font_size": 16, "bold": true }
  }
}
```

---

## Predefined Templates

### Warehouse & Case Documents

| Template | Description |
|---|---|
| Case Lid / Insert Manifest | Contents, cables, accessories, and serial numbers in a flight case |
| Case Contents Summary (No Serials) | Product counts only for quick verification |
| Kit Component Breakdown | Expands bundle SKUs into granular parts lists |
| Zone-Based Pick List | Grouped by warehouse shelf/rack for efficient pick paths |
| Return Check-In & Missing Items Audit | Scan sheet for returned items with OK/Missing/Damaged marking |
| Vehicle Load & Weight Summary | Weight, volume, and case count for transport compliance |

### Asset Management & Operations

| Template | Description |
|---|---|
| Asset Utilization & Idle Stock | Usage ratios over time, high-performing vs. dead stock |
| Overdue & Unreturned Items | Unreturned gear grouped by customer with days overdue |
| Damage & Maintenance Log | Historical damage, repair costs, inspection schedules |

### Logistics & Customer Handover

| Template | Description |
|---|---|
| On-Site Handover & Delivery Sign-Off | Delivery receipt with site notes and signature line |
| Venue Compliance & Safety Packet | Safety certificates and inspection records for equipment |

---

## API Endpoints

### Letterheads

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/reports/letterheads` | user | List all letterheads |
| `POST` | `/api/v1/reports/letterheads` | editor | Create letterhead (JSON body) |
| `PUT` | `/api/v1/reports/letterheads/{id}` | editor | Update margins/settings |
| `DELETE` | `/api/v1/reports/letterheads/{id}` | editor | Delete letterhead |
| `POST` | `/api/v1/reports/letterheads/upload` | editor | Upload PDF + create letterhead (multipart) |

### Templates

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/reports/templates` | user | List templates (filter by `category`, `data_source_type`) |
| `GET` | `/api/v1/reports/templates/{id}` | user | Get template with full body_json |
| `POST` | `/api/v1/reports/templates` | editor | Create custom template |
| `PUT` | `/api/v1/reports/templates/{id}` | editor | Update template (not builtin) |
| `DELETE` | `/api/v1/reports/templates/{id}` | editor | Delete template (not builtin) |
| `GET` | `/api/v1/reports/templates/{id}/preview` | user | Preview resolved context + flowable JSON |

### Generation

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/reports/generate` | user | Generate a report (PDF/HTML/CSV) |
| `GET` | `/api/v1/reports/logs` | user | List generation logs (filter by `entity_type`, `entity_id`) |

### Data Sources

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/reports/data-source/{type}/schema` | user | Get available Jinja2 variables for a data source |

---

## PDF Rendering Pipeline

```
1. Resolve entity context from database
         ↓
2. Parse template body_json
         ↓
3. Render Jinja2 variables in flowable text
         ↓
4. Build ReportLab flowables (Paragraphs, Tables, etc.)
         ↓
5. Generate content PDF with configured margins
         ↓
6. Overlay letterhead background PDF (if configured)
         ↓
7. Return final print-ready PDF bytes
```

### Margin Conversion

Margins are specified in millimeters and converted to PDF points:
- `1 mm = 2.83465 pt`
- Default margins: 20mm on all sides (56.69pt)

### Letterhead Overlay

The overlay process uses `pypdf`:
1. Read the letterhead background PDF
2. Read the generated content PDF
3. For each content page, merge it on top of the corresponding background page
4. If the letterhead has fewer pages than content, extra content pages are added without background
5. If the letterhead has more pages than content, extra background pages are included

---

## Frontend Components

### Settings Page > Reports Tab

- **LetterheadManager** — Upload, list, and configure letterheads
- **LetterheadCalibrator** — Interactive visual margin calibrator with live preview
- **ReportTemplateManager** — List templates, open designer for edit/create

### Job Detail > Export Button

- **ReportExportDialog** — Select template, choose format, preview, and generate

### Report Designer (Dual Mode)

**Visual Mode:**
- Block palette with drag-to-add flowable blocks
- Canvas showing block order and content
- Property editor for selected block

**Code Mode:**
- JSON editor for direct `body_json` editing
- Variable picker sidebar showing available data source fields

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PDF_REPORTS_ENABLED` | `true` | Enable/disable report generation |
| `PDF_DEFAULT_MARGIN_TOP_MM` | `20.0` | Default top margin in mm |
| `PDF_DEFAULT_MARGIN_BOTTOM_MM` | `20.0` | Default bottom margin in mm |
| `PDF_DEFAULT_MARGIN_LEFT_MM` | `20.0` | Default left margin in mm |
| `PDF_DEFAULT_MARGIN_RIGHT_MM` | `20.0` | Default right margin in mm |

### Dependencies

| Package | Purpose |
|---|---|
| `reportlab` | PDF generation from flowable definitions |
| `pypdf` | PDF reading and letterhead overlay merging |

---

## Database Schema

### letterheads

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(120) unique | |
| `is_default` | Boolean | One letterhead is default |
| `asset_file_id` | FK → asset_files | References uploaded PDF |
| `page_count` | Integer | Pages in the PDF |
| `margin_top_mm` | Numeric(6,2) | Default 20.0 |
| `margin_bottom_mm` | Numeric(6,2) | Default 20.0 |
| `margin_left_mm` | Numeric(6,2) | Default 20.0 |
| `margin_right_mm` | Numeric(6,2) | Default 20.0 |
| `created_at` | DateTime(tz) | |

### report_templates

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(200) | |
| `category` | String(50) | warehouse, asset, logistics, custom |
| `description` | Text | |
| `letterhead_id` | FK → letterheads | null = use default |
| `body_json` | Text | JSON flowable definitions |
| `data_source_type` | String(50) | job, device, product, inventory |
| `is_builtin` | Boolean | True for seeded templates |
| `is_enabled` | Boolean | |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | |

### generated_report_logs

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `template_id` | FK → report_templates | |
| `entity_type` | String(50) | job, device, product |
| `entity_id` | Integer | |
| `asset_file_id` | FK → asset_files | Generated PDF |
| `generated_by_user_id` | FK → users | |
| `format` | String(10) | pdf, html, csv |
| `created_at` | DateTime(tz) | |

---

## Implementation Files

| File | Purpose |
|---|---|
| `backend/app/domain/reports/models.py` | SQLAlchemy models |
| `backend/app/domain/reports/schemas.py` | Pydantic schemas |
| `backend/app/domain/reports/router.py` | FastAPI endpoints |
| `backend/app/domain/reports/seed.py` | 10 predefined templates |
| `backend/app/services/pdf_service.py` | ReportLab + pypdf engine |
| `backend/alembic/versions/20260813_0071_*.py` | Database migration |
| `frontend/src/stores/reports.js` | Pinia store |
| `frontend/src/components/LetterheadManager.vue` | Letterhead management UI |
| `frontend/src/components/LetterheadCalibrator.vue` | Visual margin calibrator |
| `frontend/src/components/ReportDesigner.vue` | Dual-mode template editor |
| `frontend/src/components/ReportTemplateManager.vue` | Template list for settings |
| `frontend/src/components/ReportExportDialog.vue` | Export modal |
