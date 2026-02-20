from pydantic import BaseModel, UUID4,  HttpUrl, Field
from typing import Optional, Dict, Any, List
import enum
from datetime import datetime
from uuid import UUID

class ProcedureTypes(str, enum.Enum):
    DATA_COLLECTION = "DATA_COLLECTION"              # Procedure for collecting measurements
    DATA_PROCESSING = "DATA_PROCESSING"              # Procedure for transforming/analyzing data
    SENSOR_CALIBRATION = "SENSOR_CALIBRATION"        # Procedure for calibrating sensors
    ACTUATOR_OPERATION = "ACTUATOR_OPERATION"        # Procedure for actuator tasks
    MAINTENANCE = "MAINTENANCE"                      # Procedure for system upkeep
    SHUTDOWN = "SHUTDOWN"                            # Procedure for system shutdown
    STARTUP = "STARTUP"                              # Procedure for system startup
    ALGORITHM_EXECUTION = "ALGORITHM_EXECUTION"      # Running algorithms on data or control logic
    USER_DEFINED = "USER_DEFINED"                    # Catch-all for custom or unspecified procedures


class ProcedureBase(BaseModel):
    name: str = Field(..., description="Human readable name of the deployment")
    description: Optional[str] = Field(None, description="Human readable description of the deployment")
    procedure_type: ProcedureTypes = Field(..., description="The type of procedure")
    reference: Optional[str] = Field(None, description="Reference URL or identifier for the procedure")
    steps: Optional[List[str]] = Field(None, description="Steps invovled in the procedure")
    properties: Optional[Dict[str, Any]] = Field(None, description="Arbitrary procedure properties as JSON")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tasmota SHT40 sensor procedure",
                "description": "Tasmota SHT40 test procedure",
                "procedure_type": "DATA_COLLECTION",
                "reference": "https://example.com/procedure/123",
                "steps": [
                    "Step 1: Initialize sensor",
                    "Step 2: Collect data",
                    "Step 3: Process data"
                ],
                "properties": {
                    "test": "yes"
                }
            }
        }

class ProcedureWrite(ProcedureBase):
    pass


class ProcedureRead(ProcedureBase):
    id: Optional[UUID4] = Field(None, description="Unique identifier for the Procedure")




class ProcedureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    procedure_type: Optional[ProcedureTypes] = None
    reference: Optional[str] = None
    steps: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
