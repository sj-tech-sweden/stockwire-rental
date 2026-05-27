import pytest
from urllib.parse import urljoin
from urllib.request import Request

from fastapi import HTTPException

import app.domain.settings.router as settings_router
from app.domain.settings.router import _url_origin, _is_same_origin_url, _fetch_eventory_token


def test_url_origin_invalid_port_non_numeric():
    assert _url_origin("https://host:abc") is None


def test_url_origin_invalid_port_out_of_range():
    assert _url_origin("https://host:99999") is None


def test_url_origin_valid():
    assert _url_origin("https://api.example.com") == ("https", "api.example.com", 443)
    assert _url_origin("http://api.example.com:8080") == ("http", "api.example.com", 8080)


def test_fetch_eventory_token_rejects_cross_origin_endpoint():
    with pytest.raises(HTTPException) as exc_info:
        _fetch_eventory_token(
            "https://api.example.com",
            "https://evil.com/oauth/token",
            "user",
            "pass",
        )
    assert exc_info.value.status_code == 400


def test_fetch_eventory_token_rejects_different_scheme():
    with pytest.raises(HTTPException) as exc_info:
        _fetch_eventory_token(
            "https://api.example.com",
            "http://api.example.com/oauth/token",
            "user",
            "pass",
        )
    assert exc_info.value.status_code == 400


def test_default_candidates_are_same_origin():
    api_url = "https://api.example.com/v1"
    origin = _url_origin(api_url)
    assert origin is not None
    candidates = [
        urljoin(api_url.rstrip("/") + "/", "login-json"),
        urljoin(api_url.rstrip("/") + "/", "login"),
        urljoin(api_url.rstrip("/") + "/", "oauth/token"),
    ]
    for candidate in candidates:
        assert _is_same_origin_url(candidate, origin), f"{candidate} should be same-origin"


def test_open_outbound_integration_request_validates_url_at_open_time(monkeypatch):
    validated: list[str] = []
    monkeypatch.setattr(
        settings_router,
        "_validate_outbound_integration_url",
        lambda raw_url: validated.append(raw_url) or raw_url,
    )

    class _DummyOpener:
        def open(self, req, timeout):
            return {"req": req, "timeout": timeout}

    monkeypatch.setattr(settings_router, "build_opener", lambda *_: _DummyOpener())
    req = Request("https://api.example.com/ping", method="HEAD")
    result = settings_router._open_outbound_integration_request(req, timeout=5)

    assert validated == ["https://api.example.com/ping"]
    assert result["req"] is req
    assert result["timeout"] == 5


def test_open_outbound_integration_request_uses_no_redirect_handler(monkeypatch):
    monkeypatch.setattr(settings_router, "_validate_outbound_integration_url", lambda raw_url: raw_url)
    captured: dict[str, object] = {}

    class _DummyOpener:
        def open(self, req, timeout):
            captured["req"] = req
            captured["timeout"] = timeout
            return "opened"

    def _fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return _DummyOpener()

    monkeypatch.setattr(settings_router, "build_opener", _fake_build_opener)
    req = Request("https://api.example.com/ping", method="GET")
    result = settings_router._open_outbound_integration_request(req, timeout=7)

    handlers = captured["handlers"]
    assert any(isinstance(handler, settings_router._NoRedirectHandler) for handler in handlers)
    assert any(isinstance(handler, settings_router._ValidatedHTTPHandler) for handler in handlers)
    assert any(isinstance(handler, settings_router._ValidatedHTTPSHandler) for handler in handlers)
    assert captured["req"] is req
    assert captured["timeout"] == 7
    assert result == "opened"
