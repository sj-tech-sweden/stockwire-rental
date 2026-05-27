import socket
import pytest
from unittest.mock import patch
from urllib.parse import urljoin

from fastapi import HTTPException

from app.domain.settings.router import _url_origin, _is_same_origin_url, _fetch_eventory_token, _is_public_http_url


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


def _mock_socket(addresses):
    """Return a mock for app.domain.settings.router.socket with given address list."""
    return {
        "return_value": [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", (addr, 80))
            for addr in addresses
        ]
    }


def test_is_public_http_url_invalid_port_no_exception():
    # Must return False, not raise ValueError
    assert _is_public_http_url("https://host:99999/") is False


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
