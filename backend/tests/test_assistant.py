"""Tests for the AI Assistant endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
