"""
Standalone background worker service using arq

Usage:
    arq app.worker.WorkerSettings
"""
import os
from arq.connections import RedisSettings
from app.handlers import (
    handle_sync_mqtt_topics_to_redis,
    handle_fetch_open_meteo_data,
)
from app.scheduler import sync_mqtt_cron, fetch_meteo_cron
from logger.logging_config import setup_logging_json, setup_logging_colored

# Initialize logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-jobs-worker", level=LOG_LEVEL)
else:
    logger = setup_logging_json("home-telemetry-jobs-worker", level=LOG_LEVEL)


# Parse Redis URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
from urllib.parse import urlparse

parsed = urlparse(REDIS_URL)
redis_host = parsed.hostname or "localhost"
redis_port = parsed.port or 6379
redis_db = int(parsed.path.lstrip("/") or "0")
redis_password = parsed.password


class WorkerSettings:
    """arq worker configuration"""
    
    redis_settings = RedisSettings(
        host=redis_host,
        port=redis_port,
        database=redis_db,
        password=redis_password,
    )
    
    functions = [
        handle_sync_mqtt_topics_to_redis,
        handle_fetch_open_meteo_data,
    ]
    
    # Cron jobs for periodic tasks
    cron_jobs = [
        sync_mqtt_cron,
        fetch_meteo_cron,
    ]
    
    on_startup = None
    on_shutdown = None
    
    # Worker settings
    job_timeout = 600  # 10 minutes
    keep_result = 86400  # Keep results for 24 hours
    allow_abort_jobs = True
