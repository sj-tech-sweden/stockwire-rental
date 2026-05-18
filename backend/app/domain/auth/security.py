from datetime import datetime, timedelta, timezone
import hashlib

from jose import jwt
import bcrypt

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
