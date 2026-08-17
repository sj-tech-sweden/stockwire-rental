"""Tests for report template generation endpoints."""

import io

from pypdf import PdfReader


def _seed_product(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "RPT-01",
            "name": "Report Test Speaker",
            "category": "audio",
            "brand": "Test",
            "manufacturer": "Test",
            "product_type": "equipment",
            "weight_kg": "10.000",
            "daily_rate": "100.00",
            "replace_cost": "500.00",
        },
    )
    assert product.status_code == 200
    return product.json()["id"]


def _seed_job(client):
    job = client.post(
        "/api/v1/jobs",
        json={
            "job_code": "RPT-JOB-01",
            "description": "Report test job",
            "status": "draft",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "sales_price": "1000.00",
        },
    )
    assert job.status_code == 200
    return job.json()["id"]


def _seed_template(client, entity_type):
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "TEST REPORT", "level": 1},
            {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
        ],
    }
    if entity_type == "product":
        body["flowables"].append(
            {"type": "key_value", "source": "product", "fields": [{"key": "name", "label": "Name"}]}
        )
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": f"Test {entity_type} template",
            "category": "custom",
            "description": "Test template",
            "body_json": __import__("json").dumps(body),
            "data_source_type": entity_type,
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    return tmpl.json()["id"]


def test_list_report_templates(client):
    resp = client.get("/api/v1/reports/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_generate_pdf_report_for_job(client):
    job_id = _seed_job(client)
    template_id = _seed_template(client, "job")

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "job",
            "entity_id": job_id,
            "format": "pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["format"] == "pdf"
    assert data["size_bytes"] > 0
    assert data["download_url"]

    # Download and verify it is a valid PDF
    download = client.get(data["download_url"])
    assert download.status_code == 200
    payload = download.content
    assert payload.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(payload))
    assert len(reader.pages) >= 1


def test_generate_html_report_for_product(client):
    product_id = _seed_product(client)
    template_id = _seed_template(client, "product")

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "html",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["format"] == "html"
    assert data["size_bytes"] > 0

    download = client.get(data["download_url"])
    assert download.status_code == 200
    html = download.text
    assert "TEST REPORT" in html
    assert html.strip().endswith("</html>")


def test_generate_csv_report_for_product(client):
    product_id = _seed_product(client)
    template_id = _seed_template(client, "product")

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "csv",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["format"] == "csv"
    assert data["size_bytes"] > 0

    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/csv")


def test_generate_pdf_with_alignment_and_columns(client):
    job_id = _seed_job(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "Centered Heading", "level": 1, "align": "center"},
            {"type": "paragraph", "text": "Right paragraph", "style": "body", "align": "right"},
            {
                "type": "columns",
                "widths": ["40%", "60%"],
                "columns": [
                    [
                        {"type": "paragraph", "text": "Left column", "style": "body"},
                    ],
                    [
                        {"type": "paragraph", "text": "Right column", "style": "body", "align": "right"},
                    ],
                ],
            },
        ],
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test alignment template",
            "category": "custom",
            "description": "Test alignment and columns",
            "body_json": __import__("json").dumps(body),
            "data_source_type": "job",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "job",
            "entity_id": job_id,
            "format": "pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_generate_html_with_alignment_and_columns(client):
    job_id = _seed_job(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "Centered", "level": 2, "align": "center"},
            {"type": "paragraph", "text": "Right", "style": "body", "align": "right"},
            {
                "type": "columns",
                "widths": ["50%", "50%"],
                "columns": [
                    [{"type": "paragraph", "text": "A", "style": "body"}],
                    [{"type": "paragraph", "text": "B", "style": "body", "align": "right"}],
                ],
            },
        ],
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test HTML alignment template",
            "category": "custom",
            "description": "Test HTML alignment and columns",
            "body_json": __import__("json").dumps(body),
            "data_source_type": "job",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "job",
            "entity_id": job_id,
            "format": "html",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    html = download.text
    assert 'class="align-center"' in html
    assert 'class="align-right"' in html
    assert '<div class="columns">' in html


def test_generate_pdf_with_job_summary_card_template(client):
    """Ensure the builtin Job Summary Card style template renders without errors."""
    job_id = _seed_job(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "JOB SUMMARY", "level": 1, "align": "center"},
            {"type": "spacer", "height_mm": 2},
            {
                "type": "columns",
                "widths": ["50%", "50%"],
                "columns": [
                    [
                        {"type": "heading", "text": "Customer", "level": 2},
                        {"type": "paragraph", "text": "{{ job.customer_name }}", "style": "body"},
                        {"type": "paragraph", "text": "{{ job.venue_name }}", "style": "small"},
                    ],
                    [
                        {"type": "heading", "text": "Dates", "level": 2, "align": "right"},
                        {"type": "paragraph", "text": "Start: {{ job.start_date }}", "style": "body", "align": "right"},
                        {"type": "paragraph", "text": "End: {{ job.end_date }}", "style": "body", "align": "right"},
                    ],
                ],
            },
            {"type": "spacer", "height_mm": 3},
            {"type": "line"},
            {"type": "spacer", "height_mm": 5},
            {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small", "align": "center"},
        ],
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test job summary card",
            "category": "custom",
            "description": "Test columns and alignments",
            "body_json": __import__("json").dumps(body),
            "data_source_type": "job",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "job",
            "entity_id": job_id,
            "format": "pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_generate_pdf_with_qr_barcode(client):
    product_id = _seed_product(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "QR Test", "level": 1},
            {"type": "barcode", "value": "{{ product.sku }}", "barcode_type": "qr", "align": "center"},
        ],
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test QR barcode",
            "category": "custom",
            "description": "Test QR code rendering",
            "body_json": __import__("json").dumps(body),
            "data_source_type": "product",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_generate_pdf_in_swedish_translates_labels(client):
    """Report generation in Swedish should translate known headings, labels and the generated-at line."""
    product_id = _seed_product(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "CASE MANIFEST", "level": 1},
            {"type": "key_value", "source": "product", "fields": [
                {"key": "name", "label": "Name"},
                {"key": "sku", "label": "SKU"},
            ]},
            {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
        ],
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test Swedish translation",
            "category": "custom",
            "description": "Test Swedish report translation",
            "body_json": __import__("json").dumps(body),
            "data_source_type": "product",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "pdf",
            "language": "sv",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    text = _pdf_text(download.content)
    assert "FLIGHTCASE-INNEHÅLL" in text
    assert "Namn" in text
    assert "SKU" in text
    assert "Genererad:" in text


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_template_translations_switch_language(client):
    """A template with translations should render in the requested language."""
    product_id = _seed_product(client)
    body = {
        "page_size": "A4",
        "flowables": [
            {"type": "heading", "text": "English heading", "level": 1},
            {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
        ],
    }
    translations = {
        "sv": {
            "flowables": [
                {"type": "heading", "text": "Svensk rubrik", "level": 1},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ]
        },
        "de": {
            "flowables": [
                {"type": "heading", "text": "Deutsche Uberschrift", "level": 1},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ]
        },
    }
    tmpl = client.post(
        "/api/v1/reports/templates",
        json={
            "name": "Test multilingual template",
            "category": "custom",
            "description": "Test language switching",
            "body_json": __import__("json").dumps(body),
            "translations_json": __import__("json").dumps(translations),
            "data_source_type": "product",
            "is_enabled": True,
        },
    )
    assert tmpl.status_code == 201
    template_id = tmpl.json()["id"]

    # English
    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "pdf",
            "language": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    text_en = _pdf_text(download.content)
    assert "English heading" in text_en
    assert "Svensk rubrik" not in text_en
    assert "Deutsche Uberschrift" not in text_en

    # Swedish
    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "pdf",
            "language": "sv",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    text_sv = _pdf_text(download.content)
    assert "Svensk rubrik" in text_sv
    assert "English heading" not in text_sv

    # German
    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": template_id,
            "entity_type": "product",
            "entity_id": product_id,
            "format": "pdf",
            "language": "de",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    text_de = _pdf_text(download.content)
    assert "Deutsche Uberschrift" in text_de
    assert "English heading" not in text_de


def test_seeded_case_manifest_renders_contents(client, db_session):
    """The builtin Case Lid / Insert Manifest template must list contained devices."""
    from app.domain.reports.models import ReportTemplate
    from app.domain.reports.seed import seed_report_templates

    # Seed builtin templates into the current test database.
    seed_report_templates(db_session)
    case_tmpl = db_session.query(ReportTemplate).filter_by(name="Case Lid / Insert Manifest").first()
    assert case_tmpl is not None

    templates = client.get("/api/v1/reports/templates").json()
    case_tmpl_data = next((t for t in templates if t["name"] == "Case Lid / Insert Manifest"), None)
    assert case_tmpl_data is not None

    # Create a product and a case device plus one contained device
    product_resp = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "CASE-01",
            "name": "Flight Case",
            "category": "cases",
            "brand": "Test",
            "manufacturer": "Test",
            "product_type": "case",
            "weight_kg": "5.000",
            "daily_rate": "10.00",
            "replace_cost": "100.00",
        },
    )
    assert product_resp.status_code == 200
    product_id = product_resp.json()["id"]

    item_resp = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "MIC-01",
            "name": "Microphone",
            "category": "audio",
            "brand": "Test",
            "manufacturer": "Test",
            "product_type": "equipment",
            "weight_kg": "0.500",
            "daily_rate": "5.00",
            "replace_cost": "50.00",
        },
    )
    assert item_resp.status_code == 200
    item_product_id = item_resp.json()["id"]

    case_resp = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "CASE-001",
            "serial_number": "CASESN001",
            "status": "available",
            "condition": "good",
        },
    )
    assert case_resp.status_code == 200
    case_id = case_resp.json()["id"]

    content_resp = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": item_product_id,
            "asset_tag": "MIC-001",
            "serial_number": "MICSERIAL001",
            "status": "available",
            "condition": "good",
            "case_device_id": case_id,
        },
    )
    assert content_resp.status_code == 200

    resp = client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": case_tmpl_data["id"],
            "entity_type": "device",
            "entity_id": case_id,
            "format": "pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    text = _pdf_text(download.content)
    assert "CASE MANIFEST" in text
    assert "MIC-01" in text
    assert "Microphone" in text
    assert "MICSERIAL001" in text
