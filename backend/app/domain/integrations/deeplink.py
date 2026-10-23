"""Signed deeplink tokens for the Stagewire ⇄ stockwire-rental job linking.

A deeplink token is an HMAC-SHA256 signature over a JSON payload:

    { "src": "stagewire"|"stockwire", "job_id": <int>, "instance_id": <str>,
      "ts": <unix seconds>, "nonce": <random> }

The token is ``<base64url(payload)>.<base64url(hmac)>``. The HMAC secret is the
integration instance's stored API key (``api_key``), so each linked instance has
its own secret and the raw key is never placed in the token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid

DEFAULT_TTL_SECONDS = 900


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded)


def _normalize_secret(secret: str) -> bytes:
    return secret.encode("utf-8")


def sign_deeplink(
    secret: str,
    *,
    src: str,
    job_id: int | str,
    instance_id: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Create a signed deeplink token for a job."""
    payload = {
        "src": src,
        # Rental job ids are integers; Stagewire job ids are UUIDs. Keep each as-is.
        "job_id": int(job_id) if str(job_id).strip().isdigit() else str(job_id).strip(),
        "instance_id": str(instance_id),
        "ts": int(time.time()),
        "nonce": uuid.uuid4().hex,
        "ttl": int(ttl_seconds),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(_normalize_secret(secret), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def verify_deeplink(secret: str, token: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict:
    """Verify a deeplink token and return its payload.

    Raises ``ValueError`` on a malformed, tampered, or expired token.
    """
    if not token or "." not in token:
        raise ValueError("Malformed deeplink token")
    payload_b64, sig_b64 = token.split(".", 1)
    try:
        payload_bytes = _b64url_decode(payload_b64)
        provided_sig = _b64url_decode(sig_b64)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Malformed deeplink token") from exc

    expected_sig = hmac.new(_normalize_secret(secret), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Deeplink token signature is invalid")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Deeplink token payload is invalid") from exc

    ts = int(payload.get("ts", 0))
    ttl = int(payload.get("ttl", ttl_seconds))
    if ts <= 0 or (time.time() - ts) > ttl:
        raise ValueError("Deeplink token has expired")

    return payload


def generate_link_secret() -> str:
    """Generate a fresh random secret for a new integration instance."""
    return os.urandom(32).hex()


def peek_deeplink_instance_id(token: str) -> str | None:
    """Read ``instance_id`` from an unverified token (to locate the secret).

    Returns ``None`` for a malformed token. Does not validate the signature or
    expiry — callers must still verify the token with the matching secret.
    """
    if not token or "." not in token:
        return None
    payload_b64 = token.split(".", 1)[0]
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    value = payload.get("instance_id")
    return str(value).strip() if value is not None else None
