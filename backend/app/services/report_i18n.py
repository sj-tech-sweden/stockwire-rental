"""Lightweight translations for report generation.

The frontend passes the user's preferred language when generating a report. Fixed
strings that come from the backend (column labels, static headings, dates, etc.)
are translated here. User-editable custom template text is rendered as-is.
"""

from __future__ import annotations

from datetime import date, datetime

_REPORT_STRINGS = {
    "en": {
        "generated": "Generated",
        "case_manifest": "CASE MANIFEST",
        "case_contents": "CASE CONTENTS",
        "kit_component_breakdown": "KIT COMPONENT BREAKDOWN",
        "zone_based_pick_list": "ZONE-BASED PICK LIST",
        "return_check_in": "RETURN CHECK-IN & MISSING ITEMS",
        "vehicle_load": "VEHICLE LOAD & WEIGHT SUMMARY",
        "asset_utilization": "ASSET UTILIZATION & IDLE STOCK",
        "overdue_unreturned": "OVERDUE & UNRETURNED ITEMS",
        "damage_maintenance": "DAMAGE & MAINTENANCE LOG",
        "handover_sign_off": "ON-SITE HANDOVER & SIGN-OFF",
        "venue_compliance": "VENUE COMPLIANCE & SAFETY PACKET",
        "job_summary_card": "JOB SUMMARY CARD",
        "contents": "Contents",
        "components": "Components",
        "accessories": "Accessories",
        "products": "Products",
        "devices": "Devices",
        "requirements": "Requirements",
        "maintenance_records": "Maintenance Records",
        "defect_reports": "Defect Reports",
        "case_id": "Case ID",
        "serial_number": "Serial Number",
        "status": "Status",
        "condition": "Condition",
        "product": "Product",
        "sku": "SKU",
        "category": "Category",
        "qty": "Qty",
        "quantity": "Qty",
        "required": "Required",
        "kit_name": "Kit Name",
        "brand": "Brand",
        "location": "Location",
        "weight_kg": "Weight (kg)",
        "total_weight_kg": "Total Weight (kg)",
        "job_code": "Job Code",
        "customer": "Customer",
        "venue": "Venue",
        "start_date": "Start Date",
        "end_date": "End Date",
        "notes": "Notes",
        "description": "Description",
        "name": "Name",
        "asset_tag": "Asset Tag",
        "maintenance_type": "Type",
        "scheduled_date": "Scheduled",
        "completed_date": "Completed",
        "severity": "Severity",
        "title": "Title",
        "date": "Date",
        "yes": "Yes",
        "no": "No",
        "page": "Page",
        "of": "of",
        "no_data": "No data",
    },
    "sv": {
        "generated": "Genererad",
        "case_manifest": "FLIGHTCASE-INNEHÅLL",
        "case_contents": "FLIGHTCASE-INNEHÅLL",
        "kit_component_breakdown": "KIT-KOMPONENTER",
        "zone_based_pick_list": "ZONBASERAD PLOCKLISTA",
        "return_check_in": "RETURGRANSKNING & SAKNADE DELAR",
        "vehicle_load": "FORDONSLAST & VIKT",
        "asset_utilization": "TILLGÅNGSANVÄNDNING & OBEGAGNAT",
        "overdue_unreturned": "FÖRSENADE & EJ ÅTERLÄMNADE",
        "damage_maintenance": "SKADE- & UNDERHÅLLSLOGG",
        "handover_sign_off": "PLATSÖVERLÄMNING & KVITTO",
        "venue_compliance": "LOKAL- & SÄKERHETSPAKET",
        "job_summary_card": "JOBSAMMANDRAG",
        "contents": "Innehåll",
        "components": "Komponenter",
        "accessories": "Tillbehör",
        "products": "Produkter",
        "devices": "Enheter",
        "requirements": "Krav",
        "maintenance_records": "Underhållsposter",
        "defect_reports": "Skaderapporter",
        "case_id": "Case ID",
        "serial_number": "Serienummer",
        "status": "Status",
        "condition": "Skick",
        "product": "Produkt",
        "sku": "SKU",
        "category": "Kategori",
        "qty": "Antal",
        "quantity": "Antal",
        "required": "Obligatorisk",
        "kit_name": "Kit-namn",
        "brand": "Märke",
        "location": "Plats",
        "weight_kg": "Vikt (kg)",
        "total_weight_kg": "Total vikt (kg)",
        "job_code": "Jobbkod",
        "customer": "Kund",
        "venue": "Lokal",
        "start_date": "Startdatum",
        "end_date": "Slutdatum",
        "notes": "Anteckningar",
        "description": "Beskrivning",
        "name": "Namn",
        "asset_tag": "Tillgångstagg",
        "maintenance_type": "Typ",
        "scheduled_date": "Planerat",
        "completed_date": "Utfört",
        "severity": "Allvarlighetsgrad",
        "title": "Titel",
        "date": "Datum",
        "yes": "Ja",
        "no": "Nej",
        "page": "Sida",
        "of": "av",
        "no_data": "Ingen data",
    },
}


def _normalize_language(language: str | None) -> str:
    value = str(language or "en").lower().split("-")[0]
    return value if value in _REPORT_STRINGS else "en"


# Map common English phrases used in seeded/custom templates to translation keys.
_ENGLISH_PHRASE_TO_KEY = {
    "CASE MANIFEST": "case_manifest",
    "CASE CONTENTS": "case_contents",
    "KIT COMPONENT BREAKDOWN": "kit_component_breakdown",
    "ZONE-BASED PICK LIST": "zone_based_pick_list",
    "RETURN CHECK-IN & MISSING ITEMS": "return_check_in",
    "VEHICLE LOAD & WEIGHT SUMMARY": "vehicle_load",
    "ASSET UTILIZATION & IDLE STOCK": "asset_utilization",
    "OVERDUE & UNRETURNED ITEMS": "overdue_unreturned",
    "DAMAGE & MAINTENANCE LOG": "damage_maintenance",
    "ON-SITE HANDOVER & SIGN-OFF": "handover_sign_off",
    "VENUE COMPLIANCE & SAFETY PACKET": "venue_compliance",
    "JOB SUMMARY CARD": "job_summary_card",
    "Contents": "contents",
    "Components": "components",
    "Accessories": "accessories",
    "Products": "products",
    "Devices": "devices",
    "Requirements": "requirements",
    "Maintenance Records": "maintenance_records",
    "Defect Reports": "defect_reports",
    "Case ID": "case_id",
    "Serial Number": "serial_number",
    "Status": "status",
    "Condition": "condition",
    "Product": "product",
    "SKU": "sku",
    "Category": "category",
    "Qty": "qty",
    "Quantity": "quantity",
    "Required": "required",
    "Kit Name": "kit_name",
    "Brand": "brand",
    "Location": "location",
    "Weight (kg)": "weight_kg",
    "Total Weight (kg)": "total_weight_kg",
    "Job Code": "job_code",
    "Customer": "customer",
    "Venue": "venue",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Notes": "notes",
    "Description": "description",
    "Name": "name",
    "Asset Tag": "asset_tag",
    "Type": "maintenance_type",
    "Scheduled": "scheduled_date",
    "Completed": "completed_date",
    "Severity": "severity",
    "Title": "title",
    "Date": "date",
    "Yes": "yes",
    "No": "no",
    "Page": "page",
    "of": "of",
    "Generated": "generated",
}


def get_translator(language: str | None = None):
    """Return a translator callable for the given language."""
    lang = _normalize_language(language)
    strings = _REPORT_STRINGS.get(lang, _REPORT_STRINGS["en"])
    fallback = _REPORT_STRINGS["en"]

    def translate(key: str, default: str | None = None) -> str:
        # Direct key lookup first.
        if key in strings:
            return strings[key]
        if key in fallback:
            return fallback[key]
        # Fall back to mapping known English phrases to keys.
        mapped = _ENGLISH_PHRASE_TO_KEY.get(key)
        if mapped:
            return strings.get(mapped, fallback.get(mapped, key))
        if default is not None:
            return default
        return key

    return translate


def format_report_date(value: date | datetime | str | None, language: str | None = "en") -> str | None:
    """Format a date/datetime for reports using the given language."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if not isinstance(value, (date, datetime)):
        return str(value)

    fmt = "%Y-%m-%d" if not isinstance(value, datetime) or value.hour == 0 and value.minute == 0 else "%Y-%m-%d %H:%M"
    return value.strftime(fmt)


def translate_flowables(flowables: list[dict], language: str | None = None) -> list[dict]:
    """Translate fixed labels/headings in a list of flowable definitions.

    Custom user text that does not match known English phrases is left untouched.
    """
    if not flowables:
        return flowables
    _ = get_translator(language)

    def translate_text(text: str) -> str:
        if not text:
            return text
        stripped = text.strip()
        if stripped.startswith("Generated:"):
            rest = stripped[len("Generated:"):].strip()
            return f"{_('generated')}: {rest}"
        return _(stripped, default=text)

    def translate_label(label: str) -> str:
        if not label:
            return label
        key = label.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
        return _(key, default=label)

    result = []
    for fdef in flowables:
        fdef = dict(fdef)
        ftype = fdef.get("type", "")
        if ftype in ("heading", "paragraph"):
            fdef["text"] = translate_text(fdef.get("text", ""))
        elif ftype == "table":
            fdef["columns"] = [
                {**col, "label": translate_label(col.get("label", ""))}
                for col in fdef.get("columns", [])
            ]
        elif ftype == "key_value":
            fdef["fields"] = [
                {**field, "label": translate_label(field.get("label", ""))}
                for field in fdef.get("fields", [])
            ]
        elif ftype == "columns":
            fdef["columns"] = [translate_flowables(col, language) for col in fdef.get("columns", [])]
        result.append(fdef)
    return result
