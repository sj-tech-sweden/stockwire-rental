import pytest
from urllib.parse import urljoin

from fastapi import HTTPException

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
