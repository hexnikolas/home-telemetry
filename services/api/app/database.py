from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import AsyncGenerator

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Helper function to require env variables
def get_env_var(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Environment variable '{name}' must be set in your .env file")
    return value

# Required environment variables
database_host = get_env_var('DATABASE_HOST')
database_port = get_env_var('DATABASE_PORT')
database_name = get_env_var('DATABASE_NAME')
database_user = get_env_var('DATABASE_USER')
database_pass = get_env_var('DATABASE_PASS')

# Use postgresql+asyncpg instead of postgresql
SQLALCHEMY_DATABASE_URL = (
    f'postgresql+asyncpg://{database_user}:{database_pass}@{database_host}:{database_port}/{database_name}'
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    future=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
)

AsyncSessionFactory = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Create Base here
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()