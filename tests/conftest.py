import pytest
from httpx import AsyncClient, ASGITransport
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from app.models import Base
from app.database import init_engine
from app.main import app
from app.auth.jwt import create_access_token
from sqlalchemy import text

# ────────────────────────────────────────────────────────────────────────────────
# All scopes required by the API
# ────────────────────────────────────────────────────────────────────────────────
ALL_REQUIRED_SCOPES = [
    "systems:read",
    "systems:write",
    "deployments:read",
    "deployments:write",
    "procedures:read",
    "procedures:write",
    "observations:read",
    "observations:write",
    "datastreams:read",
    "datastreams:write",
    "properties:read",
    "properties:write",
]


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("timescale/timescaledb:latest-pg16") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(postgres_container):
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session", autouse=True)
def init_test_engine(db_url):
    init_engine(db_url, poolclass=NullPool)


@pytest.fixture(autouse=True)
async def setup_tables(db_url):
    engine = create_async_engine(db_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def valid_token():
    """Generate a JWT token with all required scopes for testing."""
    return create_access_token(client_id="test-client", scopes=ALL_REQUIRED_SCOPES)


@pytest.fixture(scope="session")
async def client(valid_token):
    """Create a test client with valid authentication token."""
    headers = {"Authorization": f"Bearer {valid_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac