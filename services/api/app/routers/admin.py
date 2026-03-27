from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import redis.asyncio as aioredis
import os
import json

from app.auth.dependencies import require_scope

router = APIRouter(prefix="/admin/jobs", tags=["Admin"])

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def get_redis():
    return await aioredis.from_url(REDIS_URL, decode_responses=True)

@router.get("/", dependencies=[Depends(require_scope("admin:read"))])
async def list_jobs(limit: int = 20):
    """List all enqueued and processed jobs from Redis"""
    redis = await get_redis()
    try:
        # Get all job IDs from the master queue
        job_ids = await redis.lrange("queue:all", 0, limit - 1)
        
        jobs = []
        for job_id in job_ids:
            job_data = await redis.hgetall(f"job:{job_id}")
            if job_data:
                # Parse JSON fields
                if "data" in job_data:
                    try:
                        job_data["data"] = json.loads(job_data["data"])
                    except: pass
                if "result" in job_data and job_data["result"]:
                    try:
                        job_data["result"] = json.loads(job_data["result"])
                    except: pass
                jobs.append(job_data)
        
        return {
            "total_enqueued": await redis.llen("queue:all"),
            "jobs": jobs
        }
    finally:
        await redis.close()

@router.get("/schedules", dependencies=[Depends(require_scope("admin:read"))])
async def list_schedules():
    """List all periodic job schedules"""
    redis = await get_redis()
    try:
        # Get all schedule keys from the sorted set
        schedule_keys = await redis.zrange("schedules", 0, -1)
        
        schedules = []
        for key in schedule_keys:
            data = await redis.hgetall(f"schedule:{key}")
            if data:
                if "data" in data:
                    try:
                        data["data"] = json.loads(data["data"])
                    except: pass
                # Add next run timestamp from the sorted set
                score = await redis.zscore("schedules", key)
                data["next_run_timestamp"] = score
                data["job_id"] = key  # 👈 add this
                schedules.append(data)
        
        return schedules
    finally:
        await redis.close()

@router.get("/{job_id}", dependencies=[Depends(require_scope("admin:read"))])
async def get_job_details(job_id: str):
    """Get detailed information about a specific job"""
    redis = await get_redis()
    try:
        job_data = await redis.hgetall(f"job:{job_id}")
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if "data" in job_data:
            try:
                job_data["data"] = json.loads(job_data["data"])
            except: pass
        if "result" in job_data and job_data["result"]:
            try:
                job_data["result"] = json.loads(job_data["result"])
            except: pass
            
        return job_data
    finally:
        await redis.close()

@router.delete("/schedules/{job_type}/{interval_minutes}", dependencies=[Depends(require_scope("admin:write"))])
async def delete_schedule(job_type: str, interval_minutes: int):
    """Delete a periodic job schedule"""
    redis = await get_redis()
    try:
        schedule_key = f"schedule:{job_type}:{interval_minutes}"
        
        # Remove from sorted set (the index)
        removed_from_set = await redis.zrem("schedules", schedule_key)
        
        # Remove the schedule data hash
        removed_data = await redis.delete(f"schedule:{schedule_key}")
        
        if not removed_from_set and not removed_data:
            raise HTTPException(status_code=404, detail="Schedule not found")
            
        return {"message": f"Successfully deleted schedule for {job_type} ({interval_minutes}min)"}
    finally:
        await redis.close()

@router.delete("/{job_id}", dependencies=[Depends(require_scope("admin:write"))])
async def delete_job(job_id: str):
    """Delete a job and its metadata from Redis"""
    redis = await get_redis()
    try:
        # Check if it exists
        if not await redis.exists(f"job:{job_id}"):
            raise HTTPException(status_code=404, detail="Job not found")

        # 1. Remove from 'queue:all' (the history)
        await redis.lrem("queue:all", 0, job_id)
        
        # 2. Try to remove from individual job type queues (if it was still pending)
        # Note: We don't know the job_type without reading it first, so we read the hash
        job_data = await redis.hgetall(f"job:{job_id}")
        if job_data and "job_type" in job_data:
            await redis.lrem(f"queue:{job_data['job_type']}", 0, job_id)

        # 3. Remove the hash data itself
        await redis.delete(f"job:{job_id}")
        
        # 4. Remove from completed set if it was there
        await redis.srem("jobs:completed", job_id)

        return {"message": f"Job {job_id} deleted"}
    finally:
        await redis.close()
