from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.database import init_engine, init_db
from app.routers import systems, deployments, procedures, features_of_interest, observed_properties, datastreams, observations, admin
from app.rate_limit import limiter
from app.middlewares import CorrelationIdMiddleware, RequestLoggingMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from logger.logging_config import setup_logging_json
import os

# Initialize structured logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging_json("home-telemetry-api", level=LOG_LEVEL)

api_description = """
This API provides a standards-based framework for managing **observational data and metadata**.
It is inspired by the OGC SensorThings / O&M model and enables you to describe systems, deployments, procedures,
features of interest, observed properties, datastreams, and their resulting observations in a consistent way.

### Core Concepts
- **Systems**: Sensors, actuators, or composite platforms
- **Deployments**: When and where systems are deployed
- **Procedures**: Methods or workflows
- **Features of Interest**: The real-world phenomena being observed
- **Observed Properties**: The measurable characteristics (e.g., temperature)
- **Datastreams**: Continuous flow of observations
- **Observations**: Individual results with time, location, and value

### Purpose

This API is designed to:
- Provide a **structured way to manage metadata** about sensors, systems, deployments, and procedures.
- Enable linking of observations to their **procedural, spatial, and semantic context**.
- Facilitate **integration, interoperability, and discovery** of observational data in environmental,
  scientific, and IoT domains.

Together, these resources form a complete chain from **system → deployment → datastream → observation**,
allowing rich description, querying, and management of both **metadata** and **measurements**.
"""

tags_metadata = [
    {
        "name": "Systems",
        "description": (
            "Endpoints for managing **Systems**, which represent physical or virtual entities "
            "such as sensors, actuators, platforms, or composite systems. "
            "Systems can be standalone or composed of subsystems."
        ),
    },
    {
        "name": "Deployments",
        "description": (
            "Endpoints for managing **Deployments**, which describe when, where, and how "
            "systems are deployed. Deployments can be field, laboratory, mobile, fixed, "
            "temporary, permanent, virtual, or custom setups."
        ),
    },
    {
        "name": "Procedures",
        "description": (
            "Endpoints for managing **Procedures**, which define methods or workflows "
            "used by systems to collect, process, or act upon data. Examples include "
            "data collection, calibration, maintenance, startup/shutdown, or algorithm execution."
        ),
    },
    {
        "name": "FeaturesOfInterest",
        "description": (
            "Endpoints for managing **Features of Interest (FoI)**, which represent the real-world "
            "entities, areas, or phenomena being observed. These can include environmental, "
            "atmospheric, hydrospheric, lithospheric, biospheric, built, individual, population, "
            "object, or event features."
        ),
    },
    {
        "name": "ObservedProperties",
        "description": (
            "Endpoints for managing **Observed Properties**, which define the measurable phenomena "
            "or characteristics of a Feature of Interest. Each observed property specifies a unit "
            "of measure, value type, and optionally a domain, definition, or base property."
        ),
    },
    {
        "name": "Datastreams",
        "description": (
            "Endpoints for managing **Datastreams**, which link a System, Procedure, Observed Property, "
            "and optional Feature of Interest. A datastream represents a continuous series of observations "
            "with associated metadata such as validity period, result type, activity status, and location."
        ),
    },
    {
        "name": "Observations",
        "description": (
            "Endpoints for managing **Observations**, which are individual results produced by a datastream. "
            "Each observation records the result time, optional location, parameters, "
            "and the result value (JSON, numeric, text, or boolean)."
        ),
    }
]

#SEED_FILE = Path(__file__).parent / "observed_properties.json"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the API...", extra={"version": "0.1.0"})
    try:
        init_engine()  # creates engine from env vars
        logger.info("Database engine initialized")
        
        await init_db()
        logger.info("Database initialized and seeded if needed")

        from app.mqtt.mqtt_client import startup_mqtt, shutdown_mqtt
        startup_mqtt()
        logger.info("MQTT client started")
    except Exception as e:
        logger.error("Failed to start API", extra={"error": str(e)})
        raise

    yield

    try:
        shutdown_mqtt()
        logger.info("MQTT client shutdown")
    except Exception as e:
        logger.error("Error during MQTT shutdown", extra={"error": str(e)})
    
    logger.info("API shutdown complete")


app = FastAPI(
    title="Home Telemetry API",
    description=api_description,
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

# Add middleware (order matters - add in reverse order of execution)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(systems.router, prefix="/api/v1/systems", tags=["Systems"])
app.include_router(deployments.router, prefix="/api/v1/deployments", tags=["Deployments"])
app.include_router(procedures.router, prefix="/api/v1/procedures", tags=["Procedures"])
app.include_router(features_of_interest.router, prefix="/api/v1/features-of-interest", tags=["FeaturesOfInterest"])
app.include_router(observed_properties.router, prefix="/api/v1/observed-properties", tags=["ObservedProperties"])
app.include_router(datastreams.router, prefix="/api/v1/datastreams", tags=["Datastreams"])
app.include_router(observations.router, prefix="/api/v1/observations", tags=["Observations"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
def read_root():
    logger.debug("Root endpoint accessed")
    return {
        "Name": "Home Telemetry API",
        "Version": "0.1.0",
        "Created by": "Nikos Zacharatos",
        "About": "An API for managing systems, deployments, procedures, features of interest, observed properties, datastreams, and their observations — enabling the structured collection and retrieval of in-situ data.",
        "Contact": "nikos.zacharatos@protonmail.com",
        "License": "Apache 2.0",
        "Docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint."""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "home-telemetry-api",
        "version": "0.1.0"
    }
