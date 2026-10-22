"""Tests for the Stagewire⇄stockwire-rental signed deeplink tokens."""

import time

import pytest

from app.domain.integrations.deeplink import (
    generate_link_secret,
    peek_deeplink_instance_id,
    sign_deeplink,
    verify_deeplink,
)


def test_sign_and_verify_roundtrip():
    secret = generate_link_secret()
    token = sign_deeplink(secret, src="stagewire", job_id=42, instance_id="stagewire-main")
    payload = verify_deeplink(secret, token)
    assert payload["src"] == "stagewire"
    assert payload["job_id"] == 42
    assert payload["instance_id"] == "stagewire-main"


def test_verify_rejects_tampered_token():
    secret = generate_link_secret()
    token = sign_deeplink(secret, src="stagewire", job_id=42, instance_id="stagewire-main")
    tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    with pytest.raises(ValueError):
        verify_deeplink(secret, tampered)


def test_verify_rejects_wrong_secret():
    token = sign_deeplink("secret-a", src="stagewire", job_id=42, instance_id="x")
    with pytest.raises(ValueError):
        verify_deeplink("secret-b", token)


def test_verify_rejects_expired_token(monkeypatch):
    secret = generate_link_secret()
    token = sign_deeplink(secret, src="stagewire", job_id=1, instance_id="x", ttl_seconds=1)
    # Advance beyond the TTL.
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 10)
    with pytest.raises(ValueError):
        verify_deeplink(secret, token)


def test_peek_instance_id_without_verifying():
    secret = generate_link_secret()
    token = sign_deeplink(secret, src="stockwire", job_id=7, instance_id="abc-123")
    assert peek_deeplink_instance_id(token) == "abc-123"
    assert peek_deeplink_instance_id("garbage") is None


def test_register_and_list_stagewire_instance(client):
    """Stagewire can push its own instance registration (base_url + shared key)."""
    payload = {
        "instance_id": "stagewire-main",
        "name": "Stagewire Prod",
        "base_url": "https://stagewire.example.com",
        "api_key": "shared-secret-key",
        "default_customer_id": None,
    }
    r = client.post("/api/v1/settings/integrations/stagewire/register", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "stagewire-main"
    assert body["api_url"] == "https://stagewire.example.com"
    assert body["has_api_key"] is True

    listed = client.get("/api/v1/settings/integrations/stagewire-instances")
    assert listed.status_code == 200
    assert any(i["id"] == "stagewire-main" for i in listed.json())


def test_register_rejects_short_key(client):
    r = client.post(
        "/api/v1/settings/integrations/stagewire/register",
        json={"base_url": "https://stagewire.example.com", "api_key": "short"},
    )
    assert r.status_code == 422


def test_register_rejects_overwrite_without_current_key(monkeypatch):
    from app.domain.settings import router as settings_router
    from app.domain.settings.schemas import StagewireInboundRegisterBody

    stored = {
        "stagewire_instances": [
            {"id": "stagewire-main", "api_key": "stored-secret-123", "api_url": "http://a.test"}
        ]
    }

    class FakeSetting:
        value_json = ""

    setting = FakeSetting()
    import json as _json

    setting.value_json = _json.dumps(stored)
    monkeypatch.setattr(settings_router, "_get_or_create_setting", lambda *a, **k: setting)

    class FakeDB:
        def commit(self):
            pass

    body = StagewireInboundRegisterBody(base_url="http://evil.test", api_key="attacker-key-999")
    with pytest.raises(Exception) as exc:
        settings_router.register_stagewire_instance(body, db=FakeDB())
    assert getattr(exc.value, "status_code", None) == 403

    body_ok = StagewireInboundRegisterBody(
        base_url="http://a.test", api_key="stored-secret-123", instance_id="stagewire-main"
    )
    result = settings_router.register_stagewire_instance(body_ok, db=FakeDB())
    assert result.has_api_key is True
