from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import AsyncGenerator
from logger.logging_config import logger

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
    await seed_db()


async def seed_db() -> None:
    """Seeds the database with initial data from current_data.sql if tables are empty."""
    sql_file = Path(__file__).parent / "current_data.sql"
    if not sql_file.exists():
        return

    # Using the existing engine factory
    async with AsyncSessionFactory() as session:
        try:
            # Check if systems table has any entries
            # Using text() to avoid circular imports here
            result = await session.execute(text("SELECT 1 FROM public.systems LIMIT 1;"))
            if result.fetchone():
                return
        except Exception as e:
            # If table doesn't exist, we can't check. Proceed to seed.
            logger.info(f"Checking for existing data failed: {e}")

        logger.info(f"Seeding database with initial data from {sql_file}...")
        try:
            with open(sql_file, "r") as f:
                content = f.read()

            # Filter out psql meta-commands and SET statements that might fail and are not needed
            statements = [s.strip() for s in content.split(';') if s.strip()]
            for statement in statements:
                # Basic filter for non-SQL commands
                if (statement.startswith('\\\\') or 
                    statement.startswith('SET ') or 
                    statement.startswith('SELECT pg_catalog')):
                    continue
                await session.execute(text(statement + ";"))
            
            await session.commit()
            logger.info("Database seeding completed successfully.")
        except Exception as e:
            await session.rollback()
            logger.info(f"Error during seeding: {e}")
