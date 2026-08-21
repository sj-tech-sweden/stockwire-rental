"""Tests for Twenty CRM sync fixes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.integrations.twenty_client import TwentyClient


# ---------------------------------------------------------------------------
# TwentyClient – Authorization header uses the actual API key
# ---------------------------------------------------------------------------


def test_twenty_client_auth_header_uses_api_key():
    """TwentyClient must include the api_key in the Authorization header."""
    client = TwentyClient(api_key="test-secret-key-123", base_url="https://api.twenty.com")
    auth = client.headers.get("Authorization", "")
    assert "test-secret-key-123" in auth, (
        f"Authorization header should contain the api_key, got: {auth!r}"
    )


def test_twenty_client_auth_header_is_bearer():
    """TwentyClient Authorization header should use ******"""
    client = TwentyClient(api_key="mykey", base_url="https://api.twenty.com")
    auth = client.headers.get("Authorization", "")
    assert auth.startswith("Bearer "), (
        f"Authorization header should start with 'Bearer ', got: {auth!r}"
    )


def test_twenty_client_different_keys_produce_different_headers():
    """Two clients with different API keys must produce different Auth headers."""
    client_a = TwentyClient(api_key="key-aaa", base_url="https://api.twenty.com")
    client_b = TwentyClient(api_key="key-bbb", base_url="https://api.twenty.com")
    assert client_a.headers["Authorization"] != client_b.headers["Authorization"]


# ---------------------------------------------------------------------------
# TwentyClient.list_objects – must use GET, not POST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_objects_uses_get_method():
    """list_objects must use GET to read, not POST (which would create records)."""
    client = TwentyClient(api_key="key", base_url="https://api.twenty.com")

    captured = {}

    async def _fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"companies": {"edges": []}}}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    client._request_with_retry = _fake_request

    await client.list_objects("companies", limit=10, offset=0)

    assert captured["method"] == "GET", (
        f"list_objects should use GET, but used {captured['method']!r}"
    )


@pytest.mark.asyncio
async def test_list_objects_sends_params_not_json_body():
    """list_objects must pass limit/orderBy as query params, not a JSON body."""
    client = TwentyClient(api_key="key", base_url="https://api.twenty.com")

    captured = {}

    async def _fake_request(method, url, **kwargs):
        captured["kwargs"] = kwargs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"companies": {"edges": []}}}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    client._request_with_retry = _fake_request

    await client.list_objects("companies", limit=25, offset=0)

    # Must NOT send a JSON body (which would trigger object creation)
    assert "json" not in captured["kwargs"], (
        "list_objects must not send a JSON body; it should use query params"
    )
    # Must send query params
    assert "params" in captured["kwargs"], (
        "list_objects must pass parameters as query params"
    )
    assert captured["kwargs"]["params"]["limit"] == 25


@pytest.mark.asyncio
async def test_list_objects_offset_included_when_nonzero():
    """list_objects should include offset in query params when it is > 0."""
    client = TwentyClient(api_key="key", base_url="https://api.twenty.com")

    captured = {}

    async def _fake_request(method, url, **kwargs):
        captured["kwargs"] = kwargs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"companies": {"edges": []}}}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    client._request_with_retry = _fake_request

    await client.list_objects("companies", limit=50, offset=50)

    params = captured["kwargs"]["params"]
    assert params.get("offset") == 50, "offset should be included in params when nonzero"


@pytest.mark.asyncio
async def test_list_objects_no_offset_when_zero():
    """list_objects should omit offset from params when it is 0."""
    client = TwentyClient(api_key="key", base_url="https://api.twenty.com")

    captured = {}

    async def _fake_request(method, url, **kwargs):
        captured["kwargs"] = kwargs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"companies": {"edges": []}}}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    client._request_with_retry = _fake_request

    await client.list_objects("companies", limit=50, offset=0)

    params = captured["kwargs"]["params"]
    assert "offset" not in params, "offset should be omitted from params when 0"


# ---------------------------------------------------------------------------
# People pre-fetch optimisation in _do_sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_do_sync_syncs_companies_persons_and_jobs():
    """_do_sync must sync companies, persons, and jobs without legacy customer sync."""
    from app.domain.integrations.auto_sync import _do_sync

    db = MagicMock()
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

    client = MagicMock()

    # Three companies returned on first page; nothing on second
    companies_resp = {
        "data": {
            "companies": {
                "edges": [
                    {"node": {"id": "c1", "name": "Alpha"}},
                    {"node": {"id": "c2", "name": "Beta"}},
                    {"node": {"id": "c3", "name": "Gamma"}},
                ]
            }
        }
    }
    people_resp = {
        "data": {
            "people": {
                "edges": [
                    {"node": {"id": "p1", "name": {"firstName": "John", "lastName": "Doe"}}},
                ]
            }
        }
    }
    empty_resp: dict = {"data": {"companies": {"edges": []}, "people": {"edges": []}, "opportunities": {"edges": []}}}

    async def _list_objects(object_name, limit=100, offset=0):
        if object_name == "companies" and offset == 0:
            return companies_resp
        if object_name == "people" and offset == 0:
            return people_resp
        return empty_resp

    client.list_objects = _list_objects

    company_inbound_calls: list = []
    person_inbound_calls: list = []
    job_inbound_calls: list = []

    async def _sync_company_inbound(db, client, company):
        company_inbound_calls.append(company)
        return False

    async def _sync_person_inbound(db, client, person):
        person_inbound_calls.append(person)
        return False

    async def _sync_job_inbound(db, client, opp):
        job_inbound_calls.append(opp)
        return False

    with (
        patch("app.domain.integrations.sync_engine.sync_company_inbound", _sync_company_inbound),
        patch("app.domain.integrations.sync_engine.sync_company_outbound", AsyncMock()),
        patch("app.domain.integrations.sync_engine.sync_person_inbound", _sync_person_inbound),
        patch("app.domain.integrations.sync_engine.sync_person_outbound", AsyncMock()),
        patch("app.domain.integrations.sync_engine.sync_job_inbound", _sync_job_inbound),
        patch("app.domain.integrations.sync_engine.sync_job_outbound", AsyncMock()),
    ):
        await _do_sync(db, client)

    assert len(company_inbound_calls) == 3, (
        f"sync_company_inbound should be called 3 times, but was called {len(company_inbound_calls)} times"
    )
    assert len(person_inbound_calls) == 1, (
        f"sync_person_inbound should be called 1 time, but was called {len(person_inbound_calls)} times"
    )
