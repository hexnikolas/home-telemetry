# Loguru Structured Logging Implementation - Summary

## ✅ Implementation Complete

Your home-telemetry project now has production-ready structured logging with JSON output, correlation IDs, and request tracing. All services emit logs to stdout for log aggregation systems.

---

## What Was Implemented

### 1. **Shared Logging Module** (`shared/logging_config.py`)
   - Centralized logging configuration with Loguru
   - JSON output format for log aggregation (Loki, ELK, Datadog, Splunk)
   - Correlation ID and request ID management via context variables
   - `log_context()` context manager for scoped logging
   - `setup_logging_json()` for production (JSON output)
   - `setup_logging_colored()` for development (colored output)

### 2. **FastAPI Middleware** (`services/api/app/middlewares.py`)
   - `CorrelationIdMiddleware`: Extracts/generates correlation IDs from request headers
   - `RequestLoggingMiddleware`: Automatically logs all HTTP requests and responses with timings
   - Both middleware add correlation/request IDs to response headers

### 3. **Updated API Service** (`services/api/app/main.py`)
   - Initialize Loguru with `setup_logging_json()` on startup
   - Middleware registered (order matters - CorrelationId then RequestLogging)
   - Lifespan events now log startup/shutdown stages
   - New `/health` endpoint for health checks
   - Root endpoint logs debug info

### 4. **Updated Jobs Services**
   - **Scheduler** (`services/jobs/app/scheduler.py`): Logs all schedule setup and job enqueuing
   - **Worker** (`services/jobs/app/worker.py`): Logs job processing start/stop
   - **Handlers** (`services/jobs/app/handlers.py`): Detailed logging of batch operations and errors

### 5. **Updated MQTT Client** (`services/api/app/mqtt/mqtt_client.py`)
   - All `print()` statements replaced with structured logging
   - Logs for connection state, topic subscriptions, message handling
   - Error logging with context

### 6. **Dependency Updates**
   - Added `loguru>=0.7.2,<1.0.0` to:
     - `shared/pyproject.toml`
     - `services/api/pyproject.toml`
     - `services/jobs/pyproject.toml`

### 7. **Configuration Template** (`services/api/app/.env.template`)
   - `LOG_LEVEL` environment variable with examples
   - All other important env vars documented

### 8. **Documentation** (`shared/LOGGING.md`)
   - Complete logging guide with examples
   - JSON output structure
   - Log aggregation integration examples
   - Troubleshooting tips
   - Reference for all available functions

---

## Files Modified

| File | Changes |
|------|---------|
| `shared/logging_config.py` | **CREATED** - Logging configuration module |
| `shared/pyproject.toml` | Added `loguru` dependency |
| `shared/LOGGING.md` | **CREATED** - Complete logging documentation |
| `services/api/pyproject.toml` | Added `loguru` dependency |
| `services/api/app/.env.template` | **CREATED** - Environment variables template |
| `services/api/app/main.py` | Integrated logging, middleware, health endpoint |
| `services/api/app/middlewares.py` | **CREATED** - Request logging middleware |
| `services/api/app/mqtt/mqtt_client.py` | Replaced `print()` with structured logging |
| `services/jobs/pyproject.toml` | Added `loguru` and `shared` dependencies |
| `services/jobs/app/scheduler.py` | Structured logging for scheduler |
| `services/jobs/app/worker.py` | Structured logging for worker |
| `services/jobs/app/handlers.py` | Structured logging for job handlers |

---

## Key Features

### ✨ JSON Output
All logs are JSON-formatted with:
- Timestamp (ISO 8601)
- Log level (INFO, ERROR, etc.)
- Logger name and source location (function, line)
- Message
- Extra context fields
- Correlation/Request/User IDs (if available)
- Exception details (if applicable)

**Example:**
```json
{
  "timestamp": "2026-03-09T10:30:45.123456",
  "level": "INFO",
  "logger": "home_telemetry_api",
  "function": "read_observations",
  "line": 42,
  "message": "Retrieved observations",
  "correlation_id": "abc-123-def",
  "extra": {
    "count": 42,
    "datastream_id": "uuid-here"
  }
}
```

### 🔗 Correlation IDs
- Automatically extracted from `X-Correlation-ID` header
- Auto-generated UUID if not provided
- Returned in response headers
- Thread-safe context variable management
- Enables request tracing across services

### 📊 Automatic HTTP Logging
Every API request is logged with:
- HTTP method, path, status code
- Request/response times (milliseconds)
- Client IP address
- Query parameters

**Example Output:**
```
→ GET /api/v1/systems?limit=10
← 200 GET /api/v1/systems (45.23ms)
```

### 🎯 Structured Context
Pass `extra` dict to log additional context:
```python
logger.info(
    "Observation created",
    extra={
        "datastream_id": ds_id,
        "value": 23.5,
        "duration_ms": 125
    }
)
```

---

## Usage Quick Start

### In FastAPI API
```python
from shared.logging_config import logger

logger.info("Processing request", extra={"user_id": "123"})
logger.error("Database error", extra={"error": str(e)})
```

### In Background Jobs
```python
from shared.logging_config import setup_logging_json

logger = setup_logging_json("my-worker", level="INFO")
logger.info("Job started", extra={"job_id": "abc"})
```

### With Context
```python
from shared.logging_config import log_context

with log_context(correlation_id="req-123", user_id="user-456"):
    logger.info("Processing")  # Includes both IDs
```

---

## Environment Configuration

### Set Log Level
```bash
export LOG_LEVEL=DEBUG  # TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL
```

Default is `INFO`.

### For Docker
```dockerfile
ENV LOG_LEVEL=INFO
# Logs output to stdout (captured by Docker)
```

### For Production
```bash
export LOG_LEVEL=INFO
# OR in your orchestrator (K8s, Docker Compose)
```

---

## Integration with Log Aggregation

### Loki (Grafana)
Logs are automatically ready for Loki JSON parsing. Just query:
```
{service="home-telemetry-api"} | json
```

### ELK Stack
JSON output is automatically parsed by Logstash.

### Datadog / New Relic / Splunk
Send container stdout to your agent - logs are already JSON formatted.

---

## Production Checklist

- ✅ All services emit JSON logs to stdout
- ✅ Correlation IDs for request tracing
- ✅ Automatic HTTP request/response logging
- ✅ Error logging with full context
- ✅ Configurable log levels via `LOG_LEVEL` env var
- ✅ No file logging in containers (stdout only)
- ✅ Thread-safe and async-safe context management

---

## Testing the Setup

### 1. Check Logs Are JSON
```bash
# Start API
cd services/api
poetry install
poetry run uvicorn app.main:app --reload

# In another terminal
curl http://localhost:8000/health
# Check logs in the first terminal - should be JSON
```

### 2. Verify Correlation ID Tracing
```bash
# Send request with correlation ID
curl -H "X-Correlation-ID: test-123" http://localhost:8000/api/v1/systems/

# Logs should include: correlation_id: "test-123"
# Response headers should include: X-Correlation-ID: test-123
```

### 3. Check Log Levels
```bash
# Set to DEBUG
export LOG_LEVEL=DEBUG
poetry run uvicorn app.main:app

# Should see more detailed logs
```

---

## Next Steps (Optional Enhancements)

1. **Health Checks**: Add database/Redis/MQTT connectivity checks to `/health` endpoint
2. **Metrics**: Add Prometheus metrics endpoint for monitoring
3. **Error Tracking**: Send error logs to Sentry or similar
4. **Log Rotation**: If using file logs, configure rotation with Loguru
5. **Performance Monitoring**: Log slow queries/requests

---

## Documentation Reference

For detailed usage, examples, and troubleshooting, see:
- **[shared/LOGGING.md](../shared/LOGGING.md)** - Complete guide

---

**All syntax checks passed!** ✓ Your logging setup is ready for use.
