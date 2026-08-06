"""
AI Assistant chat endpoint with SSE streaming and tool calling.

Supports OpenAI-compatible APIs (Ollama, Gemini, OpenAI, OpenCode).
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.settings.models import AppSetting
from app.domain.settings.router import INTEGRATIONS_KEY, _parse_integrations
from app.assistant.schemas import ChatRequest
from app.assistant.tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

SYSTEM_PROMPT = """You are Stockwire Assistant, an AI helper for the Stockwire Rental inventory management system.

You can help users with:
- Checking inventory stock and availability
- Looking up rental rates and pricing
- Searching for customers and suppliers
- Finding products by name, category, or type
- Listing recent jobs and their status
- Browsing product categories
- Updating product information (manufacturer, category)

IMPORTANT RULES:
- When users ask about a product by number (e.g., "1510"), first search for it using search_products to find the full name. Then use check_inventory_stock with the full product name (e.g., "Pelican 1510").
- Always use full product names or SKU codes when calling tools, never just numbers.
- When users ask about availability for a vague date (e.g., "next weekend"), ASK them to clarify which specific dates they mean. For example: "Do you mean this weekend (Aug 2-3) or next weekend (Aug 9-10)?" Then use the clarified dates.
- When users ask about future availability, explain that you can only show current stock levels, not future reservations.
- When a tool call fails, explain what went wrong and suggest alternatives.
- For batch operations (like updating multiple products), use batch_update_manufacturers instead of calling update_product_manufacturer multiple times.

Be concise and helpful. Always ask clarifying questions when the user's request is ambiguous."""


def _get_llm_settings(db) -> dict:
    """Load LLM settings from the database (integrations config)."""
    default = {
        "base_url": settings.llm_base_url,
        "api_key": settings.llm_api_key,
        "model": settings.llm_model,
    }
    try:
        setting = db.execute(select(AppSetting).where(AppSetting.key == INTEGRATIONS_KEY)).scalar_one_or_none()
        if not setting:
            logger.warning("No integrations setting found in DB")
            return default
        if not setting.value_json:
            logger.warning("Integrations value_json is empty")
            return default
        integrations = _parse_integrations(setting.value_json)
        llm = integrations.get("llm")
        logger.info("LLM config from DB: %s", json.dumps(llm) if llm else "None")
        if isinstance(llm, dict) and llm.get("base_url"):
            result = {
                "base_url": str(llm.get("base_url", "")).strip() or default["base_url"],
                "api_key": str(llm.get("api_key", "")).strip() or default["api_key"],
                "model": str(llm.get("model", "")).strip() or default["model"],
            }
            logger.info("Resolved LLM: base_url=%s model=%s", result["base_url"], result["model"])
            return result
    except Exception as e:
        logger.warning("Failed to load LLM settings: %s", e)
    return default


def _get_client(db=None) -> AsyncOpenAI:
    """Create an OpenAI-compatible client from DB or config LLM settings."""
    if db:
        llm = _get_llm_settings(db)
    else:
        llm = {"base_url": settings.llm_base_url, "api_key": settings.llm_api_key, "model": settings.llm_model}

    base_url = str(llm.get("base_url") or "").strip()
    api_key = str(llm.get("api_key") or "").strip() or "ollama"

    if not base_url:
        base_url = settings.llm_base_url

    return AsyncOpenAI(base_url=base_url, api_key=api_key)


@router.post("/chat")
async def chat(request: ChatRequest, db=Depends(get_db), _user=Depends(require_admin)):
    """Stream a chat response with optional tool calling."""

    llm = _get_llm_settings(db)
    base_url = str(llm.get("base_url") or "").strip()
    api_key = str(llm.get("api_key") or "").strip()
    model = str(llm.get("model") or "").strip()

    if not base_url:
        base_url = settings.llm_base_url
    if not api_key:
        api_key = "ollama"

    logger.info("chat: base_url=%s model=%s api_key_len=%d", base_url, model, len(api_key))

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def event_stream():
        model = llm.get("model") or settings.llm_model
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in request.messages:
                messages.append({"role": m.role, "content": m.content})

            max_iterations = 5
            for _ in range(max_iterations):
                full_response = ""
                tool_calls_raw = []

                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS if TOOLS else None,
                    tool_choice="auto" if TOOLS else None,
                    stream=True,
                )

                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    if delta.content:
                        full_response += delta.content
                        yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            while len(tool_calls_raw) <= idx:
                                tool_calls_raw.append({"id": "", "function": {"name": "", "arguments": ""}})
                            if tc.id:
                                tool_calls_raw[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_raw[idx]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_raw[idx]["function"]["arguments"] += tc.function.arguments

                if not tool_calls_raw:
                    break

                assistant_message = {"role": "assistant", "content": full_response or None}
                assistant_message["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in tool_calls_raw
                    if tc["function"]["name"]
                ]
                messages.append(assistant_message)

                for tc in tool_calls_raw:
                    if not tc["function"]["name"]:
                        continue
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': tc['function']['name'], 'args': args})}\n\n"

                    result = execute_tool(tc["function"]["name"], args, db)
                    result_str = json.dumps(result, default=str)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_str,
                    })

                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': tc['function']['name'], 'result': result})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("Assistant chat error")
            raw_error_msg = str(e)
            error_msg = "An internal error occurred while processing your request."
            if "Connection" in raw_error_msg or "connect" in raw_error_msg.lower() or "Errno" in raw_error_msg:
                error_msg = f"Cannot connect to LLM at {base_url}. Is the server running?"
            elif "401" in raw_error_msg or "unauthorized" in raw_error_msg.lower() or "Invalid API Key" in raw_error_msg:
                error_msg = f"Authentication failed. Check your API key for {base_url}."
            elif "403" in raw_error_msg or "forbidden" in raw_error_msg.lower():
                try:
                    import httpx
                    resp = httpx.post(
                        base_url + "/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
                        timeout=10,
                        follow_redirects=True,
                    )
                    body = resp.json() if resp.status_code >= 400 else {}
                    api_msg = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else ""
                    error_msg = f"Access denied: {api_msg}" if api_msg else f"Access denied by {base_url}. Check model availability."
                except Exception:
                    error_msg = f"Access denied by {base_url}. Check your API key permissions and model availability."
            elif "404" in raw_error_msg:
                error_msg = f"Model '{model}' not found. Fetch models in Settings > AI Assistant to see available options."
            elif "429" in raw_error_msg or "rate" in raw_error_msg.lower():
                error_msg = "Rate limited by the LLM provider. Try again shortly."
            elif "timeout" in raw_error_msg.lower():
                error_msg = f"Connection to {base_url} timed out."
            elif "str" in raw_error_msg and "_set_private_attributes" in raw_error_msg:
                error_msg = f"API at {base_url} returned an incompatible response format."
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/test-connection")
async def test_connection(db=Depends(get_db), _user=Depends(get_current_user)):
    """Test connection to the configured LLM backend."""
    llm = _get_llm_settings(db)
    base_url = llm.get("base_url", "")
    model = llm.get("model", "")
    try:
        logger.info("Creating AsyncOpenAI client: base_url=%s api_key_type=%s", base_url, type(llm.get("api_key")).__name__)
        client = AsyncOpenAI(
            base_url=str(base_url or ""),
            api_key=str(llm.get("api_key") or "ollama"),
        )
        logger.info("Client created, calling models.list()")
        models = await client.models.list()
        model_count = len(models.data) if hasattr(models, 'data') else 0
        return {
            "ok": True,
            "base_url": base_url,
            "model": model,
            "models_available": model_count,
            "message": f"Connected to {base_url}. {model_count} model(s) available.",
        }
    except Exception as e:
        logger.exception("test_connection error")
        raw_error_msg = str(e)
        raw_error_lower = raw_error_msg.lower()
        error_msg = "Unable to complete connection test due to an internal error."
        if "str" in raw_error_msg and "_set_private_attributes" in raw_error_msg:
            # Try to get the actual response body for debugging
            extra = ""
            try:
                import httpx
                resp = httpx.get(base_url + "/models", headers={"Authorization": f"Bearer {llm.get('api_key', '')}"}, timeout=10, follow_redirects=True)
                extra = f" (status={resp.status_code}, body={resp.text[:300]})"
            except Exception:
                pass
            error_msg = f"API at {base_url}/models returned incompatible response.{extra}"
        elif "connection" in raw_error_lower or "connect" in raw_error_lower or "errno" in raw_error_lower:
            error_msg = f"Cannot connect to {base_url}. Is the server running?"
        elif "401" in raw_error_msg or "unauthorized" in raw_error_lower or "invalid api key" in raw_error_lower:
            extra = ""
            try:
                import httpx
                resp = httpx.post(
                    base_url + "/chat/completions",
                    headers={"Authorization": f"Bearer {llm.get('api_key', '')}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=10,
                    follow_redirects=True,
                )
                extra = f" (status={resp.status_code}, body={resp.text[:300]})"
            except Exception:
                pass
            error_msg = f"Authentication failed for {base_url}.{extra}"
        elif "403" in raw_error_msg or "forbidden" in raw_error_lower:
            extra = ""
            try:
                import httpx
                resp = httpx.post(
                    base_url + "/chat/completions",
                    headers={"Authorization": f"Bearer {llm.get('api_key', '')}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
                    timeout=10,
                    follow_redirects=True,
                )
                body = resp.json() if resp.status_code >= 400 else {}
                api_msg = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else ""
                if api_msg:
                    error_msg = f"Access denied: {api_msg}"
                else:
                    error_msg = f"Access denied by {base_url}. Check your API key permissions and model availability."
            except Exception:
                error_msg = f"Access denied by {base_url}. Check your API key permissions and model availability."
        elif "404" in raw_error_msg:
            error_msg = f"Model '{model}' not found. Fetch models to see available options."
        elif "429" in raw_error_msg or "rate" in raw_error_lower:
            error_msg = "Rate limited by the LLM provider. Try again shortly."
        elif "timeout" in raw_error_lower:
            error_msg = f"Connection to {base_url} timed out."
        return {
            "ok": False,
            "base_url": base_url,
            "model": model,
            "message": error_msg,
        }


@router.get("/debug/llm-settings")
async def debug_llm_settings(db=Depends(get_db), _user=Depends(require_admin)):
    """Debug endpoint to see raw LLM settings from DB (admin only)."""
    llm = _get_llm_settings(db)
    masked = {**llm, "api_key": "***" if llm.get("api_key") else ""}
    return {"llm": masked, "llm_type": str(type(llm))}


@router.get("/models")
async def list_models(db=Depends(get_db), _user=Depends(get_current_user)):
    """List available models from the configured LLM backend."""
    try:
        llm = _get_llm_settings(db)
        client = AsyncOpenAI(
            base_url=str(llm.get("base_url") or ""),
            api_key=str(llm.get("api_key") or "ollama"),
        )
        models = await client.models.list()
        model_list = [
            {"id": m.id, "owned_by": getattr(m, 'owned_by', '')}
            for m in (models.data if hasattr(models, 'data') else [])
        ]
        return {"models": model_list, "count": len(model_list)}
    except Exception as e:
        error_msg = str(e)
        if "str" in error_msg and "_set_private_attributes" in error_msg:
            return {"models": [], "count": 0, "error": f"API returned an unexpected response format. The server may not be fully OpenAI-compatible."}
        logger.exception("Failed to list models from configured LLM backend")
        return {"models": [], "count": 0, "error": "Unable to list models at this time."}


@router.post("/test-model")
async def test_model(
    payload: dict,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """Test a specific model with a simple prompt."""
    model_id = payload.get("model", "")
    if not model_id:
        return {"ok": False, "error": "No model specified"}

    llm = _get_llm_settings(db)
    base_url = str(llm.get("base_url") or "")
    api_key = str(llm.get("api_key") or "ollama")

    try:
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        response = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Say hello in one sentence."}],
            max_tokens=50,
        )
        reply = response.choices[0].message.content if response.choices else ""
        return {"ok": True, "model": model_id, "response": reply}
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            try:
                import httpx
                resp = httpx.post(
                    base_url + "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_id, "messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
                    timeout=10,
                    follow_redirects=True,
                )
                body = resp.json() if resp.status_code >= 400 else {}
                api_msg = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else ""
                return {"ok": False, "error": api_msg or f"Model {model_id} not available"}
            except Exception:
                return {"ok": False, "error": f"Model {model_id} not available or restricted"}
        logger.exception("Unexpected error while testing model '%s'", model_id)
        return {"ok": False, "error": "Unable to test model due to an internal error"}
