from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, OAuthFlowClientCredentials
from jose import JWTError
from app.auth.jwt import decode_access_token
from logger.logging_config import logger

# ---------------------------------------------------------------------------
# OAuth2 scheme — FastAPI uses this to:
#   1. Render the lock icon on every secured endpoint in Swagger UI
#   2. Show the "Authorize" button with client_credentials flow
#   3. Extract the Bearer token from the Authorization header
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2(
    flows=OAuthFlowsModel(
        clientCredentials=OAuthFlowClientCredentials(
            tokenUrl="/auth/token",
            scopes={},
        )
    )
)


async def _get_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate the Bearer token and return the JWT claims."""
    # The OAuth2 base class returns the raw Authorization header value,
    # which includes the 'Bearer ' prefix — strip it before decoding.
    if token and token.lower().startswith("bearer "):
        token = token[7:]
    logger.debug(f"Decoding token (first 20 chars): {repr(token[:20]) if token else 'EMPTY'}")
    try:
        payload = decode_access_token(token)
        logger.debug(f"Token decoded OK: sub={payload.get('sub')}, scopes={payload.get('scopes')}")
        return payload
    except JWTError as exc:
        logger.warning(f"JWT decode failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except RuntimeError as exc:
        logger.error(f"JWT runtime error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


def require_scope(scope: str):
    """Dependency factory.  Usage:
        @router.get("/", dependencies=[Depends(require_scope("systems:read"))])
    """
    async def _check(payload: dict = Depends(_get_payload)) -> dict:
        if scope not in payload.get("scopes", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scope — required: '{scope}'",
            )
        return payload

    return _check
