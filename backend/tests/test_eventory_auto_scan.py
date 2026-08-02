"""Tests for the Eventory auto-scan feature (auto_scan_out_on_receive and auto_scan_in_on_return)."""

import json
from unittest.mock import MagicMock, patch

from app.domain.inventory.router import _trigger_eventory_auto_scan
from app.domain.settings.router import (
    _eventory_scan_in_pack_list,
    _eventory_scan_out_pack_list,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(
    external_reference: str | None = "eventory-main:42",
    eventory_packlists_json: str | None = None,
) -> MagicMock:
    product = MagicMock()
    product.external_reference = external_reference
    product.eventory_packlists_json = eventory_packlists_json
    return product


def _make_db(instance_cfg: dict | None = None) -> MagicMock:
    """Return a mock db that returns a fake AppSetting with the given instance config."""
    if instance_cfg is None:
        instance_cfg = {
            "id": "eventory-main",
            "enabled": True,
            "api_url": "https://api.eventory.se",
            "api_key": "key123",
            "username": "",
            "password": "",
            "token_endpoint": "",
            "auto_scan_out_on_receive": True,
            "auto_scan_in_on_return": True,
        }

    setting = MagicMock()
    setting.value_json = json.dumps({
        "eventory_instances": [instance_cfg],
        "productionplanner": {},
        "stockwire_instances": [],
    })

    db = MagicMock()
    db.scalar.return_value = setting
    return db


# ---------------------------------------------------------------------------
# _eventory_scan_out_pack_list / _eventory_scan_in_pack_list
# ---------------------------------------------------------------------------


def test_scan_out_calls_correct_endpoint(monkeypatch):
    captured = {}

    def _fake_open(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.method
        ctx = MagicMock()
        ctx.__enter__ = lambda s: s
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    monkeypatch.setattr(
        "app.domain.settings.router._open_outbound_integration_request", _fake_open
    )
    monkeypatch.setattr(
        "app.domain.settings.router._validate_outbound_integration_url", lambda url: url
    )

    _eventory_scan_out_pack_list(
        "https://api.eventory.se", {"Accept": "application/json"}, "pl-123"
    )

    assert captured["url"] == "https://api.eventory.se/pack-lists/pl-123/scan-out"
    assert captured["method"] == "POST"


def test_scan_in_calls_correct_endpoint(monkeypatch):
    captured = {}

    def _fake_open(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.method
        ctx = MagicMock()
        ctx.__enter__ = lambda s: s
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    monkeypatch.setattr(
        "app.domain.settings.router._open_outbound_integration_request", _fake_open
    )
    monkeypatch.setattr(
        "app.domain.settings.router._validate_outbound_integration_url", lambda url: url
    )

    _eventory_scan_in_pack_list(
        "https://api.eventory.se", {"Accept": "application/json"}, "pl-456"
    )

    assert captured["url"] == "https://api.eventory.se/pack-lists/pl-456/scan-in"
    assert captured["method"] == "POST"


def test_scan_out_is_silent_on_network_error(monkeypatch):
    """scan-out must not raise even if the network call fails."""
    from urllib.error import URLError

    def _fake_open(req, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr(
        "app.domain.settings.router._open_outbound_integration_request", _fake_open
    )
    monkeypatch.setattr(
        "app.domain.settings.router._validate_outbound_integration_url", lambda url: url
    )

    # Must not raise
    _eventory_scan_out_pack_list(
        "https://api.eventory.se", {"Accept": "application/json"}, "pl-000"
    )


def test_scan_in_is_silent_on_network_error(monkeypatch):
    """scan-in must not raise even if the network call fails."""
    from urllib.error import URLError

    def _fake_open(req, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr(
        "app.domain.settings.router._open_outbound_integration_request", _fake_open
    )
    monkeypatch.setattr(
        "app.domain.settings.router._validate_outbound_integration_url", lambda url: url
    )

    # Must not raise
    _eventory_scan_in_pack_list(
        "https://api.eventory.se", {"Accept": "application/json"}, "pl-000"
    )


# ---------------------------------------------------------------------------
# _trigger_eventory_auto_scan – unit tests
# ---------------------------------------------------------------------------


def test_trigger_scan_out_skips_when_flag_disabled():
    """auto_scan_out_on_receive=False → no Eventory call."""
    db = _make_db({
        "id": "eventory-main",
        "enabled": True,
        "api_url": "https://api.eventory.se",
        "api_key": "k",
        "username": "",
        "password": "",
        "token_endpoint": "",
        "auto_scan_out_on_receive": False,
        "auto_scan_in_on_return": True,
    })
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 0, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        mock_out.assert_not_called()


def test_trigger_scan_in_skips_when_flag_disabled():
    """auto_scan_in_on_return=False → no Eventory call."""
    db = _make_db({
        "id": "eventory-main",
        "enabled": True,
        "api_url": "https://api.eventory.se",
        "api_key": "k",
        "username": "",
        "password": "",
        "token_endpoint": "",
        "auto_scan_out_on_receive": True,
        "auto_scan_in_on_return": False,
    })
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 2, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_in_pack_list") as mock_in:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_in")
        mock_in.assert_not_called()


def test_trigger_scan_out_skips_already_fully_scanned():
    """out >= quantity → already scanned out → no Eventory call."""
    db = _make_db()
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 2, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        mock_out.assert_not_called()


def test_trigger_scan_in_skips_when_nothing_scanned_out():
    """out == 0 → nothing to scan back in → no Eventory call."""
    db = _make_db()
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 0, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_in_pack_list") as mock_in:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_in")
        mock_in.assert_not_called()


def test_trigger_scan_out_calls_for_active_packlists_with_remaining():
    """Scan-out fires for active pack lists where out < quantity."""
    db = _make_db()
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 1, "source": "active"},
            {"pack_list_id": "pl-2", "quantity": 3, "out": 3, "source": "active"},  # already full
            {"pack_list_id": "pl-3", "quantity": 1, "out": 0, "source": "archived"},  # archived – skip
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out, \
         patch("app.domain.inventory.router._eventory_set_headers"), \
         patch("app.domain.inventory.router._fetch_eventory_token", return_value=""):
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        # Only pl-1 qualifies (active, out < quantity)
        mock_out.assert_called_once()
        args = mock_out.call_args[0]
        assert args[2] == "pl-1"


def test_trigger_scan_in_calls_for_active_packlists_with_out_gt_zero():
    """Scan-in fires for active pack lists where out > 0."""
    db = _make_db()
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 2, "source": "active"},
            {"pack_list_id": "pl-2", "quantity": 3, "out": 0, "source": "active"},  # nothing out
            {"pack_list_id": "pl-3", "quantity": 1, "out": 1, "source": "archived"},  # archived – skip
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_in_pack_list") as mock_in, \
         patch("app.domain.inventory.router._eventory_set_headers"), \
         patch("app.domain.inventory.router._fetch_eventory_token", return_value=""):
        _trigger_eventory_auto_scan(db, product, scan_action="scan_in")
        # Only pl-1 qualifies (active, out > 0)
        mock_in.assert_called_once()
        args = mock_in.call_args[0]
        assert args[2] == "pl-1"


def test_trigger_scan_skips_disabled_instance():
    """If the Eventory instance is disabled, no scan is triggered."""
    db = _make_db({
        "id": "eventory-main",
        "enabled": False,
        "api_url": "https://api.eventory.se",
        "api_key": "k",
        "username": "",
        "password": "",
        "token_endpoint": "",
        "auto_scan_out_on_receive": True,
        "auto_scan_in_on_return": True,
    })
    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 0, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        mock_out.assert_not_called()


def test_trigger_scan_skips_product_without_external_reference():
    """Products without an external_reference are not rental products from Eventory."""
    db = _make_db()
    product = _make_product(external_reference=None, eventory_packlists_json="[]")

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        mock_out.assert_not_called()


def test_trigger_scan_skips_missing_instance():
    """If the instance_id from external_reference doesn't exist in config, no scan."""
    db = _make_db({
        "id": "different-instance",
        "enabled": True,
        "api_url": "https://api.eventory.se",
        "api_key": "k",
        "username": "",
        "password": "",
        "token_endpoint": "",
        "auto_scan_out_on_receive": True,
        "auto_scan_in_on_return": True,
    })
    product = _make_product(
        external_reference="eventory-main:42",  # different instance
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 0, "source": "active"}
        ])
    )

    with patch("app.domain.inventory.router._eventory_scan_out_pack_list") as mock_out:
        _trigger_eventory_auto_scan(db, product, scan_action="scan_out")
        mock_out.assert_not_called()


def test_trigger_scan_is_silent_on_unexpected_exception():
    """Any unexpected exception must be swallowed to avoid disrupting the local scan."""
    db = MagicMock()
    db.scalar.side_effect = RuntimeError("DB explosion")

    product = _make_product(
        eventory_packlists_json=json.dumps([
            {"pack_list_id": "pl-1", "quantity": 2, "out": 0, "source": "active"}
        ])
    )

    # Must not raise
    _trigger_eventory_auto_scan(db, product, scan_action="scan_out")


# ---------------------------------------------------------------------------
# Schema – EventoryInstanceConfig includes the new fields
# ---------------------------------------------------------------------------


def test_eventory_instance_config_defaults():
    from app.domain.settings.schemas import EventoryInstanceConfig

    cfg = EventoryInstanceConfig(id="x", name="X")
    assert cfg.auto_scan_out_on_receive is False
    assert cfg.auto_scan_in_on_return is False


def test_eventory_instance_config_accepts_true_values():
    from app.domain.settings.schemas import EventoryInstanceConfig

    cfg = EventoryInstanceConfig(
        id="x",
        name="X",
        auto_scan_out_on_receive=True,
        auto_scan_in_on_return=True,
    )
    assert cfg.auto_scan_out_on_receive is True
    assert cfg.auto_scan_in_on_return is True


# ---------------------------------------------------------------------------
# _normalize_plugin_config preserves the new fields
# ---------------------------------------------------------------------------


def test_normalize_plugin_config_preserves_auto_scan_fields():
    from app.domain.settings.schemas import EventoryInstanceConfig
    from app.domain.settings.router import _normalize_plugin_config

    cfg = EventoryInstanceConfig(
        id="x",
        name="X",
        auto_scan_out_on_receive=True,
        auto_scan_in_on_return=True,
    )
    result = _normalize_plugin_config(cfg)
    assert result["auto_scan_out_on_receive"] is True
    assert result["auto_scan_in_on_return"] is True


def test_normalize_plugin_config_defaults_auto_scan_fields():
    from app.domain.settings.schemas import EventoryInstanceConfig
    from app.domain.settings.router import _normalize_plugin_config

    cfg = EventoryInstanceConfig(id="x", name="X")
    result = _normalize_plugin_config(cfg)
    assert result["auto_scan_out_on_receive"] is False
    assert result["auto_scan_in_on_return"] is False
