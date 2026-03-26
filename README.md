# Home Telemetry Project

This repository contains a modular home telemetry system built with a microservices architecture.

## Overview

- **Microservices:**
  - Each service (API, Ingestion, Grafana, database, etc.) runs independently and communicates via well-defined interfaces.
  - Services are organized in the `services/` directory.

- **Shared Schemas Module:**
  - Common Pydantic schemas for data validation and serialization are located in `shared/schemas/`.
  - These schemas are imported by multiple services to ensure consistent data models across the project.

- **Tests:**
  - Automated tests are provided in the `tests/` directory.

## Services

The following microservices make up the home telemetry system:

| Service | Description |
|---------|-------------|
| **API** | FastAPI backend providing RESTful endpoints for data management and system control |
| **Ingestion** | Data ingestion service for processing incoming telemetry data from various sources |
| **Jobs** | Background job queue service for handling asynchronous tasks and scheduled jobs |
| **Notifier** | Notification service for sending alerts and notifications via configured channels |
| **Database** | TimescaleDB for time-series data storage and pgAdmin for database management |
| **Redis** | In-memory cache and message queue for job processing and data caching |
| **Grafana** | Visualization and dashboarding platform for monitoring and analytics |

## Getting Started

Refer to each service's README for setup and usage instructions:
- `services/api/README.md` — API backend
- `services/ingestion/README.md` — Data ingestion
- `services/jobs/README.md` — Background jobs
- `services/notifier/README.md` — Notifications
- `services/db/README.md` — Database containers
- `services/redis/README.md` — Redis cache and queue
- `services/grafana/README.md` — Grafana dashboards
