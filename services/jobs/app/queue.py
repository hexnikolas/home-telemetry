"""
ARQ-based background job queue for async tasks and periodic jobs
"""
import os
from arq import create_pool
from arq.connections import RedisSettings
from logger.logging_config import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def get_redis_settings() -> RedisSettings:
    """Parse Redis URL and return RedisSettings for arq"""
    # Parse Redis URL (e.g., "redis://localhost:6379/0")
    from urllib.parse import urlparse
    
    parsed = urlparse(REDIS_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = int(parsed.path.lstrip("/") or "0")
    password = parsed.password
    
    return RedisSettings(
        host=host,
        port=port,
        database=db,
        password=password,
    )


async def get_redis_pool():
    """Create and return arq Redis pool"""
    settings = get_redis_settings()
    return await create_pool(settings)


# arq will be configured in worker.py and scheduler.py
logger.info("[JOBS] arq job queue initialized")
