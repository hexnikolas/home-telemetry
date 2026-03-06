"""
Standalone scheduler service for periodic jobs

Usage:
    python -m app.scheduler
"""
import asyncio
import sys
from app.queue import job_queue


async def setup_schedules():
    """Set up all recurring schedules here"""
    
    # Example: Scrape energy prices every 30 minutes
    await job_queue.schedule_periodic_job(
        job_type="scrape_energy_prices",
        data={"source_url": "https://example.com/prices"},
        interval_minutes=1
    )
    
    # Add more scheduled jobs as needed:
    # await job_queue.schedule_periodic_job(
    #     job_type="process_observations",
    #     data={"datastream_id": "some-uuid"},
    #     interval_minutes=60
    # )


async def main():
    print("=" * 50)
    print("Starting Scheduler Service")
    print("=" * 50)
    
    try:
        # Connect to Redis
        await job_queue.connect()
        
        # Set up all periodic jobs
        await setup_schedules()
        
        # Start scheduler loop (blocks indefinitely)
        await job_queue.scheduler_loop()
        
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Shutdown signal received")
    except Exception as e:
        print(f"[SCHEDULER] Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        await job_queue.disconnect()
        print("[SCHEDULER] Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
