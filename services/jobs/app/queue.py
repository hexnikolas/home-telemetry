"""
Redis-based background job queue for async tasks and periodic jobs
"""
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any, Dict
import redis.asyncio as aioredis
import os
from logger.logging_config import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    def __init__(
        self,
        job_type: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        status: JobStatus = JobStatus.PENDING,
        created_at: Optional[datetime] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.job_type = job_type
        self.data = data
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.result = result
        self.error = error

    def to_dict(self) -> Dict:
        d = {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "data": json.dumps(self.data),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.result is not None:
            d["result"] = json.dumps(self.result)
        if self.error is not None:
            d["error"] = self.error
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Job":
        return cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            data=json.loads(data["data"]),
            status=JobStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            result=json.loads(data["result"]) if data.get("result") else None,
            error=data.get("error"),
        )


class JobQueue:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.job_handlers: Dict[str, Callable] = {}

    async def connect(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("[JOBS] Redis connection established")

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("[JOBS] Redis connection closed")

    async def reconnect(self):
        """Reconnect to Redis"""
        try:
            if self.redis:
                await self.redis.close()
        except Exception:
            pass
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler function for a job type"""
        self.job_handlers[job_type] = handler
        logger.info(f"[JOBS] Registered handler for job type: {job_type}")

    async def enqueue(self, job_type: str, data: Dict[str, Any]) -> Job:
        """Enqueue a new job"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        job = Job(job_type=job_type, data=data)
        
        # Store job metadata
        await self.redis.hset(
            f"job:{job.job_id}", 
            mapping=job.to_dict()
        )
        
        # Add to job queue
        await self.redis.lpush(f"queue:{job_type}", job.job_id)
        
        # Add to all jobs queue
        await self.redis.lpush("queue:all", job.job_id)
        
        logger.info(f"[JOBS] Enqueued job {job.job_id} of type {job_type}")
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job details by ID"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        job_data = await self.redis.hgetall(f"job:{job_id}")
        if not job_data:
            return None

        return Job.from_dict(job_data)

    async def process_jobs(self):
        """Main background worker loop - continuously processes jobs"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        logger.info("[JOBS] Worker started")
        
        while True:
            try:
                # Get next job from queue
                result = await self.redis.blpop(
                    list(f"queue:{jtype}" for jtype in self.job_handlers.keys()),
                    timeout=10
                )

                if not result:
                    continue

                job_type, job_id = result

                job = await self.get_job(job_id)
                if not job:
                    logger.info(f"[JOBS] Job {job_id} not found")
                    continue

                # Update status to running
                await self._update_job_status(job_id, JobStatus.RUNNING)
                logger.info(f"[JOBS] Processing {job.job_type} job {job_id}")

                # Get handler and execute
                handler = self.job_handlers.get(job.job_type)
                if not handler:
                    await self._update_job_status(
                        job_id,
                        JobStatus.FAILED,
                        error=f"No handler for job type: {job.job_type}"
                    )
                    continue

                try:
                    result = await handler(job.data)
                    await self._update_job_status(job_id, JobStatus.COMPLETED, result=result)
                    logger.info(f"[JOBS] Job {job_id} completed successfully")
                except Exception as e:
                    await self._update_job_status(
                        job_id,
                        JobStatus.FAILED,
                        error=str(e)
                    )
                    logger.info(f"[JOBS] Job {job_id} failed: {str(e)}")

            except asyncio.CancelledError:
                logger.info("[JOBS] Worker shutdown")
                break
            except Exception as e:
                logger.info(f"[JOBS] Worker error: {str(e)}")
                # Attempt reconnect
                logger.info("[JOBS] Attempting to reconnect to Redis...")
                await asyncio.sleep(10)
                try:
                    await self.reconnect()
                    logger.info("[JOBS] Reconnected to Redis successfully")
                except Exception as re:
                    logger.info(f"[JOBS] Reconnect failed: {str(re)}")
                    await asyncio.sleep(10)

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ):
        """Update job status and optional result/error"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        update_data = {"status": status.value}
        if result:
            update_data["result"] = json.dumps(result)
        if error:
            update_data["error"] = error

        await self.redis.hset(f"job:{job_id}", mapping=update_data)
        
        # Add to completed jobs set for cleanup
        if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
            await self.redis.sadd("jobs:completed", job_id)
            # Set expiry to 7 days
            await self.redis.expire(f"job:{job_id}", 7 * 24 * 3600)
            # Also ensure jobs:completed set doesn't grow forever (re-set TTL)
            await self.redis.expire("jobs:completed", 7 * 24 * 3600)

    async def schedule_periodic_job(
        self,
        job_type: str,
        data: Dict[str, Any],
        interval_minutes: int
    ):
        """Schedule a job to run periodically (interval in minutes)"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        # schedule_key = f"schedule:{job_type}:{interval_minutes}"
        schedule_key = f"{job_type}:{interval_minutes}"
        next_run = datetime.utcnow() + timedelta(minutes=interval_minutes)
        
        await self.redis.zadd(
            "schedules",
            {schedule_key: next_run.timestamp()}
        )
        await self.redis.hset(
            f"schedule:{schedule_key}",
            mapping={
                "job_type": job_type,
                "data": json.dumps(data),
                "interval_minutes": str(interval_minutes),
                "last_run": datetime.utcnow().isoformat(),
            }
        )
        # Set TTL on schedule (7 days) - will be updated each run
        await self.redis.expire(f"schedule:{schedule_key}", 7 * 24 * 3600)
        logger.info(f"[JOBS] Scheduled periodic job {job_type} every {interval_minutes} minutes")

    async def scheduler_loop(self):
        """Background loop to check and enqueue scheduled jobs"""
        if not self.redis:
            raise RuntimeError("Redis not connected")

        logger.info("[JOBS] Scheduler started")
        
        while True:
            try:
                now = datetime.utcnow().timestamp()
                
                # Get all schedules due for execution
                # due_schedules = await self.redis.zrangebyscore("schedules", 0, now)
                due_schedules = await self.redis.zrangebyscore("schedules", 0, now) or []

                for schedule_key in due_schedules:
                    logger.info(f"[JOBS] Found due schedule: {schedule_key}")
                    schedule_data = await self.redis.hgetall(f"schedule:{schedule_key}")
                    if schedule_data:
                        job_type = schedule_data["job_type"]
                        data = json.loads(schedule_data["data"])
                        interval = int(schedule_data["interval_minutes"])
                        
                        # Enqueue the job
                        await self.enqueue(job_type, data)
                        
                        # Reschedule for next interval
                        next_run = datetime.utcnow() + timedelta(minutes=interval)
                        await self.redis.zadd("schedules", {schedule_key: next_run.timestamp()})
                        
                        logger.info(f"[JOBS] Executed scheduled job {job_type}, next run in {interval} minutes")
                    if not schedule_data:
                        logger.info(f"[JOBS] Missing schedule data for {schedule_key}, skipping")
                        continue  # 👈 was already there but double-check the key matches exactly
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("[JOBS] Scheduler shutdown")
                break
            except Exception as e:
                logger.info(f"[JOBS] Scheduler error: {str(e)}")
                logger.info("[JOBS] Attempting to reconnect to Redis...")
                await asyncio.sleep(10)
                try:
                    await self.reconnect()
                    logger.info("[JOBS] Scheduler reconnected to Redis successfully")
                except Exception as re:
                    logger.info(f"[JOBS] Scheduler reconnect failed: {str(re)}")
                    await asyncio.sleep(10)


# Global job queue instance
job_queue = JobQueue()
