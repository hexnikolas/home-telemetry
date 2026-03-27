# API Backend Guide

This directory contains the backend API service for home telemetry, built with [FastAPI](https://fastapi.tiangolo.com/).

## Overview

The API implements a resource model closely aligned with the **OGC Connected Systems standard**, enabling sensor data management and observation collection.

- **Framework:** FastAPI for high-performance async APIs
- **Architecture:** RESTful + WebSocket support
- **Database:** Async SQLAlchemy ORM with PostgreSQL
- **Authentication:** OAuth2 Client Credentials flow with JWT tokens and scope-based authorization
- **Resources:** Systems, Procedures, Deployments, Features of Interest, Observed Properties, Datastreams, Observations
- **Real-time Subscriptions:** WebSocket endpoint to subscribe to datastreams and receive new observations

---

## Resources

The API manages the following core resources:

| Resource | Description |
|---|---|
| **Systems** | Physical or logical sensor systems (e.g., a weather station, an energy meter) |
| **Procedures** | Measurement procedures or algorithms used by systems |
| **Deployments** | Deployment configurations linking systems to locations and time periods |
| **Features of Interest** | Real-world objects being observed (e.g., a building, a room, a sensor location) |
| **Observed Properties** | Phenomena being measured (e.g., temperature, humidity, power consumption) |
| **Datastreams** | Time series streams linking a system, procedure, feature, and observed property |
| **Observations** | Individual sensor readings with timestamps and result values |

Each resource has REST endpoints for CRUD operations with full filtering and pagination support.

---

## Authentication & Authorization

All endpoints are protected with **OAuth2 Client Credentials** flow:

- **Token Endpoint:** `POST /auth/token`
- **Token Format:** JWT (HS256, 15-min default expiry)
- **Authorization:** Bearer token in `Authorization` header
- **Scopes:** Fine-grained (`systems:read/write`, `observations:write`, etc.)

Clients are registered with role-based scope sets (e.g., ingestion worker only has `observations:write`).


---

## Real-time Observations (WebSocket)

Subscribe to new observations on a datastream in real-time:

```
WS /api/v1/datastreams/ws/{datastream_id}
```

Any incoming observations for that datastream are pushed to all connected subscribers.

---

## Bulk Operations

- **Bulk Observations:** `POST /api/v1/observations/bulk` — Ingest multiple observations in a single request (used by ingestion workers)

---

## Rate Limiting

The API implements per-endpoint rate limiting to prevent abuse:

- **Default:** 100 requests per minute per client (configurable)
- **Enforcement:** Token-based (scoped to client credentials)
- **Response:** Returns `429 Too Many Requests` when limit exceeded

See `app/rate_limit.py` for configuration.

---

## Middleware & CORS

- **CORS:** Enabled for cross-origin requests (configurable allowed origins)
- **Request Logging:** All HTTP requests are logged with timestamp, method, path, and response status
- **Error Handling:** Standardized error responses with descriptive messages and HTTP status codes
- **Validation:** Pydantic-based request validation with detailed error feedback

---

## Error Handling & Validation

Request validation follows Pydantic schemas:

```python
# UUID validation, timezone handling, range checks, etc.
class ObservationWrite(BaseModel):
    datastream_id: UUID
    result_time: datetime
    result_numeric: float
```

Failed validation returns `422 Unprocessable Entity` with field-level error details.

Database errors and authorization failures return appropriate HTTP status codes (400, 401, 403, 404, 500, etc.).

---

## Docker Deployment

The API is containerized for easy deployment:


```bash
docker compose up
```

The container runs Uvicorn on port 8000 and expects a PostgreSQL database accessible via `DATABASE_URL`.

---

## Usage

1. **Install Dependencies**
   
   Make sure you have [Poetry](https://python-poetry.org/) installed. Then:
   
   ```sh
   poetry install
   ```

2. **Run the API Server**
   
   Start the FastAPI server with Uvicorn:
   
   ```sh
   poetry run uvicorn app.main:app --host 0.0.0.0 --reload
   ```

   The API will be available at `http://localhost:8000` by default.
   
   **Interactive Documentation:** Visit `http://localhost:8000/docs` (Swagger UI) for API browsing and testing.

---

## Configuration

Environment variables (see `.env` / `.env.template`):

- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET_KEY` — Secret for signing JWT tokens
- `JWT_TOKEN_EXPIRE_MINUTES` — Token TTL (default: 15)
- `CLIENT_SECRET_*_HASH` — bcrypt hashes of client secrets

---