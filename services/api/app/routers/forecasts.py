from fastapi import APIRouter, Depends, Request, Header, status
from fastapi import HTTPException
from schemas.forecast_schemas import TemperatureForecast, ForecastPoint
from app.rate_limit import limiter
from app.auth.dependencies import require_scope
import os
import pickle
import redis.asyncio as aioredis
from datetime import datetime, timezone, timedelta
import pandas as pd
from logger.logging_config import logger
from pydantic import BaseModel
import json

router = APIRouter()


class ModelInfo(BaseModel):
    """Information about the trained model"""
    model_exists: bool
    training_data_end: datetime | None = None
    model_age_seconds: int | None = None
    model_age_hours: float | None = None
    message: str


# @router.get("/outside-temp", response_model=TemperatureForecast, summary="Get 12-hour Temperature Forecast", dependencies=[Depends(require_scope("observations:read"))])
@router.get("/outside-temp/public", response_model=TemperatureForecast, summary="Get 12-hour Temperature Forecast (Public)")
async def get_temperature_forecast(request: Request) -> TemperatureForecast:
    """
    Get 12-hour temperature forecast for outside temperature datastream.
    
    Uses the cached Prophet model trained on 30 days of historical data.
    Returns forecasts at 30-minute intervals with 95% confidence intervals.
    """
    datastream_id = os.getenv("OUTSIDE_TEMP_DATASTREAM_ID")
    if not datastream_id:
        raise HTTPException(status_code=500, detail="Outside temperature datastream not configured")
    
    try:
        # Retrieve model from Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis = await aioredis.from_url(redis_url, decode_responses=False)
        model_key = f"weather_model:{datastream_id}"
        model_bytes = await redis.get(model_key)
        await redis.close()
        
        if not model_bytes:
            raise HTTPException(status_code=404, detail="Forecast model not trained yet. Check back later.")
        
        # Unpickle the model
        model = pickle.loads(model_bytes)
        
        # Generate forecast for next 12 hours at 30-minute intervals from now
        now = datetime.now(timezone.utc)
        now_pd = pd.Timestamp(now).tz_localize(None)  # Remove timezone for Prophet
        future_periods = 24  # 24 x 30-minute intervals = 12 hours
        
        # Create dataframe with timestamps from now to now + 12 hours at 30-minute intervals
        from pandas import date_range
        future_dates = date_range(start=now_pd, periods=future_periods, freq="30min")
        future_df = pd.DataFrame({"ds": future_dates})
        
        forecast = model.predict(future_df)
        
        # Extract forecast predictions
        future_forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].reset_index(drop=True)
        
        logger.info(
            f"Forecast generated: min {future_forecast['yhat'].min():.1f}° | max {future_forecast['yhat'].max():.1f}° | "
            f"mean {future_forecast['yhat'].mean():.1f}° | start {future_forecast['yhat'].iloc[0]:.1f}° → end {future_forecast['yhat'].iloc[-1]:.1f}°"
        )
        
        # Build response
        forecast_points = []
        for _, row in future_forecast.iterrows():
            forecast_points.append(
                ForecastPoint(
                    timestamp=pd.Timestamp(row["ds"]).to_pydatetime().replace(tzinfo=timezone.utc),
                    forecast=float(row["yhat"]),
                    lower_bound=float(row["yhat_lower"]),
                    upper_bound=float(row["yhat_upper"]),
                )
            )
        
        return TemperatureForecast(
            datastream_id=datastream_id,
            forecast_generated_at=now,
            forecast_points=forecast_points,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Forecast generation failed", extra={"error": str(e), "error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")


@router.get("/model-info", response_model=ModelInfo, summary="Get Forecast Model Age")
async def get_model_info(request: Request) -> ModelInfo:
    """
    Get information about the trained forecast model.
    
    Returns the age of the model based on when it was actually trained.
    """
    datastream_id = os.getenv("OUTSIDE_TEMP_DATASTREAM_ID")
    if not datastream_id:
        raise HTTPException(status_code=500, detail="Outside temperature datastream not configured")
    
    try:
        # Retrieve metadata from Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis = await aioredis.from_url(redis_url, decode_responses=True)
        
        metadata_key = f"{datastream_id}:model_metadata"
        metadata_str = await redis.get(metadata_key)
        
        await redis.close()
        
        if not metadata_str:
            return ModelInfo(
                model_exists=False,
                message="Forecast model not trained yet. Check back later."
            )
        
        # Parse metadata
        metadata = json.loads(metadata_str)
        trained_at_str = metadata.get("trained_at")
        
        if not trained_at_str:
            return ModelInfo(
                model_exists=False,
                message="Model metadata incomplete. Check back later."
            )
        
        # Use actual training time
        trained_at = datetime.fromisoformat(trained_at_str)
        
        # Calculate model age
        now = datetime.now(timezone.utc)
        age = now - trained_at
        age_seconds = int(age.total_seconds())
        age_hours = age.total_seconds() / 3600
        
        return ModelInfo(
            model_exists=True,
            training_data_end=trained_at,
            model_age_seconds=age_seconds,
            model_age_hours=round(age_hours, 2),
            message=f"Model trained at {trained_at.isoformat()}"
        )
    
    except Exception as e:
        logger.exception("Failed to get model info", extra={"error": str(e), "error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


# Redis constants
RETRAIN_IN_PROGRESS_KEY = "model:retrain:in_progress"
MODEL_METADATA_KEY = lambda ds_id: f"{ds_id}:model_metadata"
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "")


async def validate_service_api_key(x_api_key: str = Header(None)) -> str:
    """Validate the service API key from X-API-Key header"""
    if not x_api_key:
        logger.warning("Missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    
    if not SERVICE_API_KEY:
        logger.error("SERVICE_API_KEY environment variable not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service not properly configured",
        )
    
    if x_api_key != SERVICE_API_KEY:
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return x_api_key


@router.post("/model/retrain", summary="Trigger Temperature Model Retrain", dependencies=[Depends(validate_service_api_key)])
async def retrain_temperature_model() -> dict:
    """
    Trigger retraining of the temperature Prophet model.
    
    Validates that:
    - Model is at least 1 hour old
    - No retrain is already in progress
    
    If valid, enqueues a retrain job and sets an in-progress flag.
    
    Returns:
        - 200: Retrain job enqueued successfully
        - 400: Model is too young (< 1 hour old)
        - 409: Retrain already in progress
        - 500: Server error
    """
    datastream_id = os.getenv("OUTSIDE_TEMP_DATASTREAM_ID")
    
    if not datastream_id:
        logger.error("OUTSIDE_TEMP_DATASTREAM_ID not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service not properly configured",
        )
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    
    try:
        # 1. Check if retrain is already in progress
        in_progress = await redis.get(RETRAIN_IN_PROGRESS_KEY)
        if in_progress:
            logger.warning(
                "Retrain already in progress",
                extra={"datastream_id": datastream_id}
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Model retrain already in progress",
            )
        
        # 2. Check model age from Redis metadata
        model_metadata_key = MODEL_METADATA_KEY(datastream_id)
        model_data = await redis.get(model_metadata_key)
        
        if model_data:
            try:
                metadata = json.loads(model_data)
                trained_at_str = metadata.get("trained_at")
                
                if trained_at_str:
                    trained_at = datetime.fromisoformat(trained_at_str)
                    model_age = datetime.now(timezone.utc) - trained_at
                    
                    if model_age < timedelta(hours=1):
                        logger.warning(
                            "Model too young to retrain",
                            extra={
                                "datastream_id": datastream_id,
                                "model_age_minutes": int(model_age.total_seconds() / 60),
                            }
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Model is only {int(model_age.total_seconds() / 60)} minutes old. Cannot retrain before 1 hour.",
                        )
                    
                    logger.info(
                        "Model age check passed",
                        extra={
                            "datastream_id": datastream_id,
                            "model_age_hours": round(model_age.total_seconds() / 3600, 2),
                        }
                    )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Failed to parse model metadata",
                    extra={"error": str(e), "datastream_id": datastream_id}
                )
        else:
            logger.info("No existing model metadata found, proceeding with retrain")
        
        # 3. Publish to RabbitMQ queue for jobs worker to process
        import aio_pika
        
        rabbitmq_url = os.getenv("RABBITMQ_URL")
        if not rabbitmq_url:
            logger.error("RABBITMQ_URL environment variable not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service not properly configured",
            )
        connection = await aio_pika.connect(rabbitmq_url)
        channel = await connection.channel()
        
        # Declare the queue (will be created if it doesn't exist)
        queue_name = "model.retrain"
        queue = await channel.declare_queue(queue_name, durable=True)
        
        # Publish the retrain message
        message_body = json.dumps({
            "requested_at": datetime.now(timezone.utc).isoformat(),
        })
        
        message = aio_pika.Message(
            body=message_body.encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        
        await channel.default_exchange.publish(message, routing_key=queue_name)
        await connection.close()
        
        logger.info(
            "Retrain message published to RabbitMQ",
            extra={
                "datastream_id": datastream_id,
                "queue": queue_name
            }
        )
        
        return {
            "status": "success",
            "message": "Model retrain message enqueued",
            "datastream_id": datastream_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to enqueue retrain job",
            extra={"datastream_id": datastream_id, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue retrain job",
        )
    finally:
        await redis.close()
