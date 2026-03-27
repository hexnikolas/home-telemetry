import os
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_TOKEN_EXPIRE_MINUTES", "15"))


def create_access_token(client_id: str, scopes: list[str]) -> str:
    """Sign and return a JWT for the given client and scopes."""
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": client_id,
        "scopes": scopes,
        "iat": now,
        "exp": now + TOKEN_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify signature and expiry, return the claims dict.
    Raises jose.JWTError on any validation failure."""
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
