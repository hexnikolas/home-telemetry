# Jobs Service - Dramatiq

Background job processing service using Dramatiq with Redis broker for the home-telemetry platform.

## Features

- **Open Meteo Weather Data**: Fetches weather data every 30 minutes at :00 and :30
- **Automatic Retry**: Failed jobs automatically retry up to 10 times with 5-minute intervals
- **Result Time Preservation**: Original timestamp is maintained across all retries, preventing data gaps
- **MQTT Topic Syncing**: Synchronizes sensor configurations every 5 minutes
- **Temperature Model Training**: Trains Prophet models for temperature forecasting
- **Lightweight**: Uses Dramatiq for minimal overhead

## Architecture

- **Broker**: Redis-backed Dramatiq broker
- **Tasks**: Asynchronous job tasks with retry policies
- **Scheduler**: APScheduler for periodic task execution
- **Worker**: Multi-process Dramatiq worker (4 processes by default)

## Configuration

Set these environment variables in `.env`:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `API_URL`: Home Telemetry API URL (default: `http://localhost:8000`)
- `API_CLIENT_ID`: OAuth2 client ID
- `API_CLIENT_SECRET`: OAuth2 client secret
- `OPEN_METEO_LATITUDE`: Weather station latitude (default: `37.7749`)
- `OPEN_METEO_LONGITUDE`: Weather station longitude (default: `-122.4194`)
- `OUTSIDE_TEMP_DATASTREAM_ID`: Datastream ID for temperature model training
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `LOG_FORMAT`: Logging format - `json` or `colored` (default: `json`)

## Running Locally

```bash
# Install dependencies
poetry install

# Run worker with scheduler
dramatiq app.worker -p 4 -t 4
```

## Docker

```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f jobs-worker

# Stop
docker-compose down
```

## Scheduled Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| sync_mqtt_topics_to_redis | Every 5 minutes | Sync MQTT topic configuration |
| fetch_open_meteo_data | :00 and :30 each hour | Fetch weather data with auto-retry |
| train_temperature_model | Odd days at 00:00 UTC | Train temperature forecast model |

## Retry Strategy

The `fetch_open_meteo_data` task implements intelligent retry:
- **Trigger**: On any failure (network, API errors, etc.)
- **Retry Count**: Up to 10 attempts
- **Interval**: Exactly 5 minutes between retries
- **Timestamp**: Original measurement time is preserved across all retries
- **Outcome**: If it fails at :00 but succeeds at :05, the observation is recorded with :00 timestamp

This ensures no data gaps in your dataset even during transient API failures.

## Migration from ARQ

This service replaces the previous ARQ-based jobs service. The old service is backed up in `jobs_arq/`.

### Key Differences

| Aspect | ARQ | Dramatiq |
|--------|-----|----------|
| Retry Support | Limited | First-class with policies |
| Retry Timing | Complex workarounds | Built-in `@retry` decorator |
| Task Serialization | Function references | Robust message queue |
| Periodic Tasks | Built-in cron | APScheduler integration |
| Memory Footprint | ~15-17% | ~15-17% (similar) |

