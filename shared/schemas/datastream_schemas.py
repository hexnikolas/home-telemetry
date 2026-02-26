from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any
from enum import Enum
from schemas.observed_property_schemas import ObservedPropertyRead


class ValueTypes(str, Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"


class DatastreamBase(BaseModel):
    name: str = Field(..., description="Human readable name of the datastream")
    description: Optional[str] = Field(None, description="Human readable description of the datastream")
    system_id: UUID4 = Field(..., description="System generating this datastream")
    observed_property_id: Optional[UUID4] = Field(None, description="Observed property linked to this datastream")
    deployment_id: Optional[UUID4] = Field(None, description="Deployment during which this datastream was generated")
    procedure_id: Optional[UUID4] = Field(None, description="Procedure used for generating observations")
    feature_of_interest_id: Optional[UUID4] = Field(None, description="Optional feature of interest this datastream observes")
    is_gps_enabled: bool = Field(..., description="Indicates if the datastream provides GPS location with observations")
    observation_result_type: ValueTypes = Field(..., description="Data type of the observation results in this datastream")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional metadata or custom properties of the datastream")


class DatastreamWrite(DatastreamBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the datastream")


class DatastreamRead(DatastreamWrite):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Temperature Stream",
                "description": "Stream of temperature data",
                "system_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "observed_property_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "deployment_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "procedure_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "feature_of_interest_id": "c3dfd894-2629-4232-91ae-df3206daf509",
                "is_gps_enabled": False,
                "observation_result_type": "FLOAT",
                "properties": {"unit": "°C"}
            }
        }
    )


class DatastreamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_id: Optional[UUID4] = None
    observed_property_id: Optional[UUID4] = None
    deployment_id: Optional[UUID4] = None
    procedure_id: Optional[UUID4] = None
    feature_of_interest_id: Optional[UUID4] = None
    is_gps_enabled: Optional[bool] = None
    observation_result_type: Optional[ValueTypes] = None
    properties: Optional[Dict[str, Any]] = None