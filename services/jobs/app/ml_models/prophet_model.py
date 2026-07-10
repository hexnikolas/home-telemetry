"""
Prophet temperature model training and caching
"""
import pickle
import json
import os
import httpx
import redis.asyncio as aioredis
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import time
from prophet import Prophet
from logger.logging_config import logger

# Import protos from shared package
from protos import observations_pb2, observations_pb2_grpc


from grpc import aio as grpc_aio

# Configuration
API_URL = os.getenv("API_URL", "http://api:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OBSERVATIONS_API_URL = f"{API_URL}/api/v1/observations/"

# Auth
API_CLIENT_ID = os.getenv("API_CLIENT_ID", "")
API_CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "")
_api_base = API_URL.split("/api/")[0] if "/api/" in API_URL else API_URL
API_TOKEN_URL = f"{_api_base}/auth/token"


async def train_and_cache_model(
    datastream_id: str,
    days: int = 80,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch observations, train Prophet model, and cache in Redis.

    Args:
        datastream_id: UUID of the datastream
        days: Days of historical data to fetch (default: 30)
        token: OAuth2 access token (used only for REST fallback)

    Returns:
        Dict with result status
    """
    logger.info(f"Training temperature model - datastream: {datastream_id}, days: {days}")

    # Fetch observations
    start_time = time.time()
    try:
        observations = await _fetch_observations_grpc(datastream_id, days)
    except Exception as grpc_error:
        logger.warning(
            f"gRPC observation fetch failed, falling back to REST: {grpc_error}"
        )
        observations = await _fetch_observations(datastream_id, days, token)
    fetch_duration = time.time() - start_time

    if not observations:
        logger.warning(f"No observations found for {datastream_id}")
        return {"status": "error", "message": "No observations found"}

    # Prepare data
    start_time = time.time()
    df = _prepare_dataframe(observations)
    prepare_duration = time.time() - start_time
    logger.info(f"Data prepared: {len(df)} samples in {prepare_duration:.2f}s")

    # Train
    start_time = time.time()
    model = _train_prophet(df)
    train_duration = time.time() - start_time

    # Cache
    start_time = time.time()
    await _cache_model(datastream_id, model)
    cache_duration = time.time() - start_time

    total_duration = fetch_duration + prepare_duration + train_duration + cache_duration
    logger.info(
        f"Model training complete - "
        f"fetch: {fetch_duration:.2f}s, "
        f"prepare: {prepare_duration:.2f}s, "
        f"train: {train_duration:.2f}s, "
        f"cache: {cache_duration:.2f}s, "
        f"total: {total_duration:.2f}s"
    )

    return {
        "status": "success",
        "datastream_id": datastream_id,
        "training_samples": len(df),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "fetch_duration_seconds": fetch_duration,
        "total_duration_seconds": total_duration,
    }


async def _fetch_observations(
    datastream_id: str,
    days: int,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch observations from REST API with pagination."""
    if not token:
        logger.info("Getting OAuth2 token")
        token = await _get_token()

    auth_headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Use API's time filter format: timestamp1/timestamp2
    time_filter = f"{start_date.isoformat()}/{now.isoformat()}"
    logger.info(f"Fetching observations for {datastream_id} - {days} days")

    all_obs = []
    offset = 0
    limit = 100
    fetch_start_time = time.time()
    batch_times = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                batch_start = time.time()
                response = await client.get(
                    OBSERVATIONS_API_URL,
                    params={
                        "datastream_ids": datastream_id,
                        "time": time_filter,
                        "limit": limit,
                        "offset": offset,
                        "ordering": "result_time",
                    },
                    headers=auth_headers,
                )
                batch_duration = time.time() - batch_start
                batch_times.append(batch_duration)
                response.raise_for_status()
                data = response.json()

                # Handle both list and dict responses
                if isinstance(data, list):
                    obs = data
                else:
                    obs = data.get("items", [])
                if not obs:
                    break

                all_obs.extend(obs)
                offset += limit
                logger.debug(f"Batch {len(batch_times)}: {len(obs)} obs, total {len(all_obs)} - {batch_duration:.2f}s")

            except Exception as e:
                logger.error(f"Failed to fetch observations: {e}")
                break

    total_fetch_time = time.time() - fetch_start_time
    avg_batch_time = sum(batch_times) / len(batch_times) if batch_times else 0
    logger.info(
        f"Fetch complete: {len(all_obs)} observations in {total_fetch_time:.2f}s "
        f"({len(batch_times)} batches, avg {avg_batch_time:.2f}s/batch)"
    )

    # Log the actual fetched value range
    if all_obs:
        temps = [o.get("result_numeric") for o in all_obs if o.get("result_numeric") is not None]
        if temps:
            logger.info(
                f"Temperature range: {min(temps):.1f}° - {max(temps):.1f}° (mean: {sum(temps)/len(temps):.1f}°)"
            )

    return all_obs


async def _fetch_observations_grpc(
    datastream_id: str,
    days: int,
) -> List[Dict[str, Any]]:
    """Fetch observations from gRPC service"""
    grpc_host = os.getenv("GRPC_HOST", "api")
    grpc_port = os.getenv("GRPC_PORT", "50051")
    grpc_addr = f"{grpc_host}:{grpc_port}"

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    logger.info(f"Fetching observations via gRPC for {datastream_id} - {days} days from {grpc_addr}")

    all_obs = []
    fetch_start_time = time.time()

    try:
        async with grpc_aio.insecure_channel(grpc_addr) as channel:
            stub = observations_pb2_grpc.ObservationServiceStub(channel)
            request = observations_pb2.GetObservationsRequest(
                datastream_id=datastream_id,
                time_start=start_date.isoformat(),
                time_end=now.isoformat(),
                limit=10000,  # High limit to fetch all observations
            )

            count = 0
            async for obs in stub.GetObservations(request):
                # count += 1
                all_obs.append({
                    "id": obs.id,
                    "datastream_id": obs.datastream_id,
                    "result_time": obs.result_time,
                    "result_numeric": obs.result_numeric if obs.result_numeric != 0.0 else None,
                    "result_text": obs.result_text if obs.result_text else None,
                    "result_boolean": obs.result_boolean if obs.result_boolean else None,
                    "result_complex": obs.result_complex if obs.result_complex else None,
                    "parameters": dict(obs.parameters) if obs.parameters else None,
                })
                # if count % 100 == 0:
                #     logger.debug(f"Streamed {count} observations")

    except Exception as e:
        logger.error(f"gRPC fetch failed: {e}")
        raise

    total_fetch_time = time.time() - fetch_start_time
    logger.info(
        f"gRPC fetch complete: {len(all_obs)} observations in {total_fetch_time:.2f}s "
        f"(streaming)"
    )

    # Log the actual fetched value range
    if all_obs:
        temps = [o.get("result_numeric") for o in all_obs if o.get("result_numeric") is not None]
        if temps:
            logger.info(
                f"Temperature range: {min(temps):.1f}° - {max(temps):.1f}° (mean: {sum(temps)/len(temps):.1f}°)"
            )

    return all_obs


def _prepare_dataframe(observations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert observations to Prophet format"""
    logger.info(f"Preparing dataframe - {len(observations)} observations")

    data = []

    for obs in observations:
        if obs.get("result_numeric") is None:
            continue

        data.append({
            "ds": pd.to_datetime(obs["result_time"]),
            "y": obs["result_numeric"],
        })

    df = pd.DataFrame(data).sort_values("ds").reset_index(drop=True)
    # Remove timezone for Prophet compatibility (Prophet requires naive UTC datetimes)
    df["ds"] = df["ds"].dt.tz_localize(None)
    df = df.drop_duplicates(subset=["ds"], keep="first")

    logger.info(
        f"DataFrame ready: {len(df)} rows, "
        f"temp range {df['y'].min():.1f}° - {df['y'].max():.1f}°, "
        f"mean {df['y'].mean():.1f}°"
    )

    return df


def _train_prophet(df: pd.DataFrame) -> Prophet:
    """Train Prophet model"""
    logger.info(
        f"Starting Prophet training - {len(df)} samples, "
        f"date range {df['ds'].min()} to {df['ds'].max()}"
    )

    model = Prophet(
        interval_width=0.95,
        yearly_seasonality=False,  # Not enough data (only 30 days) for yearly seasonality
        weekly_seasonality=False,  # Not enough data (only ~4 weeks) for reliable weekly patterns
        daily_seasonality=True,    # Daily cycles are strong in temperature data
        seasonality_mode="multiplicative",  # Better for percentage variations in temperature
        seasonality_prior_scale=5.0,  # Reduce seasonality strength to avoid overshooting
        changepoint_prior_scale=0.01,  # Reduce trend sensitivity to noise
    )

    model.fit(df)
    logger.info("Prophet model training complete")

    return model


async def _cache_model(datastream_id: str, model: Prophet) -> None:
    """Cache model and metadata in Redis"""
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=False)
        serialized = pickle.dumps(model)
        ttl_seconds = 4 * 24 * 3600  # 4 days

        # Cache the model
        await redis.setex(f"weather_model:{datastream_id}", ttl_seconds, serialized)

        # Cache the metadata with trained_at timestamp
        metadata = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "datastream_id": datastream_id,
        }
        await redis.setex(f"{datastream_id}:model_metadata", ttl_seconds, json.dumps(metadata))

        await redis.close()

        logger.info(
            f"Model cached in Redis - {len(serialized)} bytes, TTL 4 days"
        )
    except Exception as e:
        logger.error(f"Failed to cache model: {e}")
        raise


async def _get_token() -> str:
    """Get OAuth2 token"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            API_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": API_CLIENT_ID,
                "client_secret": API_CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        token = response.json()["access_token"]

        logger.debug("OAuth2 token obtained")
        return token


async def compare_fetch_methods(datastream_id: str, days: int = 50) -> None:
    """Compare REST vs gRPC performance for fetching observations"""
    logger.info(f"Comparing REST vs gRPC for {datastream_id} - {days} days")

    # Test REST
    token = await _get_token()
    rest_start = time.time()
    rest_obs = await _fetch_observations(datastream_id, days, token)
    rest_duration = time.time() - rest_start

    # Test gRPC
    grpc_start = time.time()
    grpc_obs = await _fetch_observations_grpc(datastream_id, days)
    grpc_duration = time.time() - grpc_start

    logger.info(f"=== COMPARISON ===")
    logger.info(f"REST:  {rest_duration:.2f}s for {len(rest_obs)} observations")
    logger.info(f"gRPC:  {grpc_duration:.2f}s for {len(grpc_obs)} observations")
    logger.info(f"Speed improvement: {rest_duration/grpc_duration:.1f}x faster with gRPC")
    logger.info(f"Time saved per training: {rest_duration - grpc_duration:.2f}s")
