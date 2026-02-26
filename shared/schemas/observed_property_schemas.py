from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, List
from enum import Enum

class ValueTypes(str, Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"



class ObservedPropertyDomains(str, Enum):
    ENVIRONMENTAL_BASICS = "ENVIRONMENTAL_BASICS"
    AIR_QUALITY = "AIR_QUALITY"
    WATER_QUALITY = "WATER_QUALITY"
    ELECTRICAL = "ELECTRICAL"
    LIGHT_AND_RADIATION = "LIGHT_AND_RADIATION"
    MOTION_AND_POSITION = "MOTION_AND_POSITION"
    MECHANICAL = "MECHANICAL"
    BIOLOGICAL = "BIOLOGICAL"
    BUILT_ENVIRONMENT = "BUILT_ENVIRONMENT"
    REMOTE_SENSING = "REMOTE_SENSING"
    ENERGY_AND_HEAT = "ENERGY_AND_HEAT"
    HEALTH_AND_BIOMEDICAL = "HEALTH_AND_BIOMEDICAL"
    SPECIAL_CASES = "SPECIAL_CASES"

class ObservedPropertyBase(BaseModel):
    name: str = Field(..., description="Human readable name")
    description: Optional[str] = Field(None, description="Human readable description")
    domain: ObservedPropertyDomains = Field(..., description="The domain of the observed property")
    property_definition: Optional[str] = Field(None, description="Reference to the base property definition")
    unit_definition: Optional[str] = Field(None, description="Unit of measurement for the observed property")
    unit_symbol: Optional[str] = Field(None, description="Symbol for the unit of measurement (e.g., °C, m/s)")
    reference: Optional[str] = Field(None, description="Wikipedia (or other knowledge base) link for human-readable reference")
    keywords: Optional[List[str]] = Field(None, description="Synonyms or related search terms")
    value_type: ValueTypes = Field(..., description="Data type of the observed property value")

class ObservedPropertyWrite(ObservedPropertyBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the observed property")

class ObservedPropertyRead(ObservedPropertyWrite):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Temperature",
                "description": "Measurement of thermal energy",
                "domain": "ENVIRONMENTAL_BASICS",
                "property_definition": "ISO 80000-5",
                "unit_definition": "Degrees Celsius",
                "unit_symbol": "°C",
                "reference": "https://en.wikipedia.org/wiki/Celsius",
                "keywords": ["heat", "thermal energy"],
                "value_type": "FLOAT"
            }
        }
    )

class ObservedPropertyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[ObservedPropertyDomains] = None
    property_definition: Optional[str] = None
    unit_definition: Optional[str] = None
    unit_symbol: Optional[str] = None
    reference: Optional[str] = None
    keywords: Optional[List[str]] = None
    value_type: Optional[ValueTypes] = None