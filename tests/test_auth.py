import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.main import app
from app.auth.jwt import create_access_token, JWT_SECRET_KEY, ALGORITHM

pytestmark = pytest.mark.asyncio

# ────────────────────────────────────────────────────────────────────────────────
# JWT Helpers for Auth Testing
# ────────────────────────────────────────────────────────────────────────────────
# Note: JWT_SECRET_KEY and ALGORITHM are imported directly from app.auth.jwt
# to ensure we use the exact same key/algorithm that the app uses


def create_expired_token() -> str:
    """Create a JWT token that has already expired."""
    now = int(datetime.now(timezone.utc).timestamp())
    # Expired 1 hour ago
    payload = {
        "sub": "test-client",
        "scopes": ["systems:read"],
        "iat": now - 7200,  # Issued 2 hours ago
        "exp": now - 3600,  # Expired 1 hour ago
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_token_with_scopes(scopes: list[str]) -> str:
    """Create a JWT token with specific scopes."""
    return create_access_token(client_id="test-client", scopes=scopes)


# ────────────────────────────────────────────────────────────────────────────────
# Auth Test Fixtures
# ────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def client_no_auth():
    """Test client without authentication header."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def client_invalid_token():
    """Test client with malformed/invalid token."""
    headers = {"Authorization": "Bearer invalid.token.here"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac


@pytest.fixture
async def client_expired_token():
    """Test client with an expired JWT token."""
    expired_token = create_expired_token()
    headers = {"Authorization": f"Bearer {expired_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac


@pytest.fixture
async def client_insufficient_scope():
    """Test client with valid token but limited scopes (no systems:write)."""
    limited_token = create_token_with_scopes(["systems:read", "observations:read"])
    headers = {"Authorization": f"Bearer {limited_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac


# ────────────────────────────────────────────────────────────────────────────────
# Auth Tests
# ────────────────────────────────────────────────────────────────────────────────

class TestAuthenticationRequired:
    """Test that endpoints require authentication."""

    async def test_no_token_returns_401(self, client_no_auth):
        """Missing Authorization header should return 401."""
        payload = {
            "name": "Test System",
            "system_type": "SENSOR",
            "external_id": "ext-123",
            "is_mobile": False,
            "is_gps_enabled": False,
            "serial_number": "SN-001",
        }
        response = await client_no_auth.post("/api/v1/systems/", json=payload)
        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, client_invalid_token):
        """Malformed JWT token should return 401."""
        payload = {
            "name": "Test System",
            "system_type": "SENSOR",
            "external_id": "ext-123",
            "is_mobile": False,
            "is_gps_enabled": False,
            "serial_number": "SN-001",
        }
        response = await client_invalid_token.post("/api/v1/systems/", json=payload)
        assert response.status_code == 401

    async def test_expired_token_returns_401(self, client_expired_token):
        """Expired JWT token should return 401."""
        payload = {
            "name": "Test System",
            "system_type": "SENSOR",
            "external_id": "ext-123",
            "is_mobile": False,
            "is_gps_enabled": False,
            "serial_number": "SN-001",
        }
        response = await client_expired_token.post("/api/v1/systems/", json=payload)
        assert response.status_code == 401


class TestScopeValidation:
    """Test that endpoints enforce scope validation."""

    async def test_insufficient_scope_returns_403(self, client_insufficient_scope):
        """Valid token without required scope should return 403."""
        payload = {
            "name": "Test System",
            "system_type": "SENSOR",
            "external_id": "ext-123",
            "is_mobile": False,
            "is_gps_enabled": False,
            "serial_number": "SN-001",
        }
        # Trying to POST (systems:write) with only read scope should fail
        response = await client_insufficient_scope.post("/api/v1/systems/", json=payload)
        assert response.status_code == 403

    async def test_read_with_insufficient_scope_returns_403(self, client_insufficient_scope):
        """Token without read scope for specific endpoint should return 403."""
        # This token has systems:read but not deployments:read
        # Try to access deployments
        response = await client_insufficient_scope.get("/api/v1/deployments/")
        assert response.status_code == 403


class TestValidTokenAllowsAccess:
    """Test that valid tokens with correct scopes allow access."""

    async def test_valid_token_with_read_scope_allows_get(self, client):
        """Valid token with correct scope should allow GET access."""
        response = await client.get("/api/v1/systems")
        # Should not be 401 or 403 (auth/scope error)
        assert response.status_code != 401
        assert response.status_code != 403
        # Will likely be 200 (empty list) or other success codes
        assert response.status_code < 500

    async def test_valid_token_with_write_scope_allows_post(self, client):
        """Valid token with correct scope should allow POST."""
        payload = {
            "name": "Test System",
            "system_type": "SENSOR",
            "external_id": "ext-123",
            "is_mobile": False,
            "is_gps_enabled": False,
            "serial_number": "SN-001",
        }
        response = await client.post("/api/v1/systems/", json=payload)
        # Should not be 401 or 403 (auth/scope error)
        assert response.status_code != 401
        assert response.status_code != 403
        # Should succeed with 201 or fail with validation error (422)
        assert response.status_code in [201, 422]


class TestMultipleAuthErrors:
    """Test interaction between multiple auth factors."""

    async def test_bearer_prefix_case_insensitive(self, valid_token):
        """Bearer token prefix should be case-insensitive."""
        # Test with lowercase bearer
        headers_lower = {"Authorization": f"bearer {valid_token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers_lower,
        ) as ac:
            response = await ac.get("/api/v1/systems/")
            assert response.status_code != 401
            assert response.status_code != 403

    async def test_missing_bearer_prefix_still_works(self, valid_token):
        """Token without Bearer prefix is still accepted by the decoder."""
        # The OAuth2 dependency accepts raw tokens without Bearer prefix
        # This is not a strict enforcement, just a convenience for testing
        headers = {"Authorization": valid_token}
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
        ) as ac:
            response = await ac.post(
                "/api/v1/systems",
                json={
                    "name": "Test System",
                    "system_type": "SENSOR",
                    "external_id": "ext-123",
                    "is_mobile": False,
                    "is_gps_enabled": False,
                    "serial_number": "SN-001",
                },
            )
            # Raw token without Bearer is accepted (201 created)
            assert response.status_code != 401
