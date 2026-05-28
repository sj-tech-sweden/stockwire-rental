import socket
import pytest
from urllib.error import URLError
from unittest.mock import patch
from urllib.parse import urljoin
from urllib.request import Request

from fastapi import HTTPException

import app.domain.settings.router as settings_router
from app.domain.settings.router import (
    _ensure_public_response_peer,
    _fetch_eventory_token,
    _is_public_http_url,
    _is_same_origin_url,
    _url_origin,
    _validate_outbound_api_url,
)


def test_url_origin_invalid_port_non_numeric():
    assert _url_origin("https://host:abc") is None


def test_url_origin_invalid_port_out_of_range():
    assert _url_origin("https://host:99999") is None


def test_url_origin_valid():
    assert _url_origin("https://api.example.com") == ("https", "api.example.com", 443)
    assert _url_origin("http://api.example.com:8080") == ("http", "api.example.com", 8080)


def test_fetch_eventory_token_rejects_http_api_url():
    with pytest.raises(HTTPException) as exc_info:
        _fetch_eventory_token(
            "http://api.example.com",
            "",
            "user",
            "pass",
        )
    assert exc_info.value.status_code == 400
    assert "https" in exc_info.value.detail.lower()


def test_fetch_eventory_token_ignores_token_endpoint(monkeypatch):
    """token_endpoint is not used; candidates always derive from api_url."""
    calls: list[str] = []

    def _fake_open(req, timeout):
        calls.append(req.full_url)
        raise URLError("connection refused")

    monkeypatch.setattr(settings_router, "_is_public_http_url", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(settings_router, "_open_outbound_integration_request", _fake_open)

    with pytest.raises(HTTPException):
        _fetch_eventory_token(
            "https://api.example.com",
            "https://evil.com/oauth/token",
            "user",
            "pass",
        )

    assert calls, "expected at least one outbound request"
    assert all(url.startswith("https://api.example.com/") for url in calls)


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
    assert isinstance(handlers[0], settings_router.ProxyHandler)
    assert handlers[0].proxies == {}
    assert any(isinstance(handler, settings_router._NoRedirectHandler) for handler in handlers)
    assert any(isinstance(handler, settings_router._ValidatedHTTPHandler) for handler in handlers)
    assert any(isinstance(handler, settings_router._ValidatedHTTPSHandler) for handler in handlers)
    assert captured["req"] is req
    assert captured["timeout"] == 7
    assert result == "opened"


def test_validate_outbound_integration_url_rejects_invalid_port():
    with pytest.raises(HTTPException) as exc_info:
        settings_router._validate_outbound_integration_url("https://api.eventory.se:abc")

    assert exc_info.value.status_code == 400
    assert "invalid port" in str(exc_info.value.detail).lower()


@pytest.mark.parametrize(
    "url",
    [
        "https://user@api.eventory.se/test",
        "https://:password@api.eventory.se/test",
        "https://user:password@api.eventory.se/test",
    ],
)
def test_validate_outbound_integration_url_rejects_credentials(url):
    with pytest.raises(HTTPException) as exc_info:
        settings_router._validate_outbound_integration_url(url)

    assert exc_info.value.status_code == 400
    assert "must not contain credentials" in str(exc_info.value.detail).lower()


def test_validate_outbound_integration_url_rejects_empty_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [])
    with pytest.raises(HTTPException) as exc_info:
        settings_router._validate_outbound_integration_url("https://api.eventory.se/test")
    assert exc_info.value.status_code == 400
    assert "could not be resolved" in str(exc_info.value.detail).lower()


def test_validate_connected_outbound_socket_rejects_private_peer():
    class _DummySocket:
        def getpeername(self):
            return ("127.0.0.1", 443)

        def close(self):
            return None

    with pytest.raises(URLError, match="disallowed network address"):
        settings_router._validate_connected_outbound_socket(_DummySocket())


def test_validate_connected_outbound_socket_rejects_multicast_peer():
    class _DummySocket:
        def getpeername(self):
            return ("224.0.0.1", 443)

        def close(self):
            return None

    with pytest.raises(URLError, match="disallowed network address"):
        settings_router._validate_connected_outbound_socket(_DummySocket())


def test_validate_outbound_integration_url_rejects_multicast(monkeypatch):
    multicast_entry = (None, None, None, None, ("224.0.0.1", 0))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [multicast_entry])
    with pytest.raises(HTTPException) as exc_info:
        settings_router._validate_outbound_integration_url("https://api.eventory.se/test")
    assert exc_info.value.status_code == 400
    assert "non-public" in str(exc_info.value.detail).lower()


def test_is_public_http_url_invalid_port_no_exception():
    # Must return False, not raise ValueError
    assert _is_public_http_url("https://host:99999/") is False


def test_is_public_http_url_port_zero_rejected():
    assert _is_public_http_url("https://host:0/") is False


def test_is_public_http_url_invalid_scheme():
    assert _is_public_http_url("ftp://example.com/") is False


def test_is_public_http_url_rejects_loopback():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.gaierror = socket.gaierror
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 80)),
        ]
        assert _is_public_http_url("http://example.com/") is False


def test_is_public_http_url_rejects_private():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.gaierror = socket.gaierror
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 80)),
        ]
        assert _is_public_http_url("http://example.com/") is False


def test_is_public_http_url_rejects_mixed_public_and_private():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.gaierror = socket.gaierror
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 80)),
        ]
        assert _is_public_http_url("http://example.com/") is False


def test_is_public_http_url_accepts_all_public():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.gaierror = socket.gaierror
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 80)),
        ]
        assert _is_public_http_url("http://example.com/") is True
        assert mock_sock.getaddrinfo.call_args.kwargs["type"] == mock_sock.SOCK_STREAM


def test_is_public_http_url_strips_whitespace():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.gaierror = socket.gaierror
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443)),
        ]
        assert _is_public_http_url("  https://example.com/path  ") is True


def test_is_public_http_url_rejects_embedded_credentials():
    assert _is_public_http_url("https://user@example.com/") is False


def test_validate_outbound_api_url_allows_public_target(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    assert _validate_outbound_api_url("https://example.com:443/test") == "https://example.com:443/test"


def test_validate_outbound_api_url_rejects_shared_cgnat_range(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port, **_kwargs: [(None, None, None, None, ("100.64.0.1", 443))],
    )
    with pytest.raises(ValueError, match="non-public"):
        _validate_outbound_api_url("https://example.com/test")


@pytest.mark.parametrize(
    "ip_address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.1.1",
    ],
)
def test_validate_outbound_api_url_rejects_non_public_ranges(monkeypatch, ip_address):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port, **_kwargs: [(None, None, None, None, (ip_address, 443))],
    )
    with pytest.raises(ValueError, match="non-public"):
        _validate_outbound_api_url("https://example.com/test")


def test_validate_outbound_api_url_rejects_credentials():
    with pytest.raises(ValueError, match="must not contain credentials"):
        _validate_outbound_api_url("http://user@example.com/test")


def test_validate_outbound_api_url_rejects_invalid_port():
    with pytest.raises(ValueError, match="port is invalid"):
        _validate_outbound_api_url("https://example.com:abc/test")


def test_validate_outbound_api_url_rejects_port_zero():
    with pytest.raises(ValueError, match="port is invalid"):
        _validate_outbound_api_url("https://example.com:0/test")


def test_validate_outbound_api_url_normalizes_ipv6_host(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port, **_kwargs: [
            (None, None, None, None, ("2001:4860:4860::8888", 443, 0, 0))
        ],
    )
    assert _validate_outbound_api_url("https://[2001:4860:4860::8888]/test") == "https://[2001:4860:4860::8888]/test"


def test_validate_outbound_api_url_uses_stream_dns_resolution():
    with patch("app.domain.settings.router.socket") as mock_sock:
        mock_sock.SOCK_STREAM = socket.SOCK_STREAM
        mock_sock.getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443)),
        ]
        assert _validate_outbound_api_url("https://example.com/test") == "https://example.com/test"
        assert mock_sock.getaddrinfo.call_args.kwargs["type"] == mock_sock.SOCK_STREAM


def test_validate_outbound_api_url_rejects_empty_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [])
    with pytest.raises(ValueError, match="could not be resolved"):
        _validate_outbound_api_url("https://example.com/test")


def test_fetch_eventory_token_rejects_non_public_endpoint_url():
    with patch("app.domain.settings.router._is_public_http_url", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            _fetch_eventory_token(
                "https://api.example.com",
                "https://api.example.com/oauth/token",
                "user",
                "pass",
            )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Token endpoint must be a valid public http(s) URL"


class _FakeSocket:
    def __init__(self, host: str):
        self.host = host

    def getpeername(self):
        return (self.host, 443)


class _FakeRaw:
    def __init__(self, host: str):
        self._sock = _FakeSocket(host)


class _FakeBuffer:
    def __init__(self, host: str):
        self.raw = _FakeRaw(host)


class _FakeResponse:
    def __init__(self, host: str):
        self.fp = _FakeBuffer(host)


def test_ensure_public_response_peer_rejects_private_ip():
    with pytest.raises(HTTPException) as exc_info:
        _ensure_public_response_peer(_FakeResponse("127.0.0.1"), "Token endpoint")
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Token endpoint connected to a non-public IP address"


def test_ensure_public_response_peer_rejects_shared_cgnat_ip():
    with pytest.raises(HTTPException) as exc_info:
        _ensure_public_response_peer(_FakeResponse("100.64.0.1"), "Token endpoint")
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Token endpoint connected to a non-public IP address"


def test_fetch_eventory_token_rejects_private_peer_after_public_dns_check():
    class FakeTokenResponse(_FakeResponse):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"access_token":"secret"}'

    with patch("app.domain.settings.router._is_public_http_url", return_value=True), patch(
        "app.domain.settings.router._open_outbound_integration_request",
        return_value=FakeTokenResponse("127.0.0.1"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _fetch_eventory_token(
                "https://api.example.com",
                "https://api.example.com/oauth/token",
                "user",
                "pass",
            )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Token endpoint connected to a non-public IP address"


def test_fetch_eventory_token_disallowed_peer_is_terminal(monkeypatch):
    class FakeTokenResponse(_FakeResponse):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"access_token":"secret"}'

    calls: list[str] = []

    def _fake_open(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise URLError("Outbound connection resolved to a disallowed network address")
        return FakeTokenResponse("1.1.1.1")

    monkeypatch.setattr(settings_router, "_is_public_http_url", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(settings_router, "_open_outbound_integration_request", _fake_open)

    with pytest.raises(HTTPException) as exc_info:
        _fetch_eventory_token("https://api.example.com", "", "user", "pass")

    assert calls == ["https://api.example.com/login-json"]
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Token endpoint connected to a non-public IP address"
