"""
Cron jobs configuration for arq

The cron jobs defined here will be executed automatically by the worker
when running with arq scheduler support.
"""

import os
import json
import redis.asyncio as aioredis
from arq.cron import cron
from app.handlers import handle_sync_mqtt_topics_to_redis, handle_fetch_open_meteo_data, handle_train_temperature_model
from logger.logging_config import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Define jobs once - handler and schedule
JOB_DEFINITIONS = {
    "sync_mqtt_topics_to_redis": {
        "handler": handle_sync_mqtt_topics_to_redis,
        "minute": set(range(0, 60, 5)),  # Every 5 minutes
        "run_at_startup": True,
    },
    "fetch_open_meteo_data": {
        "handler": handle_fetch_open_meteo_data,
        "minute": {0, 30},  # At 0 and 30 minutes
        "run_at_startup": False,
    },
    "train_temperature_model": {
        "handler": handle_train_temperature_model,
        "minute": {0},
        "hour": {0},
        "day": {1, 5, 9, 13, 17, 21, 25, 28},  # Every other day (odd days of month)
        "run_at_startup": True,
    }
}

# Generate cron jobs and schedules automatically
SCHEDULES = {}
cron_jobs = []

for job_name, config in JOB_DEFINITIONS.items():
    # Create SCHEDULES entry with sorted minute list
    minute_list = sorted(list(config["minute"]))
    handler_name = config["handler"].__name__
    run_at_startup = config.get("run_at_startup", False)
    
    schedule_dict = {
        "minute": json.dumps(minute_list),
        "handler": handler_name,
        "run_at_startup": str(run_at_startup),
    }
    if "hour" in config:
        schedule_dict["hour"] = json.dumps(sorted(list(config["hour"])))
    if "day" in config:
        schedule_dict["day"] = json.dumps(sorted(list(config["day"])))
    
    SCHEDULES[job_name] = schedule_dict
    
    # Create cron job - pass all cron parameters
    cron_kwargs = {
        "run_at_startup": run_at_startup,
        "minute": config["minute"],
    }
    if "hour" in config:
        cron_kwargs["hour"] = config["hour"]
    if "day" in config:
        cron_kwargs["day"] = config["day"]
    
    cron_job = cron(config["handler"], **cron_kwargs)
    cron_jobs.append(cron_job)

# Make individual cron references available
sync_mqtt_cron = cron_jobs[0]
fetch_meteo_cron = cron_jobs[1]
train_temp_cron = cron_jobs[2]


async def publish_schedules_to_redis():
    """Publish job schedules to Redis on worker startup"""
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        for job_name, schedule_info in SCHEDULES.items():
            await redis.hset(f"job:schedule:{job_name}", mapping=schedule_info)
        await redis.close()
    except Exception as e:
        logger.error(f"Failed to publish schedules to Redis: {e}")

