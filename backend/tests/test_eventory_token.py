import pytest
import socket
from urllib.parse import urljoin

from fastapi import HTTPException

from app.domain.settings.router import _url_origin, _is_same_origin_url, _fetch_eventory_token, _validate_outbound_api_url


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


def test_validate_outbound_api_url_allows_public_target(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    assert _validate_outbound_api_url("https://example.com:443/test") == "https://example.com:443/test"


def test_validate_outbound_api_url_rejects_shared_cgnat_range(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(None, None, None, None, ("100.64.0.1", 443))],
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
        router.socket,
        "getaddrinfo",
        lambda _host, _port: [(None, None, None, None, (ip_address, 443))],
    )
    with pytest.raises(ValueError, match="non-public"):
        _validate_outbound_api_url("https://example.com/test")


def test_validate_outbound_api_url_rejects_credentials():
    with pytest.raises(ValueError, match="must not contain credentials"):
        _validate_outbound_api_url("http://user@example.com/test")


def test_validate_outbound_api_url_rejects_invalid_port():
    with pytest.raises(ValueError, match="port is invalid"):
        _validate_outbound_api_url("https://example.com:abc/test")


def test_validate_outbound_api_url_normalizes_ipv6_host(monkeypatch):
    monkeypatch.setattr(
        router.socket,
        "getaddrinfo",
        lambda _host, _port: [(None, None, None, None, ("2001:4860:4860::8888", 443, 0, 0))],
    )
    assert _validate_outbound_api_url("https://[2001:4860:4860::8888]/test") == "https://[2001:4860:4860::8888]/test"
