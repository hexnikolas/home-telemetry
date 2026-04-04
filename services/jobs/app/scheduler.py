"""
Cron jobs configuration for arq

The cron jobs defined here will be executed automatically by the worker
when running with arq scheduler support.

For development/standalone use, you can also invoke these directly:
    from arq.cron import cron
    from app.handlers import handle_sync_mqtt_topics_to_redis, handle_fetch_open_meteo_data
    from app.worker import WorkerSettings

    WorkerSettings.cron_jobs = [
        cron(handle_sync_mqtt_topics_to_redis, run_at_startup=True, minute=set(range(0, 60, 5))),  # Every 5 min
        cron(handle_fetch_open_meteo_data, run_at_startup=True, minute={0, 30}),  # Every 30 min
    ]
"""

from arq.cron import cron
from app.handlers import handle_sync_mqtt_topics_to_redis, handle_fetch_open_meteo_data

# Define cron jobs
# Sync MQTT topics every 5 minutes
sync_mqtt_cron = cron(
    handle_sync_mqtt_topics_to_redis,
    run_at_startup=True,
    minute=set(range(0, 60, 5)),  # Every 5 minutes: 0, 5, 10, 15, ...
)

# Fetch Open Meteo data every 30 minutes
fetch_meteo_cron = cron(
    handle_fetch_open_meteo_data,
    run_at_startup=True,
    minute={0, 30},  # At 0 and 30 minutes of each hour
)
