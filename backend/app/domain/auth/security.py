from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets

import bcrypt
from jose import jwt

from app.config import settings


def _prepare_password(password: str) -> bytes:
    b = password.encode('utf-8')
    # bcrypt input limit is 72 bytes; for longer inputs, use SHA256 pre-hash
    if len(b) > 72:
        return hashlib.sha256(b).digest()
    return b


def hash_password(password: str) -> str:
    pw = _prepare_password(password)
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    pw = _prepare_password(plain)
    try:
        return bcrypt.checkpw(pw, hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": str(user_id), "email": email, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def _get_api_key_pepper() -> str:
    pepper = os.getenv("API_KEY_PEPPER")
    if pepper:
        return pepper
    app_env_raw = os.getenv("APP_ENV")
    if app_env_raw and app_env_raw.strip().lower() in {"development", "test"}:
        return "stockwire-default-api-key-pepper"
    raise RuntimeError("API_KEY_PEPPER must be set outside development/test environments")


def validate_api_key_pepper() -> None:
    """Call at application startup to fail fast if API_KEY_PEPPER is misconfigured."""
    _get_api_key_pepper()


_DEFAULT_PBKDF2_ITERATIONS = 310_000
_MIN_PBKDF2_ITERATIONS = 100_000
_MAX_PBKDF2_ITERATIONS = 1_000_000
_PBKDF2_SALT_BYTES = 16
_PBKDF2_DIGEST_BYTES = 32


def _get_pbkdf2_iterations() -> int:
    raw = os.getenv("API_KEY_PBKDF2_ITERATIONS", str(_DEFAULT_PBKDF2_ITERATIONS))
    try:
        iterations = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_PBKDF2_ITERATIONS
    if iterations < _MIN_PBKDF2_ITERATIONS or iterations > _MAX_PBKDF2_ITERATIONS:
        return _DEFAULT_PBKDF2_ITERATIONS
    return iterations


def hash_api_key(raw: str) -> str:
    """Return versioned PBKDF2-HMAC-SHA256 hash string for API keys."""
    pepper = _get_api_key_pepper()
    iterations = _get_pbkdf2_iterations()
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        f"{raw}{pepper}".encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def hash_api_key_lookup(raw: str) -> str:
    """Return a fast, deterministic PBKDF2 lookup digest for indexed API key fetches.

    Uses a single PBKDF2-HMAC-SHA256 iteration with the pepper as salt.  This is
    intentionally cheap to compute (unlike the full verification hash) so indexed
    lookups add negligible latency, while still being keyed with the application
    secret to prevent offline precomputation.
    """
    pepper = _get_api_key_pepper()
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), pepper.encode("utf-8"), 1)
    return dk.hex()


def verify_api_key_hash(raw: str, stored_hash: str) -> bool:
    """Verify a raw API key against supported PBKDF2 stored hash formats.

    Supported formats:
    - ``pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>`` (current)
    - ``pbkdf2_sha256$<iterations>$<digest_hex>`` (legacy PBKDF2 format)
    """
    try:
        if len(stored_hash) > 512:
            return False
        parts = stored_hash.split("$")
        if len(parts) == 4:
            algorithm, iterations_raw, salt_hex, expected_hex = parts
            if len(salt_hex) != _PBKDF2_SALT_BYTES * 2 or len(expected_hex) != _PBKDF2_DIGEST_BYTES * 2:
                return False
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(expected_hex)
            raw_bytes = f"{raw}{_get_api_key_pepper()}".encode("utf-8")
        elif len(parts) == 3:
            algorithm, iterations_raw, expected_hex = parts
            if len(expected_hex) != _PBKDF2_DIGEST_BYTES * 2:
                return False
            expected_digest = bytes.fromhex(expected_hex)
            salt = _get_api_key_pepper().encode("utf-8")
            raw_bytes = raw.encode("utf-8")
        else:
            return False

        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        if iterations < 1 or iterations > _MAX_PBKDF2_ITERATIONS:
            return False
    except (TypeError, ValueError):
        return False

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw_bytes,
        salt,
        iterations,
    )
    return secrets.compare_digest(dk, expected_digest)
