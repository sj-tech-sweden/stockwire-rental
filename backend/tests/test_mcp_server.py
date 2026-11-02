"""Tests for the MCP server's shared tool-spec logic.

These tests intentionally do not require the optional ``mcp`` package or a live
database: they verify that ``iter_mcp_specs`` mirrors the single source of truth
in ``app.assistant.tools`` (so the SSE chat and the MCP server never drift).
"""

from app.assistant import mcp_server
from app.assistant.mcp_server import WRITE_TOOLS
from app.assistant.tools import TOOLS


def test_specs_mirror_tools_source_of_truth():
    specs = mcp_server.iter_mcp_specs(readonly=False)
    expected_names = {t["function"]["name"] for t in TOOLS}
    got_names = {s["name"] for s in specs}
    assert got_names == expected_names
    # Every spec carries a name, description and JSON-Schema parameters.
    for spec in specs:
        assert spec["name"]
        assert isinstance(spec["description"], str)
        assert spec["parameters"]["type"] == "object"
        assert "properties" in spec["parameters"]


def test_readonly_mode_excludes_write_tools():
    specs = mcp_server.iter_mcp_specs(readonly=True)
    names = {s["name"] for s in specs}
    assert WRITE_TOOLS.isdisjoint(names)
    # Read-only tools are still present.
    assert "check_inventory_stock" in names
    assert "list_jobs" in names


def test_readonly_mode_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("STOCKWIRE_MCP_READONLY", "true")
    specs = mcp_server.iter_mcp_specs()
    names = {s["name"] for s in specs}
    assert WRITE_TOOLS.isdisjoint(names)

    monkeypatch.setenv("STOCKWIRE_MCP_READONLY", "false")
    specs = mcp_server.iter_mcp_specs()
    names = {s["name"] for s in specs}
    assert WRITE_TOOLS.issubset(names)


def test_handler_signature_matches_parameters():
    # The dynamic handler must accept exactly the declared parameters so an MCP
    # client can call it. ``check_inventory_stock`` declares a required
    # ``item_name`` and no optional params.
    spec = next(s for s in mcp_server.iter_mcp_specs() if s["name"] == "check_inventory_stock")
    handler = mcp_server._build_handler(spec)
    import inspect

    sig = inspect.signature(handler)
    assert set(sig.parameters) == {"item_name"}
    # ``item_name`` is required (no default).
    assert sig.parameters["item_name"].default is inspect.Parameter.empty
