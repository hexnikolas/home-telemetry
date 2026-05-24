"""
Periodic task scheduler using APScheduler
Runs alongside the Dramatiq worker in the same process
"""
import os
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from logger.logging_config import logger
from app.tasks import sync_mqtt_topics_to_redis, fetch_open_meteo_data, train_temperature_model


def start_scheduler():
    """Initialize and start the APScheduler background scheduler"""
    logger.info("Starting APScheduler background scheduler")
    
    # Run startup jobs immediately
    logger.info("Enqueueing startup jobs")
    sync_mqtt_topics_to_redis.send()
    train_temperature_model.send()
    logger.info("Startup jobs enqueued")
    
    scheduler = BackgroundScheduler()
    
    # Schedule MQTT sync every 5 minutes
    scheduler.add_job(
        sync_mqtt_topics_to_redis.send,
        trigger=CronTrigger(minute="*/5"),
        id="sync_mqtt_topics",
        name="Sync MQTT topics to Redis",
        replace_existing=True,
    )
    logger.info("Added job: sync_mqtt_topics_to_redis (every 5 min)")
    
    # Schedule Open Meteo fetch at :00 and :30 every hour
    scheduler.add_job(
        fetch_open_meteo_data.send,
        trigger=CronTrigger(minute="0,30"),
        id="fetch_open_meteo",
        name="Fetch Open Meteo data",
        replace_existing=True,
    )
    logger.info("Added job: fetch_open_meteo_data (at :00 and :30)")
    
    # Schedule temperature model training on odd days at midnight UTC
    scheduler.add_job(
        train_temperature_model.send,
        trigger=CronTrigger(hour=0, minute=0, day="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31"),
        id="train_temperature",
        name="Train temperature model",
        replace_existing=True,
    )
    logger.info("Added job: train_temperature_model (odd days at 00:00 UTC)")
    
    scheduler.start()
    logger.info("Background scheduler STARTED - jobs are active")
    return scheduler


if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        import signal
        signal.pause()
    except KeyboardInterrupt:
        scheduler.shutdown()
