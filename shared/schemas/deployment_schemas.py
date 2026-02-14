from pydantic import BaseModel, UUID4,  HttpUrl, Field
from typing import Optional, Dict, Any, List
import enum
from datetime import datetime
from uuid import UUID

class DeploymentTypes(str, enum.Enum):
    FIELD = "FIELD"                                  # Outdoor, in-situ deployment (e.g., sensors in a forest)
    LABORATORY = "LABORATORY"                        # Controlled indoor/lab environment
    MOBILE = "MOBILE"                                # Mobile deployment (e.g., sensors on a drone, vehicle, ship)
    FIXED = "FIXED"                                  # Stationary deployment (e.g., weather station, tower)
    TEMPORARY = "TEMPORARY"                          # Short-term campaign or test deployment
    PERMANENT = "PERMANENT"                          # Long-term, continuous deployment
    VIRTUAL = "VIRTUAL"                              # Software-only deployment (e.g., simulation environment)
    CUSTOM = "CUSTOM"                                # User-defined or unspecified type


class DeploymentBase(BaseModel):
    name: str = Field(..., description="Human readable name of the deployment")
    description: Optional[str] = Field(None, description="Human readable description of the deployment")
    deployment_type: DeploymentTypes = Field(..., description="The type of deployment")
    location: Optional[str] = Field(None, description="Deployment's Location")
    properties: Optional[Dict[str, Any]] = Field(None, description="Arbitrary deployment properties as JSON")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tasmota SHT40 sensor deployment",
                "description": "Tasmota SHT40 test deployment",
                "deployment_type": "LABORATORY",
                "location": "Mini-PC, hall",
                "properties": {
                    "test": "yes",
                    "deployment_date": "12/2/2026"
                }
            }
        }

class DeploymentWrite(DeploymentBase):
    pass


class DeploymentRead(DeploymentBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the Deployment")
    system_id: UUID4 = Field(..., description="The Unique identifier of the deployed system")




class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deployment_type: Optional[str] = None
    location: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
