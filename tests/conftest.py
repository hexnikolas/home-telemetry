import pytest
from httpx import AsyncClient, ASGITransport
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from app.models import Base
from app.database import init_engine
from app.main import app


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as pg:
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
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac