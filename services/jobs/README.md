# Background Job Queue Service

Standalone service for processing background jobs from Redis queue with periodic scheduling support.

## Architecture

```
FastAPI (API Service)           Job Service
      │                              │
      ├─ Enqueue job via Redis ──────┤
      │                              │
      │                   ┌─────────────────┐
      │                   │ Redis Queue     │
      │                   ├─────────────────┤
      │                   │ job:uuid        │
      │                   │ queue:type      │
      │                   │ schedules       │
      │                   └─────────────────┘
      │                              ↑
      │              ┌───────────────┼───────────────┐
      │              │               │               │
      │         ┌─────────┐   ┌──────────┐   ┌──────────┐
      │         │ Worker1 │   │ Worker2  │   │Scheduler │
      │         └─────────┘   └──────────┘   └──────────┘
      │              │               │               │
      └──────────────┼───────────────┼───────────────┘
                     │               │
                 GET /jobs/status/id │
              returns result/status  │
```

## Quick Start (Local Development with Poetry)

### Prerequisites
- Python 3.10+
- Redis running on localhost:6379
- API service running (it will create jobs in Redis)

### 1. Install dependencies with Poetry
```bash
poetry install
```

### 2. Start Redis (separate terminal)
```bash
redis-server
```

### 3. Start Worker (process jobs)
```bash
poetry run python -m app.worker
```

### 4. Start Scheduler (periodic jobs) - optional Terminal
```bash
poetry run python -m app.scheduler
```

## Running with Docker Compose

From the `jobs/` directory:

```bash
docker-compose up
```

This starts:
- Redis
- Jobs Worker
- Jobs Scheduler
- Database (TimescaleDB)
- MQTT Broker

## Running without Docker (Fastest for Testing)

Ideal for rapid development and testing:

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Worker:**
```bash
cd services/jobs
poetry install
poetry run python -m app.worker
```

**Terminal 3 - Scheduler (optional):**
```bash
cd services/jobs
poetry run python -m app.scheduler
```

Then from your API service, enqueue jobs via REST API and they'll be processed immediately!

## Adding New Jobs

### 1. Create handler in `app/handlers.py`
```python
async def handle_my_job(data: Dict[str, Any]) -> Dict:
    print(f"Processing: {data}")
    # Your logic here
    return {"result": "success"}
```

### 2. Register in both worker and scheduler

`app/worker.py`:
```python
job_queue.register_handler("my_job", handle_my_job)
```

`app/scheduler.py`:
```python
job_queue.register_handler("my_job", handle_my_job)
```

### 3. Optional: Add periodic scheduling in `app/scheduler.py`
```python
async def setup_schedules():
    await job_queue.schedule_periodic_job(
        job_type="my_job",
        data={"key": "value"},
        interval_minutes=30
    )
```

### 4. Enqueue from API
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/enqueue" \
  -H "Content-Type: application/json" \
  -d '{"job_type": "my_job", "data": {"key": "value"}}'
```

Returns:
```json
{
  "job_id": "abc123...",
  "job_type": "my_job",
  "status": "pending",
  "created_at": "2024-03-06T12:00:00"
}
```

### 5. Check status from API
```bash
curl "http://localhost:8000/api/v1/jobs/status/abc123/"
```

## Environment Variables

- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)

## Scaling

### Multiple Workers (for parallelism)
```bash
# Terminal 2
poetry run python -m app.worker

# Terminal 3 (another worker)
poetry run python -m app.worker

# Terminal 4 (another worker)
poetry run python -m app.worker
```

Or in Docker:
```yaml
jobs-worker:
  deploy:
    replicas: 3  # 3 parallel workers
```

### Single Scheduler (important!)
Always run exactly **1 scheduler instance** to prevent duplicate scheduling.

## Job Lifecycle

```
1. API enqueues job
   └─ Stored in Redis as job:uuid
   └─ Added to queue:job_type

2. Worker polls from queue:job_type
   └─ Updates status to RUNNING

3. Worker executes handler
   └─ On success: status = COMPLETED, stores result
   └─ On failure: status = FAILED, stores error

4. Job expires after 7 days (auto-cleanup)
```

## Monitoring

### Watch worker logs (local)
```bash
poetry run python -m app.worker  # Shows all job processing
```

### Check Redis queue directly
```bash
redis-cli
> KEYS queue:*
> LLEN queue:scrape_energy_prices
> HGETALL job:abc123
```

### Check job status via API
```bash
curl "http://localhost:8000/api/v1/jobs/status/{job_id}"
```

## Testing

Run tests with pytest:
```bash
poetry run pytest
```

## Poetry Commands

```bash
# Install dependencies
poetry install

# Add a new dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Run a command in venv
poetry run python script.py

# Activate venv
poetry shell
```
