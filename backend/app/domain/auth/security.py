from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

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
    if str(settings.app_env).strip().lower() in {"development", "test"}:
        return "stockwire-default-api-key-pepper"
    raise RuntimeError("API_KEY_PEPPER must be set outside development/test environments")


def validate_api_key_pepper() -> None:
    """Call at application startup to fail fast if API_KEY_PEPPER is misconfigured."""
    _get_api_key_pepper()


_DEFAULT_PBKDF2_ITERATIONS = 310_000
_MIN_PBKDF2_ITERATIONS = 100_000


def _get_pbkdf2_iterations() -> int:
    raw = os.getenv("API_KEY_PBKDF2_ITERATIONS", str(_DEFAULT_PBKDF2_ITERATIONS))
    try:
        iterations = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_PBKDF2_ITERATIONS
    if iterations < _MIN_PBKDF2_ITERATIONS:
        return _DEFAULT_PBKDF2_ITERATIONS
    return iterations


def hash_api_key(raw: str) -> str:
    """Return versioned PBKDF2-HMAC-SHA256 hash string for API keys."""
    pepper = _get_api_key_pepper()
    iterations = _get_pbkdf2_iterations()
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw.encode("utf-8"),
        pepper.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${dk.hex()}"


def verify_pbkdf2_api_key_hash(raw: str, stored_hash: str) -> bool:
    """Verify a raw API key against a stored PBKDF2-HMAC-SHA256 versioned hash.

    The stored hash must be in the format ``pbkdf2_sha256$<iterations>$<hex>``.
    The iteration count is read from the stored hash, so verification remains
    correct even if ``API_KEY_PBKDF2_ITERATIONS`` has been changed since the
    key was created.
    """
    try:
        algorithm, iterations_raw, expected_hex = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        if iterations < 1:
            return False
    except (TypeError, ValueError):
        return False

    pepper = _get_api_key_pepper()
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw.encode("utf-8"),
        pepper.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(dk.hex(), expected_hex)
