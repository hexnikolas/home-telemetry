# API Backend Guide

This directory contains the backend API service for home telemetry, built with [FastAPI](https://fastapi.tiangolo.com/).

## Overview

- **Framework:** FastAPI for high-performance async APIs
- **Routers:** Modular route definitions in `app/routers/` (e.g., datastreams, deployments, features_of_interest, observations, etc.)
- **Database:** Async database access via SQLAlchemy (see `app/database.py`)
- **CRUD Logic:** Encapsulated in `app/crud/` for each resource
- **MQTT Integration:** MQTT client in `app/mqtt/mqtt_client.py` for sensor data ingestion
- **Configuration:** Environment variables loaded from `.env`

## Usage

1. **Install Dependencies**
   
   Make sure you have [Poetry](https://python-poetry.org/) installed. Then, install the required dependencies:
   
   ```sh
   poetry install
   ```

2. **Run the API Server**
   
   Start the FastAPI server with Uvicorn:
   
   ```sh
   poetry run uvicorn app.main:app --host 0.0.0.0 --reload
   ```

   The API will be available at `http://localhost:8000` by default.

---

This backend is not yet dockerized. Adjust configuration and environment variables as needed for your setup.

For more details, see the code in the `app/` directory and explore the routers for available endpoints.