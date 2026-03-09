# Structured Logging Guide

This project uses **Loguru** for structured, production-ready logging. All services emit JSON-formatted logs to stdout, making them suitable for log aggregation systems like Loki, ELK, Datadog, and Splunk.

## Quick Start

### Basic Usage

```python
from shared.logging_config import setup_logging, get_logger

# In your service startup
logger = setup_logging("my-service", level="INFO")

# Log messages
logger.info("Application started", extra={"version": "0.1.0"})
logger.error("Database connection failed", extra={"host": "db.example.com", "error": str(e)})
logger.debug("Processing request", extra={"user_id": "123", "action": "update"})
```

### In FastAPI Applications

The API service automatically initializes logging in `main.py`:

```python
from shared.logging_config import setup_logging_json, logger

# Already configured for you!
logger.info("Processing datastream", extra={"datastream_id": id, "count": 42})
```

### In Background Workers/Schedulers

```python
from shared.logging_config import setup_logging_json

logger = setup_logging_json("home-telemetry-worker", level=os.getenv("LOG_LEVEL", "INFO"))
logger.info("Job started", extra={"job_id": "abc123", "type": "sync"})
```

## Correlation IDs for Request Tracing

Correlation IDs allow you to trace a request across multiple services (API → DB → Cache → MQTT).

### Automatic in FastAPI

The `CorrelationIdMiddleware` automatically handles correlation IDs:

```bash
# Client sends request with correlation ID header
curl -H "X-Correlation-ID: abc123" http://localhost:8000/api/v1/systems/

# API logs all requests with this correlation ID
# Response includes the correlation ID
X-Correlation-ID: abc123
```

If no correlation ID is provided, one is automatically generated.

### Manual Context Management

```python
from shared.logging_config import log_context, set_correlation_id, set_user_id

# Set context for a block of code
with log_context(correlation_id="request-123", user_id="user456"):
    logger.info("Processing user request")
    # All logs in this block include correlation_id and user_id

# Or set individually
set_correlation_id("trace-789")
set_user_id("admin-001")
logger.info("Admin action")
```

## Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| `TRACE` | Very detailed debugging | Individual field values |
| `DEBUG` | Development and debugging | Function entry, variable inspection |
| `INFO` | Normal operations | Service startup, job completion |
| `WARNING` | Potentially problematic situations | Deprecated API usage, retry attempts |
| `ERROR` | Error events | Failed requests, exceptions |
| `CRITICAL` | Serious errors | Service crashes, data corruption |

### Set Log Level

```python
# Via environment variable (preferred)
export LOG_LEVEL=DEBUG

# Or in code
logger = setup_logging("my-service", level="DEBUG")
```

## JSON Output Structure

All logs are output as JSON for automation:

```json
{
  "timestamp": "2026-03-09T10:30:45.123456",
  "level": "INFO",
  "logger": "home_telemetry_api",
  "function": "read_observations",
  "line": 42,
  "message": "Retrieved observations",
  "correlation_id": "abc-123-def",
  "request_id": "req-456",
  "user_id": "user-789",
  "extra": {
    "count": 42,
    "datastream_id": "uuid-here",
    "duration_ms": 125.43
  }
}
```

## Adding Extra Fields

Always include context-specific information in the `extra` parameter:

```python
# Good - includes relevant business context
logger.info(
    "Observation created",
    extra={
        "datastream_id": datastream.id,
        "observation_id": obs.id,
        "value": obs.result_numeric,
        "duration_ms": time_taken
    }
)

# Avoid generic messages without context
logger.info("Done")  # Too vague!
```

## Common Logging Patterns

### Database Operations

```python
logger.info(
    "Database query executed",
    extra={
        "table": "observations",
        "operation": "SELECT",
        "rows_affected": count,
        "duration_ms": duration
    }
)
```

### MQTT Events

```python
logger.info(
    "MQTT message received",
    extra={
        "topic": "home/sensor/temperature",
        "payload_size": len(payload),
        "model": "SHT40"
    }
)
```

### HTTP Requests (Auto-logged by Middleware)

```
← 200 GET /api/v1/systems (45.23ms)
← 404 POST /api/v1/observations (12.50ms)
→ 500 GET /api/v1/deployments 
```

### Background Jobs

```python
logger.info(
    "Job started",
    extra={
        "job_id": job.id,
        "job_type": "sync_mqtt_topics",
        "retry_count": 0
    }
)

logger.error(
    "Job failed",
    extra={
        "job_id": job.id,
        "error": str(exception),
        "retry_count": 1,
        "next_retry_at": retry_time
    }
)
```

## Log Aggregation Integration

### Loki (Grafana)

Logs are JSON-formatted for easy parsing by Loki. Add this scrape config:

```yaml
scrape_configs:
  - job_name: home-telemetry
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
```

### ELK Stack (Elasticsearch)

JSON output is automatically parsed by Logstash:

```
{
  "timestamp": "...",
  "level": "INFO",
  "logger": "...",
  ...
}
```

### Datadog / Splunk

Include in environment:

```bash
export LOG_LEVEL=INFO
# Logs go to stdout in JSON format for agent ingestion
```

## Performance Notes

- **Async logging**: Loguru uses async file operations (non-blocking)
- **JSON serialization**: Slightly slower than plain text, but worth it for automation
- **Context variables**: Thread-safe and coroutine-safe (uses `contextvars`)
- **No file rotation in Docker**: Logs to stdout by design (container orchestrators handle rotation)

## Troubleshooting

### "No logs appearing"

1. Check `LOG_LEVEL` is not set too high:
   ```bash
   export LOG_LEVEL=INFO
   ```

2. Ensure logger is initialized:
   ```python
   logger = setup_logging("my-service")
   ```

3. Verify logs are going to stdout (not a file in Docker):
   ```python
   logger = setup_logging_json("service")  # Uses stderr/stdout
   ```

### "Logs not JSON formatted"

Use `setup_logging_json()` instead of `setup_logging()`:

```python
# Wrong
logger = setup_logging("service", json_output=False)

# Correct
logger = setup_logging_json("service")
```

### "Missing correlation IDs"

1. Ensure middleware is added to FastAPI app (done automatically in main.py)
2. Check headers are being sent:
   ```bash
   curl -H "X-Correlation-ID: test" http://localhost:8000/health
   ```

## Reference

### Available Functions

```python
from shared.logging_config import (
    setup_logging,              # Full control
    setup_logging_json,         # JSON output (production)
    setup_logging_colored,      # Colored output (development)
    get_correlation_id,         # Get current correlation ID
    set_correlation_id,         # Set correlation ID
    log_context,               # Context manager for scoped logging
    logger                     # Loguru logger instance
)
```

### Environment Variables

```bash
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL
```

---

**Questions?** Check service `main.py` files for examples of how logging is integrated.
