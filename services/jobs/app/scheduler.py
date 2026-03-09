"""
Standalone scheduler service for periodic jobs

Usage:
    python -m app.scheduler
"""
import asyncio
import sys
import os
from app.queue import job_queue
from shared.logging_config import setup_logging_json

# Initialize logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging_json("home-telemetry-scheduler", level=LOG_LEVEL)


async def setup_schedules():
    """Set up all recurring schedules here"""
    logger.info("Setting up periodic job schedules")
    
    # Run immediately on startup
    await job_queue.enqueue("sync_mqtt_topics_to_redis", {})
    logger.info("Enqueued immediate sync_mqtt_topics_to_redis job")

    # Example: Scrape energy prices every 30 minutes
    await job_queue.schedule_periodic_job(
        job_type="sync_mqtt_topics_to_redis",
        data={},  # No additional data needed for this job
        interval_minutes=5
    )
    logger.info("Scheduled periodic sync_mqtt_topics_to_redis job", extra={"interval_minutes": 5})


async def main():
    logger.info("=" * 50)
    logger.info("Starting Scheduler Service")
    logger.info("=" * 50)
    
    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await job_queue.connect()
        logger.info("Connected to Redis")
        
        # Set up all periodic jobs
        await setup_schedules()
        
        logger.info("Starting scheduler loop...")
        # Start scheduler loop (blocks indefinitely)
        await job_queue.scheduler_loop()
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (KeyboardInterrupt)")
    except Exception as e:
        logger.error("Fatal error in scheduler", extra={"error": str(e)})
        sys.exit(1)
    finally:
        try:
            await job_queue.disconnect()
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error("Error disconnecting from Redis", extra={"error": str(e)})
        logger.info("Scheduler cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
