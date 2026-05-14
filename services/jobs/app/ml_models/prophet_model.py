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
from prophet import Prophet
from logger.logging_config import logger

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
    days: int = 30,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch observations, train Prophet model, and cache in Redis.
    
    Args:
        datastream_id: UUID of the datastream
        days: Days of historical data to fetch (default: 30)
        token: OAuth2 access token
        
    Returns:
        Dict with result status
    """
    logger.info("Training temperature model", extra={"datastream_id": datastream_id, "days": days})
    
    # Fetch observations
    observations = await _fetch_observations(datastream_id, days, token)
    
    if not observations:
        logger.warning("No observations found", extra={"datastream_id": datastream_id})
        return {"status": "error", "message": "No observations found"}
    
    # Prepare data
    df = _prepare_dataframe(observations)
    logger.info(
        "Data prepared",
        extra={"datastream_id": datastream_id, "samples": len(df)}
    )
    
    # Train
    model = _train_prophet(df)
    
    # Cache
    await _cache_model(datastream_id, model)
    
    logger.info("Model training complete", extra={"datastream_id": datastream_id})
    
    return {
        "status": "success",
        "datastream_id": datastream_id,
        "training_samples": len(df),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }


async def _fetch_observations(
    datastream_id: str,
    days: int,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch observations from API with pagination"""
    if not token:
        logger.info("Getting OAuth2 token")
        token = await _get_token()
    
    auth_headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Use API's time filter format: timestamp1/timestamp2
    time_filter = f"{start_date.isoformat()}/{now.isoformat()}"
    logger.info(
        "Fetching observations",
        extra={
            "datastream_id": datastream_id,
            "time_filter": time_filter,
            "days": days,
            "api_url": OBSERVATIONS_API_URL,
        }
    )
    
    all_obs = []
    offset = 0
    limit = 100
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                logger.debug("Fetching batch", extra={"offset": offset, "limit": limit})
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
                logger.debug("Response received", extra={"status_code": response.status_code})
                response.raise_for_status()
                data = response.json()
                
                # Handle both list and dict responses
                if isinstance(data, list):
                    obs = data
                else:
                    obs = data.get("items", [])
                if not obs:
                    logger.info("No more observations to fetch", extra={"total": len(all_obs)})
                    break
                
                all_obs.extend(obs)
                offset += limit
                
                logger.debug("Batch received", extra={"batch_count": len(obs), "total": len(all_obs)})
                
            except Exception as e:
                logger.exception(
                    "Failed to fetch observations",
                    extra={
                        "offset": offset,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                break
    
    logger.info("Observation fetch complete", extra={"total_fetched": len(all_obs)})
    
    # Log the actual fetched value range
    if all_obs:
        temps = [o.get("result_numeric") for o in all_obs if o.get("result_numeric") is not None]
        if temps:
            logger.info(
                f"Fetched observations: min {min(temps):.1f}° | max {max(temps):.1f}° | mean {sum(temps)/len(temps):.1f}° | count {len(temps)}"
            )
    
    return all_obs


def _prepare_dataframe(observations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert observations to Prophet format"""
    logger.info("Preparing dataframe for Prophet", extra={"observation_count": len(observations)})
    
    data = []
    
    for obs in observations:
        if obs.get("result_numeric") is None:
            continue
        
        data.append({
            "ds": pd.to_datetime(obs["result_time"]),
            "y": obs["result_numeric"],
        })
    
    logger.debug("Data records created", extra={"records": len(data)})
    
    df = pd.DataFrame(data).sort_values("ds").reset_index(drop=True)
    # Remove timezone for Prophet compatibility (Prophet requires naive UTC datetimes)
    df["ds"] = df["ds"].dt.tz_localize(None)
    df = df.drop_duplicates(subset=["ds"], keep="first")
    
    logger.info(
        f"DataFrame ready: {len(df)} rows | temp range {df['y'].min():.1f}°-{df['y'].max():.1f}° | mean {df['y'].mean():.1f}°"
    )
    
    return df


def _train_prophet(df: pd.DataFrame) -> Prophet:
    """Train Prophet model"""
    logger.info(
        "Starting Prophet training",
        extra={
            "samples": len(df),
            "date_range": f"{df['ds'].min()} to {df['ds'].max()}",
        }
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
    
    logger.debug("Prophet model created with parameters")
    model.fit(df)
    logger.info("Prophet model training complete")
    
    return model


async def _cache_model(datastream_id: str, model: Prophet) -> None:
    """Cache model and metadata in Redis"""
    logger.info("Caching model in Redis", extra={"datastream_id": datastream_id})
    
    model_key = f"weather_model:{datastream_id}"
    metadata_key = f"{datastream_id}:model_metadata"
    
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=False)
        serialized = pickle.dumps(model)
        ttl_seconds = 4 * 24 * 3600  # 4 days
        
        logger.debug("Serialized model", extra={"size_bytes": len(serialized)})
        
        # Cache the model
        await redis.setex(model_key, ttl_seconds, serialized)
        
        # Cache the metadata with trained_at timestamp
        metadata = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "datastream_id": datastream_id,
        }
        await redis.setex(metadata_key, ttl_seconds, json.dumps(metadata))
        
        await redis.close()
        
        logger.info(
            "Model and metadata cached successfully",
            extra={
                "model_key": model_key,
                "metadata_key": metadata_key,
                "size_bytes": len(serialized),
                "ttl_seconds": ttl_seconds,
            }
        )
    except Exception as e:
        logger.error("Failed to cache model", extra={"datastream_id": datastream_id, "error": str(e)})
        raise


async def _get_token() -> str:
    """Get OAuth2 token"""
    logger.debug("Requesting OAuth2 token", extra={"endpoint": API_TOKEN_URL})
    
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
        
        logger.debug("OAuth2 token obtained successfully")
        return token
