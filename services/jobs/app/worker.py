"""
Standalone background worker service

Usage:
    python -m app.worker
"""
import asyncio
import sys
import os
from app.queue import job_queue
from app.handlers import (
    handle_sync_mqtt_topics_to_redis
)
from logger.logging_config import setup_logging_json, setup_logging_colored

# Initialize logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-jobs-worker", level=LOG_LEVEL)
else:
    logger = setup_logging_json("home-telemetry-jobs-worker", level=LOG_LEVEL)


async def main():
    logger.info("=" * 50)
    logger.info("Starting Background Worker Service")
    logger.info("=" * 50)
    
    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await job_queue.connect()
        logger.info("Connected to Redis")
        
        # Register all job handlers
        job_queue.register_handler("sync_mqtt_topics_to_redis", handle_sync_mqtt_topics_to_redis)
        logger.info("Registered job handlers", extra={"handlers": ["sync_mqtt_topics_to_redis"]})
        
        logger.info("Starting worker job processing loop...")
        
        # Start worker loop (blocks indefinitely)
        await job_queue.process_jobs()
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (KeyboardInterrupt)")
    except Exception as e:
        logger.error("Fatal error in worker", extra={"error": str(e)})
        sys.exit(1)
    finally:
        try:
            await job_queue.disconnect()
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error("Error disconnecting from Redis", extra={"error": str(e)})
        logger.info("Worker cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
