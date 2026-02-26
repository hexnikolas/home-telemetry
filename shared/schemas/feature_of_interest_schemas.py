from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any, List
from enum import Enum

class FeatureOfInterestTypes(str, Enum):
    ENVIRONMENT = "ENVIRONMENT"                      # General environmental feature (e.g., climate, ecosystem)
    ATMOSPHERE = "ATMOSPHERE"                        # Atmospheric feature (e.g., air quality, weather)
    HYDROSPHERE = "HYDROSPHERE"                      # Water-related (e.g., river, ocean, groundwater)
    LITHOSPHERE = "LITHOSPHERE"                      # Earth surface/soil/rock
    BIOSPHERE = "BIOSPHERE"                          # Living organisms (plants, animals, ecosystems)
    BUILT_ENVIRONMENT = "BUILT_ENVIRONMENT"          # Human-made structures (buildings, roads, cities)
    INDIVIDUAL = "INDIVIDUAL"                        # Single person, animal, or device
    POPULATION = "POPULATION"                        # Groups of individuals (e.g., community, herd, crowd)
    OBJECT = "OBJECT"                                # Specific physical object of interest
    EVENT = "EVENT"                                  # Event or phenomenon (e.g., fire, flood, accident)
    CUSTOM = "CUSTOM"                                # User-defined or unspecified feature

class FeatureOfInterestBase(BaseModel):
    name: str = Field(..., description="Human readable name of the feature of interest")
    description: Optional[str] = Field(None, description="Human readable description of the feature of interest")
    feature_type: FeatureOfInterestTypes = Field(..., description="The type of feature of interest")
    reference: Optional[str] = Field(None, description="Reference or citation for the feature of interest")
    location: Optional[str] = Field(None, description="The location of the sampling feature")
    properties: Optional[Dict[str, Any]] = Field(None, description="Arbitrary properties as JSON")
    media_links: Optional[List[str]] = Field(None, description="Links to images, documents, or other media related to the feature of interest")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Nikos' House",
                "description": "Measurements of various smart meters inside the house",
                "feature_type": "ENVIRONMENT",
                "reference": "https://en.wikipedia.org/wiki/House",
                "location": "Athens",
                "properties": {
                    "area": "80 square feet",
                    "num_rooms": 3
                },
                "media_links": ["https://example.com/house-image"]
            }
        }
    )

class FeatureOfInterestWrite(FeatureOfInterestBase):
    pass

class FeatureOfInterestRead(FeatureOfInterestBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the feature of interest")

class FeatureOfInterestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    feature_type: Optional[FeatureOfInterestTypes] = None
    reference: Optional[str] = None
    location: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    media_links: Optional[List[str]] = None