from pydantic import BaseModel
from datetime import datetime
from typing import List


class ForecastPoint(BaseModel):
    """A single forecast data point"""
    timestamp: datetime
    forecast: float
    lower_bound: float
    upper_bound: float


class TemperatureForecast(BaseModel):
    """12-hour temperature forecast"""
    datastream_id: str
    forecast_generated_at: datetime
    forecast_points: List[ForecastPoint]
    
    class Config:
        json_schema_extra = {
            "example": {
                "datastream_id": "28363ed0-b8c2-4262-b2e4-acc48333be7c",
                "forecast_generated_at": "2026-05-05T18:00:00Z",
                "forecast_points": [
                    {
                        "timestamp": "2026-05-05T18:30:00Z",
                        "forecast": 25.3,
                        "lower_bound": 24.1,
                        "upper_bound": 26.5
                    }
                ]
            }
        }
