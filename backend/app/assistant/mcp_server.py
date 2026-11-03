"""
MCP server exposing the Stockwire Assistant tools to outside agents.

This module deliberately reuses the *same* tool definitions and execution
handlers as the internal SSE chat endpoint (``app.assistant.tools``). That keeps
a single source of truth: adding or changing a tool in ``tools.TOOLS`` /
``tools.execute_tool`` automatically benefits both the in-app chat and any MCP
client, with no duplicated schema or logic.

The OpenAI-style ``function`` tool entries in ``tools.TOOLS`` are JSON-Schema
compatible, so each one is turned into an MCP tool by mapping:

    function.name        -> tool name
    function.description  -> tool description
    function.parameters   -> argument schema (used to build the function signature)

An MCP client (Claude Desktop, OpenCode, a remote agent, ...) talks to this
server over stdio (default) or SSE / streamable-http. Each tool call opens its
own database session, runs ``execute_tool``, and serialises the result to JSON.

Security note
-------------
The MCP server connects directly to the database and bypasses the FastAPI auth
layer, so it is an admin-equivalent, privileged surface. Run it only where the
agent is trusted. Set ``STOCKWIRE_MCP_READONLY=true`` to expose read-only tools
only (disabling all registered write tools).
"""

import inspect
import json
import os
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.assistant.mcp_oauth import get_mcp_claims
from app.assistant.tools import TOOLS, WRITE_TOOLS, execute_tool
from app.db.session import SessionLocal

# MCPServer (the v2 high-level API; the old ``FastMCP`` was renamed) is imported
# lazily so the shared tool specs (``iter_mcp_specs``) stay importable for unit
# tests even when the optional ``mcp`` dependency is absent.
try:  # pragma: no cover - exercised only when mcp is installed
    from mcp.server.mcpserver import MCPServer

    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    MCPServer = None
    _MCP_AVAILABLE = False

# Map JSON-Schema primitive types to Python types used for the dynamic
# function signature. Anything unknown falls back to ``str``.
_JSON_TYPE_TO_PY = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _readonly_mode() -> bool:
    return os.getenv("STOCKWIRE_MCP_READONLY", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def iter_mcp_specs(readonly: bool | None = None) -> list[dict[str, Any]]:
    """Yield MCP tool specs derived from the shared ``TOOLS`` registry.

    Each spec is ``{"name", "description", "parameters"}`` where ``parameters``
    is the JSON-Schema argument object from the OpenAI-style tool definition.

    ``readonly`` overrides the ``STOCKWIRE_MCP_READONLY`` env var when given.
    """
    if readonly is None:
        readonly = _readonly_mode()
    specs: list[dict[str, Any]] = []
    for tool in TOOLS:
        fn = tool.get("function", {})
        name = fn.get("name")
        if not name:
            continue
        if readonly and name in WRITE_TOOLS:
            continue
        specs.append(
            {
                "name": name,
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return specs


def _build_handler(spec: dict[str, Any]):
    """Create a callable that proxies an assistant tool through a DB session."""
    tool_name = spec["name"]
    params = spec["parameters"] or {"type": "object", "properties": {}}
    properties: dict[str, Any] = params.get("properties", {})
    required: set[str] = set(params.get("required", []))

    # Build a concrete signature so FastMCP (and pydantic) can derive the
    # input schema directly from the function, without re-parsing JSON-Schema.
    sig_params: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {}
    for pname, pschema in properties.items():
        ptype = _JSON_TYPE_TO_PY.get(pschema.get("type", "string"), str)
        if pname in required:
            annotations[pname] = ptype
            default = inspect.Parameter.empty
        else:
            annotations[pname] = ptype | None
            default = None
        sig_params.append(
            inspect.Parameter(
                pname,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=ptype,
            )
        )
    signature = inspect.Signature(sig_params)

    def handler(**kwargs: Any) -> str:
        # Gate write tools to admins (matches the SSE chat's existing policy).
        if tool_name in WRITE_TOOLS:
            claims = get_mcp_claims()
            if not claims or claims.get("role") != "admin":
                return json.dumps({"error": "Admin privileges required for this tool"})
        try:
            db = SessionLocal()
        except SQLAlchemyError as exc:  # pragma: no cover - depends on live DB
            return json.dumps({"error": f"Database connection failed: {exc}"})
        try:
            result = execute_tool(tool_name, kwargs, db)
        except SQLAlchemyError as exc:  # execute_tool normally catches, but be safe
            result = {"error": f"Database error: {exc}"}
        finally:
            db.close()
        return json.dumps(result, default=str)

    handler.__signature__ = signature  # type: ignore[attr-defined]
    handler.__annotations__ = annotations
    handler.__name__ = tool_name
    handler.__doc__ = spec.get("description", "")
    return handler


def build_server(
    name: str = "stockwire-assistant",
    token_verifier: Any = None,
    auth: Any = None,
) -> "MCPServer":
    """Construct the MCPServer and register every shared assistant tool.

    When ``token_verifier`` (and matching ``auth`` settings) are provided the
    streamable-HTTP endpoint is protected: only requests bearing a valid access
    token are accepted. This is how the server is mounted inside FastAPI.
    """
    if not _MCP_AVAILABLE:
        raise RuntimeError(
            "The 'mcp' package is required to run the MCP server. "
            "Install the backend dependencies (e.g. `pip install -e .`)."
        )
    server = MCPServer(name, token_verifier=token_verifier, auth=auth)
    for spec in iter_mcp_specs():
        server.tool(name=spec["name"], description=spec.get("description", ""))(
            _build_handler(spec)
        )
    return server


# Shared server instance used by ``python -m app.assistant.mcp_server``.
# ``None`` when the optional ``mcp`` dependency is not installed.
mcp = build_server() if _MCP_AVAILABLE else None


def main() -> None:
    """Entry point: ``python -m app.assistant.mcp_server``."""
    server = build_server()
    transport = os.getenv("STOCKWIRE_MCP_TRANSPORT", "stdio").lower()
    if transport == "stdio":
        server.run(transport="stdio")
        return

    if transport in {"sse", "streamable-http"}:
        server.run(
            transport=transport,
            host=os.getenv("STOCKWIRE_MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("STOCKWIRE_MCP_PORT", "8001")),
        )
        return

    raise SystemExit(f"Unknown STOCKWIRE_MCP_TRANSPORT: {transport!r}")


if __name__ == "__main__":
    main()
