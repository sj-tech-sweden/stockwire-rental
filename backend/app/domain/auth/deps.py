from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.models import User, APIKey
from app.domain.auth.security import decode_token, hash_api_key

# Make bearer optional so we can accept either JWT or API keys
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    # Try JWT first if present
    token = creds.credentials if creds else None
    if token:
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
            user = db.get(User, user_id)
            if user is None or not user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
            return user
        except (JWTError, KeyError, ValueError):
            # Fall through to API key handling
            pass

    # Fallback: check X-API-Key header or Authorization: Bearer <key>
    api_key_raw = request.headers.get("X-API-Key") or (token if token else None)
    if api_key_raw:
        pbkdf2_hash = hash_api_key(api_key_raw)
        ak = (
            db.query(APIKey)
            .filter(
                APIKey.is_active.is_(True),
                APIKey.is_admin.is_(True),
                APIKey.api_key_hash == pbkdf2_hash,
            )
            .first()
        )
        if ak and ak.is_admin:
            # Return sentinel admin user (id=0)
            return User(id=0, email=f"api-key:{ak.name}", password_hash="", full_name=ak.name, role="admin", is_active=True, is_admin=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials not provided")


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user


def require_editor(current_user: User = Depends(get_current_user)) -> User:
    if not current_user or current_user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor role required")
    return current_user
