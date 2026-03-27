from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from app.auth.clients import authenticate_client
from app.auth.jwt import create_access_token, TOKEN_EXPIRE_MINUTES
from logger.logging_config import logger
import base64

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Request Access Token",
    description=(
        "OAuth2 **Client Credentials** grant (RFC 6749 §4.4).\n\n"
        "Exchange a `client_id` + `client_secret` for a short-lived signed JWT. "
        "Attach the token to all subsequent requests as:\n\n"
        "```\nAuthorization: Bearer <token>\n```\n\n"
        "The Swagger UI **Authorize** button handles this automatically."
    ),
)
async def request_token(request: Request) -> TokenResponse:
    try:
        form = await request.form()
    except Exception as exc:
        logger.error(f"Token endpoint: failed to parse form body: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must be application/x-www-form-urlencoded",
        )

    client_id: str = form.get("client_id", "")
    client_secret: str = form.get("client_secret", "")
    grant_type: str = form.get("grant_type", "client_credentials")
    scope: str = form.get("scope", "")

    # RFC 6749 §2.3.1 — credentials may alternatively arrive in the
    # Authorization: Basic base64(client_id:client_secret) header.
    # Swagger UI uses this method for the clientCredentials flow.
    if not client_id or not client_secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    logger.debug(
        f"Token request: client_id={repr(client_id)}, "
        f"grant_type={repr(grant_type)}, scope={repr(scope)}"
    )

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id and client_secret are required",
        )

    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grant_type must be 'client_credentials'",
        )

    client = authenticate_client(client_id, client_secret)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client_id or client_secret",
            headers={"WWW-Authenticate": "Bearer"},
        )

    allowed: set[str] = set(client["scopes"])
    requested: set[str] = set(scope.split()) if scope.strip() else allowed
    granted: list[str] = sorted(requested & allowed)

    access_token = create_access_token(client_id=client_id, scopes=granted)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRE_MINUTES * 60,
    )

