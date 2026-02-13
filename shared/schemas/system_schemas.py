from pydantic import BaseModel, UUID4,  HttpUrl, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from uuid import UUID

class SystemTypes(str, Enum):
    SENSOR = "SENSOR"    
    ACTUATOR = "ACTUATOR"
    PLATFORM = "PLATFORM"
    SYSTEM = "SYSTEM"    
    CUSTOM = "CUSTOM" 

class SystemBase(BaseModel):
    name: str = Field(..., description="Human readable name")
    description: Optional[str] = Field(None, description="Human readable description")
    system_type: SystemTypes = Field(..., description="The type of system")
    external_id: Optional[str] = Field(None, description="External reference ID (e.g., MQTT ID)")
    is_mobile: Optional[bool] = Field(None, description="Indicates if the system is mobile or stationary")
    is_gps_enabled: bool = Field(..., description="Indicates if the system provides GPS location with observations")
    manufacturer: Optional[str] = Field(None, description="The manufacturer of the system")
    model: Optional[str] = Field(None, description="The model of the system")
    serial_number: Optional[str] = Field(None, description="The serial number of the system")
    properties: Optional[Dict[str, Any]] = Field(None, description="Arbitrary system properties as JSON")
    media_links: Optional[List[HttpUrl]] = Field(None, description="Links to images, documents, or other media related to the system")

class SystemWrite(SystemBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the system")

class SystemRead(SystemWrite):
    subsystems: Optional[List["SystemRead"]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Temperature Sensor",
                "description": "A sensor for measuring temperature",
                "system_type": "SENSOR",
                "external_id": "mqtt-id:temp-sensor-001",
                "is_mobile": False,
                "is_gps_enabled": False,
                "manufacturer": "SensorTech",
                "model": "ST-1000",
                "serial_number": "SN123456789",
                "properties": {"accuracy": "±0.5°C"},
                "media_links": ["https://example.com/sensor-image"]
            }
        }

class SystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_type: Optional[str] = None
    external_id: Optional[str] = None
    is_mobile: Optional[bool] = None
    is_gps_enabled: Optional[bool] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    media_links: Optional[List[HttpUrl]] = None


class SystemStatus(BaseModel):
    system_id: UUID
    last_observation: Optional[datetime] = None
    online: bool

    model_config = {"from_attributes": True}