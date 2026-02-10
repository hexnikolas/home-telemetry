from pydantic import BaseModel, UUID4,  HttpUrl, Field
from typing import Optional, Dict, Any, List
from enum import Enum

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
    subsystems: Optional[List["SystemRead"]] = None
