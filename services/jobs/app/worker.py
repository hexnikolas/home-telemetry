"""
Standalone background worker service

Usage:
    python -m app.worker
"""
import asyncio
import sys
from app.queue import job_queue
from app.handlers import (
    handle_sync_mqtt_topics_to_redis
)


async def main():
    print("=" * 50)
    print("Starting Background Worker Service")
    print("=" * 50)
    
    try:
        # Connect to Redis
        await job_queue.connect()
        
        # Register all job handlers
        job_queue.register_handler("sync_mqtt_topics_to_redis", handle_sync_mqtt_topics_to_redis)
        
        # Start worker loop (blocks indefinitely)
        await job_queue.process_jobs()
        
    except KeyboardInterrupt:
        print("\n[WORKER] Shutdown signal received")
    except Exception as e:
        print(f"[WORKER] Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        await job_queue.disconnect()
        print("[WORKER] Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
