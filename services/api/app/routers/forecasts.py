from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from schemas.forecast_schemas import TemperatureForecast, ForecastPoint
from app.rate_limit import limiter
from app.auth.dependencies import require_scope
import os
import pickle
import redis.asyncio as aioredis
from datetime import datetime, timezone
import pandas as pd
from logger.logging_config import logger

router = APIRouter()


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
        
        # Generate forecast for next 12 hours at 30-minute intervals
        now = datetime.now(timezone.utc)
        future_periods = 24  # 24 x 30-minute intervals = 12 hours
        
        try:
            future_df = model.make_future_dataframe(periods=future_periods, freq="30min")
        except Exception as e:
            logger.warning("make_future_dataframe failed, attempting workaround", extra={"error": str(e)})
            # Fallback: create dataframe manually
            from pandas import date_range
            last_date = model.history["ds"].max()
            future_dates = date_range(start=last_date + pd.Timedelta(minutes=30), periods=future_periods, freq="30min")
            future_df = pd.DataFrame({"ds": future_dates})
        
        forecast = model.predict(future_df)
        
        # Extract only future predictions (skip historical data)
        future_forecast = forecast.tail(future_periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]].reset_index(drop=True)
        
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
