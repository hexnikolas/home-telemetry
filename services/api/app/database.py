from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import AsyncGenerator

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

Base = declarative_base()

engine = None
AsyncSessionFactory = None


def init_engine(url: str = None, poolclass=None):
    global engine, AsyncSessionFactory
    if engine is not None:
        return

    if url is None:
        for name in ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASS']:
            if os.getenv(name) is None:
                raise RuntimeError(f"Environment variable '{name}' must be set")
        host = os.getenv('DATABASE_HOST')
        port = os.getenv('DATABASE_PORT')
        db_name = os.getenv('DATABASE_NAME')
        user = os.getenv('DATABASE_USER')
        pwd = os.getenv('DATABASE_PASS')
        url = f'postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db_name}'

    kwargs = dict(future=True, pool_pre_ping=True)

    if poolclass is not None:
        kwargs['poolclass'] = poolclass
    else:
        kwargs['pool_size'] = int(os.getenv("DB_POOL_SIZE", "10"))
        kwargs['max_overflow'] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        kwargs['pool_recycle'] = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    engine = create_async_engine(url, **kwargs)
    AsyncSessionFactory = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    from app import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)