from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class ObservationBase(BaseModel):
    datastream_id: Optional[UUID4] = Field(None, description="The DataStream that this observation belongs to")
    result_time: datetime = Field(..., description="The time the result observation was obtained")
    result_complex: Optional[Dict[str, Any]] = Field(None, description="Complex result if applicable")
    result_numeric: Optional[float] = Field(None, description="Numeric result if applicable")
    result_text: Optional[str] = Field(None, description="Text result if applicable")
    result_boolean: Optional[bool] = Field(None, description="Boolean result if applicable")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters associated with the observation")


class ObservationWrite(ObservationBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the observation")


class ObservationRead(ObservationWrite):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-5678-9012-3456-789012345678",
                "datastream_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "result_time": "2026-02-28T12:00:00Z",
                "result_complex": None,
                "result_numeric": 23.5,
                "result_text": None,
                "result_boolean": None,
                "parameters": {"quality": "good"}
            }
        }
    )


class ObservationUpdate(BaseModel):
    datastream_id: Optional[UUID4] = None
    result_time: Optional[datetime] = None
    result_complex: Optional[Dict[str, Any]] = None
    result_numeric: Optional[float] = None
    result_text: Optional[str] = None
    result_boolean: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None
