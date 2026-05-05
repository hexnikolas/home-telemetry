from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import uuid
from jose import jwt
import os

INTERNAL_CLIENTS = {"jobs-worker", "ingestion-worker", "notifier"}

def get_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header[7:]
            payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY", ""), algorithms=["HS256"])
            client_id = payload.get("sub")
            if client_id in INTERNAL_CLIENTS:
                return f"exempt:{uuid.uuid4()}"
            return f"client:{client_id}"
        except:
            pass
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_rate_limit_key)