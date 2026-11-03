"""Tests for the AI Assistant endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select


# ── Tool tests ──────────────────────────────────────────────────────────────


def _make_product(name="Test Product", sku="SKU-001", category="Audio", product_type="equipment", daily_rate=100.0, replace_cost=500.0):
    p = MagicMock()
    p.name = name
    p.sku = sku
    p.category = category
    p.product_type = product_type
    p.daily_rate = daily_rate
    p.replace_cost = replace_cost
    p.total_devices = 5
    p.in_store_devices = 3
    p.on_site_devices = 1
    p.damaged_devices = 1
    p.is_rental_product = False
    p.eventory_available_qty = 10
    return p


def test_product_tool_handler():
    from app.assistant.tools import execute_tool

    product = _make_product(name="Pelican 1510", sku="1510")
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [5, 3, 1, 1]
    with patch("app.assistant.tools._find_product", return_value=product):
        result = execute_tool("check_inventory_stock", {"item_name": "1510"}, mock_db)
        assert result["sku"] == "1510"
        assert result["name"] == "Pelican 1510"
        assert result["available"] == 3


def test_product_not_found():
    from app.assistant.tools import execute_tool

    mock_db = MagicMock()
    with patch("app.assistant.tools._find_product", return_value=None):
        result = execute_tool("check_inventory_stock", {"item_name": "nonexistent"}, mock_db)
        assert "error" in result


def test_rates_tool():
    from app.assistant.tools import execute_tool

    product = _make_product(daily_rate=150.0, replace_cost=800.0)
    mock_db = MagicMock()
    with patch("app.assistant.tools._find_product", return_value=product):
        result = execute_tool("get_rental_rates", {"item_name": "Test"}, mock_db)
        assert result["daily_rate"] == 150.0
        assert result["replace_cost"] == 800.0


def test_unknown_tool():
    from app.assistant.tools import execute_tool

    result = execute_tool("nonexistent_tool", {}, MagicMock())
    assert "error" in result


def test_tool_specs_enforce_fixed_value_enums():
    from app.assistant.tools import TOOLS, WRITE_TOOLS

    functions = {tool["function"]["name"]: tool["function"] for tool in TOOLS}
    assert functions["search_products"]["parameters"]["properties"]["product_type"]["enum"] == [
        "equipment",
        "accessory",
        "consumable",
        "case",
        "bundle",
        "rental",
    ]
    assert functions["list_jobs"]["parameters"]["properties"]["status"]["enum"] == [
        "draft",
        "confirmed",
        "in_progress",
        "completed",
        "cancelled",
    ]
    assert {
        "add_item_to_job",
        "update_job_manifest",
        "create_customer",
        "update_customer",
        "flag_damaged_device",
        "update_device_status",
    }.issubset(WRITE_TOOLS)


def test_product_match_reports_ambiguous_partial_search(db_session, client):
    from app.assistant.tools import execute_tool
    from app.domain.inventory.models import Product

    db_session.add_all(
        [
            Product(sku="PEL-1510", name="Pelican 1510"),
            Product(sku="PEL-1610", name="Pelican 1610"),
        ]
    )
    db_session.commit()

    result = execute_tool(
        "check_inventory_stock", {"item_name": "Pelican"}, db_session
    )

    assert "error" in result
    assert "Pelican 1510 (SKU: PEL-1510)" in result["error"]
    assert "Pelican 1610 (SKU: PEL-1610)" in result["error"]
    assert "specify exact SKU" in result["error"]


def test_date_range_availability_tool_uses_overlapping_jobs(db_session, client):
    from datetime import date

    from app.assistant.tools import execute_tool
    from app.domain.inventory.models import Device, Product
    from app.domain.jobs.models import Job, JobRequirement

    product = Product(sku="AVAIL-TOOL", name="Availability tool product")
    db_session.add(product)
    db_session.flush()
    for index in range(4):
        db_session.add(
            Device(
                product_id=product.id,
                asset_tag=f"AVAIL-TOOL-{index}",
                status="available",
                condition="good",
            )
        )
    job_a = Job(
        job_code="AVAIL-TOOL-A",
        status="confirmed",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 3),
    )
    job_b = Job(
        job_code="AVAIL-TOOL-B",
        status="confirmed",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
    )
    cancelled_job = Job(
        job_code="AVAIL-TOOL-C",
        status="cancelled",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )
    db_session.add_all([job_a, job_b, cancelled_job])
    db_session.flush()
    db_session.add_all(
        [
            JobRequirement(job_id=job_a.id, product_id=product.id, quantity_required=2),
            JobRequirement(job_id=job_b.id, product_id=product.id, quantity_required=3),
            JobRequirement(job_id=cancelled_job.id, product_id=product.id, quantity_required=20),
        ]
    )
    db_session.commit()

    result = execute_tool(
        "check_date_range_availability",
        {
            "item_name": "AVAIL-TOOL",
            "start_date": "2026-08-01",
            "end_date": "2026-08-05",
        },
        db_session,
    )
    assert result["total_quantity"] == 4
    assert result["max_reserved_quantity"] == 5
    assert result["available_quantity"] == 0
    assert result["start_date"] == date(2026, 8, 1)

    invalid = execute_tool(
        "check_date_range_availability",
        {
            "item_name": "AVAIL-TOOL",
            "start_date": "2026-08-06",
            "end_date": "2026-08-05",
        },
        db_session,
    )
    assert invalid["error"] == "start_date must be on or before end_date"


def test_job_manifest_add_update_and_remove_tools(db_session, client):
    from app.assistant.tools import execute_tool
    from app.domain.inventory.models import (
        Device,
        InventoryAuditLog,
        Product,
    )
    from app.domain.jobs.models import Job, JobRequirement

    equipment = Product(sku="MANIFEST-EQ", name="Manifest speaker")
    case_product = Product(sku="MANIFEST-CASE", name="Manifest case", product_type="case")
    db_session.add_all([equipment, case_product])
    db_session.flush()
    job = Job(job_code="MANIFEST-01", status="confirmed")
    db_session.add(job)
    db_session.flush()
    existing_line = JobRequirement(
        job_id=job.id,
        product_id=equipment.id,
        quantity_required=2,
        label="Main speakers",
    )
    case_device = Device(
        product_id=case_product.id,
        asset_tag="CASE-01",
        serial_number="CASE-SERIAL-01",
        status="in_use",
        condition="good",
    )
    db_session.add_all([existing_line, case_device])
    db_session.flush()
    packed_device = Device(
        product_id=equipment.id,
        asset_tag="SPEAKER-01",
        serial_number="SPEAKER-SERIAL-01",
        case_device_id=case_device.id,
        status="in_use",
        condition="good",
    )
    db_session.add(packed_device)
    db_session.flush()
    db_session.add_all(
        [
            InventoryAuditLog(
                source="assistant-test",
                action="job_out",
                success=True,
                message="Packed case",
                device_id=case_device.id,
                product_id=case_product.id,
                job_id=job.id,
            ),
            InventoryAuditLog(
                source="assistant-test",
                action="job_out",
                success=True,
                message="Packed speaker",
                device_id=packed_device.id,
                product_id=equipment.id,
                job_id=job.id,
            ),
        ]
    )
    db_session.commit()

    manifest = execute_tool("get_job_manifest", {"job_code": "MANIFEST-01"}, db_session)
    assert manifest["line_items"][0]["label"] == "Main speakers"
    assert manifest["cases"][0]["asset_tag"] == "CASE-01"
    assert manifest["cases"][0]["contents"][0]["product_name"] == "Manifest speaker"
    assert manifest["packed_equipment"][0]["case_device_id"] == case_device.id

    added = execute_tool(
        "add_item_to_job",
        {"job_code": "MANIFEST-01", "item_name": "MANIFEST-EQ", "quantity": 3},
        db_session,
    )
    assert added["success"] is True
    assert added["quantity_required"] == 3

    updated = execute_tool(
        "update_job_manifest",
        {
            "job_code": "MANIFEST-01",
            "requirement_id": added["requirement_id"],
            "action": "update",
            "quantity": 4,
        },
        db_session,
    )
    assert updated["quantity_required"] == 4

    removed = execute_tool(
        "update_job_manifest",
        {
            "job_code": "MANIFEST-01",
            "requirement_id": added["requirement_id"],
            "action": "remove",
        },
        db_session,
    )
    assert removed["success"] is True
    assert db_session.get(JobRequirement, added["requirement_id"]) is None


def test_customer_tools_create_and_update_customer(db_session, client):
    from app.assistant.tools import execute_tool

    created = execute_tool(
        "create_customer",
        {"name": "Acme Events", "email": "contact@acme.test", "phone": "+461234"},
        db_session,
    )
    assert created["success"] is True
    updated = execute_tool(
        "update_customer",
        {"customer_id": created["customer_id"], "phone": "+469876"},
        db_session,
    )
    assert updated["phone"] == "+469876"

    duplicate = execute_tool(
        "create_customer",
        {"name": "Acme Duplicate", "email": "contact@acme.test"},
        db_session,
    )
    assert "already exists" in duplicate["error"]


def test_device_damage_and_status_tools(db_session, client):
    from app.assistant.tools import execute_tool
    from app.domain.inventory.models import DefectReport, Device, Product

    product = Product(sku="DEVICE-TOOL", name="Device tool product")
    db_session.add(product)
    db_session.flush()
    damaged_device = Device(
        product_id=product.id,
        asset_tag="DEVICE-DAMAGE-01",
        serial_number="SERIAL-DAMAGE-01",
        status="available",
        condition="good",
    )
    status_device = Device(
        product_id=product.id,
        asset_tag="DEVICE-STATUS-01",
        serial_number="SERIAL-STATUS-01",
        status="available",
        condition="good",
    )
    db_session.add_all([damaged_device, status_device])
    db_session.commit()

    damage_result = execute_tool(
        "flag_damaged_device",
        {
            "identifier": "SERIAL-DAMAGE-01",
            "title": "Damaged connector",
            "severity": "high",
        },
        db_session,
    )
    assert damage_result["success"] is True
    assert damage_result["condition"] == "damaged"
    assert damage_result["status"] == "maintenance"
    assert db_session.get(DefectReport, damage_result["defect_report_id"]).severity == "high"

    status_result = execute_tool(
        "update_device_status",
        {"identifier": "DEVICE-STATUS-01", "status": "on_site"},
        db_session,
    )
    assert status_result["status"] == "in_use"

    invalid = execute_tool(
        "update_device_status",
        {"identifier": "DEVICE-STATUS-01", "status": "unknown"},
        db_session,
    )
    assert "error" in invalid


def test_tool_failure_rolls_back_session(db_session, client, monkeypatch):
    from app.assistant import tools
    from app.assistant.tools import execute_tool
    from app.domain.inventory.models import Product

    db_session.add(Product(sku="ROLLBACK-01", name="Rollback product"))
    db_session.commit()

    def fail_with_pending_insert(args, db):
        db.add(Product(sku="ROLLBACK-01", name="Duplicate product"))
        db.commit()

    monkeypatch.setattr(tools, "_update_manufacturer", fail_with_pending_insert)
    with patch.object(db_session, "rollback", wraps=db_session.rollback) as rollback:
        result = execute_tool(
            "update_product_manufacturer",
            {"item_name": "ROLLBACK-01", "manufacturer": "Test"},
            db_session,
        )

    assert "error" in result
    rollback.assert_called_once()
    assert db_session.scalar(select(Product).where(Product.sku == "ROLLBACK-01")).name == "Rollback product"


# ── Endpoint tests ──────────────────────────────────────────────────────────


def test_models_endpoint(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_models = MagicMock()
        mock_models.data = [MagicMock(id="gpt-4o"), MagicMock(id="gpt-3.5-turbo")]
        mock_instance.models.list = AsyncMock(return_value=mock_models)
        MockOpenAI.return_value = mock_instance

        resp = client.get("/api/v1/assistant/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["models"][0]["id"] == "gpt-4o"


def test_models_endpoint_error(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.models.list = AsyncMock(side_effect=Exception("Connection refused"))
        MockOpenAI.return_value = mock_instance

        resp = client.get("/api/v1/assistant/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert "error" in data


def test_test_connection_success(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_models = MagicMock()
        mock_models.data = [MagicMock(id="model-a"), MagicMock(id="model-b")]
        mock_instance.models.list = AsyncMock(return_value=mock_models)
        MockOpenAI.return_value = mock_instance

        resp = client.get("/api/v1/assistant/test-connection")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["models_available"] == 2


def test_test_connection_failure(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.models.list = AsyncMock(side_effect=Exception("Connection refused"))
        MockOpenAI.return_value = mock_instance

        resp = client.get("/api/v1/assistant/test-connection")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "message" in data


def test_test_model_success(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello! I am working."))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        resp = client.post("/api/v1/assistant/test-model", json={"model": "gpt-4o"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "Hello" in data["response"]


def test_test_model_no_model(client):
    resp = client.post("/api/v1/assistant/test-model", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "No model" in data["error"]


def test_test_model_unavailable(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("403 Forbidden: Model not available")
        )
        MockOpenAI.return_value = mock_instance

        resp = client.post("/api/v1/assistant/test-model", json={"model": "restricted-model"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False


def test_chat_endpoint(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello", tool_calls=None))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=" world", tool_calls=None))]

        async def async_iter():
            for c in [chunk1, chunk2]:
                yield c

        mock_instance.chat.completions.create = AsyncMock(return_value=async_iter())
        MockOpenAI.return_value = mock_instance

        resp = client.post(
            "/api/v1/assistant/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert resp.status_code == 200
        content = resp.text
        assert "Hello" in content
        assert "world" in content
        assert "[DONE]" in content


def test_chat_endpoint_error(client):
    with patch("app.assistant.router.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        MockOpenAI.return_value = mock_instance

        resp = client.post(
            "/api/v1/assistant/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert resp.status_code == 200
        content = resp.text
        assert "Connection" in content or "error" in content
        assert "[DONE]" in content
