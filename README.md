# Home Telemetry Project

This repository contains a modular home telemetry system built with a microservices architecture.

## Overview

- **Microservices:**
  - Each service (API backend, MQTT broker, Grafana, database, etc.) runs independently and communicates via well-defined interfaces.
  - Services are organized in the `services/` directory.

- **Shared Schemas Module:**
  - Common Pydantic schemas for data validation and serialization are located in `shared/schemas/`.
  - These schemas are imported by multiple services to ensure consistent data models across the project.

- **Tests:**
  - Automated tests are provided in the `tests/` directory.

## Getting Started

Refer to each service's README for setup and usage instructions:
- `services/api/README.md` — API backend
- `services/mqtt_broker/README.md` — Mosquitto MQTT broker
- `services/grafana/README.md` — Grafana dashboards
- `services/db/README.md` — Database containers
