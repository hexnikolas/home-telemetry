"""
Worker startup - initializes scheduler and loads tasks
This module is used as the entry point by Dramatiq: dramatiq app.worker
"""
import os
import sys
from logger.logging_config import setup_logging_json, setup_logging_colored

# Initialize logging FIRST
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-jobs-worker", level=LOG_LEVEL)
else:
    logger = setup_logging_json("home-telemetry-jobs-worker", level=LOG_LEVEL)

logger.info("Initializing Dramatiq worker with scheduler")

# Import broker FIRST (exposes it at module level for dramatiq)
from app.broker import broker  # noqa: F401, E402

# Import all tasks so they're registered with the broker
from app import tasks  # noqa: F401, E402

# Start the background scheduler
from app.scheduler import start_scheduler  # noqa: E402

scheduler = start_scheduler()

logger.info("Dramatiq worker ready - scheduler running")

