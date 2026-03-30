# Ingestion Service Guide

This directory contains the **Observations Ingestion Worker** — a background service that consumes sensor data from MQTT via RabbitMQ, processes it through model-specific handlers, and publishes observations to the telemetry API.

## Architecture Overview

```
Sensors (MQTT)
    ↓
RabbitMQ (Message Queue)
    ↓
Ingestion Worker
    ├→ Topic/Model Lookup (Redis)
    ├→ Handler (SHT40, A1T, etc.)
    ├→ TokenManager (Auth)
    └→ API (POST /observations/bulk)
```

The worker:
1. Connects to RabbitMQ and consumes MQTT-to-AMQP bridged messages
2. Routes each message to a model-specific handler
3. Transforms raw sensor data into `ObservationWrite` objects
4. Batches observations and sends them to the API with OAuth2 authentication
5. Acknowledges/NACKs messages based on API response

---

## Components

### RabbitMQ Integration

- **Queue Name:** `observations_queue`
- **Message Format:** Routing key with MQTT path (dots as separators)
  ```
  Routing Key: tele.NOUS_A1T_4E4984.SENSOR
  Body (JSON): {"Time": "2026-03-28T10:15:00", "ENERGY": {"Power": 100.5, ...}}
  ```
- **Connection:** Async via `aio-pika`
- **Config:** `RABBITMQ_URL`, `RABBITMQ_EXCHANGE`, `RABBITMQ_ROUTING_KEY`

See `app/queue.py` for queue management and batching logic.

### Ingestion Worker (`app/worker.py`)

The main application that:

1. **Connects to Redis** — loads topic-to-datastream mappings cached by the jobs sync job
2. **Fetches API auth token** — bootstraps OAuth2 credentials on startup
3. **Consumes RabbitMQ messages** — batches by configurable size/timeout
4. **Routes to handlers** — converts MQTT topic → model → handler
5. **Sends to API** — `POST /api/v1/observations/bulk` with exponential backoff retry
6. **Acknowledges on success** — removes messages from queue

**Configuration:**
- `BATCH_SIZE` — max observations per bulk request (default: 100)
- `BATCH_TIMEOUT` — seconds to wait before flushing a partial batch (default: 5)
- `API_MAX_RETRIES` — retry attempts on API failure (default: 5)
- `BASE_DELAY` — exponential backoff base delay in seconds (default: 5)

### Handlers (`app/handlers.py`)

Model-specific functions that transform raw MQTT payloads into observations:

| Handler | Sensor Model | Payload Path | Extracts |
|---|---|---|---|
| `handle_sensor_SHT40` | SHT40 (Temp/Humidity) | `data["SHT4X"]` | Temperature, Humidity, DewPoint |
| `handle_sensor_A1T` | NOUS A1T (Energy Meter) | `data["ENERGY"]` | Power, Voltage, Total |

Each handler:
- Accepts `(data: dict, datastreams: Dict[str, str])` — the `datastreams` dict is `{"Temperature": "uuid", ...}` from Redis
- Parses the `Time` field (ISO format, CET) and converts to UTC
- Yields `ObservationWrite` objects for each measured property
- Silently skips properties with no configured datastream

**Adding a new sensor type:**
1. Create a handler function accepting `(data, datastreams)`
2. Register it in `MODEL_HANDLERS` dict
3. Add `mqtt_key` to each datastream's `properties` on the API
4. The jobs sync job picks up the new datastreams automatically

### Redis Integration

The worker reads **topic configurations** written by the jobs sync job:

```
HGETALL mqtt:topic_config
→ {
    "tele/NOUS_A1T_4E4984/SENSOR": '{"model": "A1T", "datastreams": {"Power": "uuid-a", "Voltage": "uuid-b", "Total": "uuid-c"}}',
    "tele/SHT40_SENSOR_01/SENSOR": '{"model": "SHT40", "datastreams": {"Temperature": "uuid-x", "Humidity": "uuid-y", ...}}'
  }
```

The `datastreams` dict within each config is keyed by `mqtt_key` (the field name in the MQTT payload) and values are datastream UUIDs. This allows handlers to work with any number of sensors of the same model.

---

## Authentication

The worker authenticates to the API using **OAuth2 Client Credentials**:

- **Token Endpoint:** `POST {API_BASE_URL}/auth/token`
- **Token Format:** JWT (HS256, 15-min expiry by default)
- **Token Manager:** In-memory cache with auto-refresh 60 seconds before expiry
- **Scope:** `observations:write` (required for bulk POST)

**Configuration:**
- `API_CLIENT_ID` — default: `ingestion-worker`
- `API_CLIENT_SECRET` — plaintext secret (match the bcrypt hash on API)

Credentials must exist in the API's client registry (`services/api/app/auth/clients.py`).

---

## Message Reliability & Dead Letter Queue (DLQ)

The ingestion worker implements a robust retry and failure handling mechanism:

### Retry Logic

1. **API-Level Retries:** Each batch of observations is retried up to `API_MAX_RETRIES` times (default: 5) with exponential backoff if the API request fails
2. **Message-Level Retries:** If a batch fails after all API retries, each message is tracked with a retry counter in RabbitMQ headers

### Dead Letter Queue

When a message fails processing after `MAX_MESSAGE_RETRIES` attempts (default: 3), it's moved to the **Dead Letter Queue** (`observations.dlq`) for manual inspection and recovery.

**Message Flow:**
```
Message received (retry_count = 0)
    ↓
Processing fails → republish with retry_count = 1
    ↓
Processing fails → republish with retry_count = 2
    ↓
Processing fails → republish with retry_count = 3
    ↓
Max retries exceeded → move to observations.dlq
```

**DLQ Messages Include:**
- `x-retry-count` — Number of retry attempts
- `x-failed-at` — Timestamp of final failure
- `x-original-routing-key` — Original MQTT topic

### Managing the DLQ

View messages in the DLQ:
```bash
python view_dlq.py --count 20
```

Purge the DLQ:
```bash
python view_dlq.py --purge
```

**Configuration:**
- `MAX_MESSAGE_RETRIES` — Message-level retries before DLQ (default: 3)
- `API_MAX_RETRIES` — API request retries per batch (default: 5)
- `BASE_DELAY` — Initial retry delay in seconds for exponential backoff (default: 5)

---

## Architecture Decisions

- **Batch Processing:** Observations are accumulated and sent in bulk (not one-by-one) for efficiency and reduced API load
- **Redis Caching:** Topic configs are fetched once on startup, reducing API calls during steady-state message processing
- **Token Refresh:** JWT tokens are cached in-memory and auto-refreshed 60s before expiry to minimize token endpoint calls
- **Message Acknowledgment:** Only acknowledged after successful API ingestion (or after max retries) — provides delivery guarantees

---

