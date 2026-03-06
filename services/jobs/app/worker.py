"""
Standalone background worker service

Usage:
    python -m app.worker
"""
import asyncio
import sys
from app.queue import job_queue
from app.handlers import (
    handle_scrape_energy_prices,
    handle_process_observations,
    handle_send_alert
)


async def main():
    print("=" * 50)
    print("Starting Background Worker Service")
    print("=" * 50)
    
    try:
        # Connect to Redis
        await job_queue.connect()
        
        # Register all job handlers
        job_queue.register_handler("scrape_energy_prices", handle_scrape_energy_prices)
        job_queue.register_handler("process_observations", handle_process_observations)
        job_queue.register_handler("send_alert", handle_send_alert)
        
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
