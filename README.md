# Home Telemetry Project

Microservices home monitoring system. Sensor → MQTT → RabbitMQ → API → Observations → Alerts & Dashboards.

## Data Pipeline

```
Sensors (MQTT)
    ↓
RabbitMQ (message bridge)
    ↓
Ingestion Worker
    ├─ Route by topic (via Redis mapping)
    ├─ Handler per device model (SHT40, NOUS A1T, etc.)
    └─ POST to API
        ↓
    API (FastAPI)
        ├─ Store in TimescaleDB
        ├─ Publish to Redis Streams (datastream:{uuid})
        └─ WebSocket subscriptions
            ↓
    Notifier (subscribes Redis Streams)
        ├─ Evaluate rules (threshold, heartbeat)
        ├─ Check other services' health
        └─ Send alerts (Gotify, etc.)
    
    Grafana (queries TimescaleDB + OpenMeteo API)
        └─ Dashboards
    
    Jobs Service (background tasks)
        ├─ Sync MQTT topic config (every 5 min)
        ├─ Fetch weather data (every :00, :30)
        └─ Train ML models (every day)
```

## Key Features

- **OAuth2 Client Credentials** — All services authenticate via API tokens
- **Real-time Subscriptions** — WebSocket for live observation streams
- **Threshold Alerts** — Rules-based notifications when data exceeds limits
- **Heartbeat Monitoring** — Detects offline sensors
- **Time Series Forecasting** — Prophet models for temperature predictions
- **Data Model** — OGC-Connected Systems aligned (Systems, Procedures, Deployments, Features, Datastreams, Observations)

## Services

| Service | Role |
|---------|------|
| **API** | REST + WebSocket backend, OAuth2, data storage |
| **Ingestion** | MQTT consumer, batch observations to API |
| **Jobs** | Scheduled tasks (MQTT sync, weather, model training), retrain listener |
| **Notifier** | Rules engine, alert delivery |
| **TimescaleDB** | Time-series storage |
| **Redis** | Caching, message queue, real-time streams |
| **Grafana** | Dashboards |

## Getting Started

Refer to each service's README for setup and usage instructions:
- `services/api/README.md` — API backend
- `services/ingestion/README.md` — Data ingestion
- `services/jobs/README.md` — Background jobs
- `services/notifier/README.md` — Notifications
- `services/db/README.md` — Database containers
- `services/redis/README.md` — Redis cache and queue
- `services/grafana/README.md` — Grafana dashboards
