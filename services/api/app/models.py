from sqlalchemy import Column, String, Text, Boolean, Float, ForeignKey, Enum, Index, PrimaryKeyConstraint, event, TIMESTAMP, ARRAY, DDL
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSON
from sqlalchemy.sql import func
from .database import Base
import uuid
import enum


class ValueTypes(enum.Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"


class SystemTypes(enum.Enum):
    SENSOR = "SENSOR"                                # Device that measures phenomena (e.g., temperature sensor)
    ACTUATOR = "ACTUATOR"                            # Device that acts upon the environment (e.g., motor, valve)
    PLATFORM = "PLATFORM"                            # Host platform carrying sensors/actuators (e.g., drone, vehicle)
    SYSTEM = "SYSTEM"                                # General system composed of multiple components
    CUSTOM = "CUSTOM"                                # Catch-all for user-defined or unspecified systems


class DeploymentTypes(enum.Enum):
    FIELD = "FIELD"                                  # Outdoor, in-situ deployment (e.g., sensors in a forest)
    LABORATORY = "LABORATORY"                        # Controlled indoor/lab environment
    MOBILE = "MOBILE"                                # Mobile deployment (e.g., sensors on a drone, vehicle, ship)
    FIXED = "FIXED"                                  # Stationary deployment (e.g., weather station, tower)
    TEMPORARY = "TEMPORARY"                          # Short-term campaign or test deployment
    PERMANENT = "PERMANENT"                          # Long-term, continuous deployment
    VIRTUAL = "VIRTUAL"                              # Software-only deployment (e.g., simulation environment)
    CUSTOM = "CUSTOM"                                # User-defined or unspecified type


class ProcedureTypes(enum.Enum):
    DATA_COLLECTION = "DATA_COLLECTION"              # Procedure for collecting measurements
    DATA_PROCESSING = "DATA_PROCESSING"              # Procedure for transforming/analyzing data
    SENSOR_CALIBRATION = "SENSOR_CALIBRATION"        # Procedure for calibrating sensors
    ACTUATOR_OPERATION = "ACTUATOR_OPERATION"        # Procedure for actuator tasks
    MAINTENANCE = "MAINTENANCE"                      # Procedure for system upkeep
    SHUTDOWN = "SHUTDOWN"                            # Procedure for system shutdown
    STARTUP = "STARTUP"                              # Procedure for system startup
    ALGORITHM_EXECUTION = "ALGORITHM_EXECUTION"      # Running algorithms on data or control logic
    USER_DEFINED = "USER_DEFINED"                    # Catch-all for custom or unspecified procedures


class FeatureOfInterestTypes(enum.Enum):
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


class ObservedProperyDomains(enum.Enum):
    ENVIRONMENTAL_BASICS = "ENVIRONMENTAL_BASICS"    # Generic physical environment (e.g., temperature, humidity, pressure)
    AIR_QUALITY = "AIR_QUALITY"                      # Gases, particulates, air pollutants (e.g., CO2, PM2.5, ozone)
    WATER_QUALITY = "WATER_QUALITY"                  # Chemical, physical, and biological water properties (e.g., pH, turbidity, salinity)
    ELECTRICAL = "ELECTRICAL"                        # Voltage, current, power, frequency, resistance, conductivity
    LIGHT_AND_RADIATION = "LIGHT_AND_RADIATION"      # Luminance, UV index, solar radiation, infrared
    MOTION_AND_POSITION = "MOTION_AND_POSITION"      # Acceleration, velocity, orientation, GPS position
    MECHANICAL = "MECHANICAL"                        # Force, torque, strain, pressure (mechanical stress/strain sensors)
    BIOLOGICAL = "BIOLOGICAL"                        # Biological measurements (e.g., biomass, chlorophyll, microbial counts)
    BUILT_ENVIRONMENT = "BUILT_ENVIRONMENT"          # Building-related metrics (e.g., occupancy, HVAC, noise levels)
    REMOTE_SENSING = "REMOTE_SENSING"                # Satellite or drone observations (spectral bands, NDVI, SAR)
    ENERGY_AND_HEAT = "ENERGY_AND_HEAT"              # Energy usage, heat flux, thermal comfort
    HEALTH_AND_BIOMEDICAL = "HEALTH_AND_BIOMEDICAL"  # Heart rate, blood oxygen, body temperature, biosignals
    SPECIAL_CASES = "SPECIAL_CASES"                  # Miscellaneous or domain-specific properties


class ControlStreamTypes(enum.Enum):
    SELF = "SELF"                                    # Control stream that affect the parent system itself or one of its subsystems
    EXTERNAL = "EXTERNAL"                            # Control stream that affect external features of interest


class StatusCode(enum.Enum):
    PENDING = "PENDING"                              # The command is pending, meaning it has been received by the system but no decision to accept or reject it has been made.
    ACCEPTED = "ACCEPTED"                            # The command was accepted by the receiving system. This usually means that the command has passed the first validation steps, but it can still be rejected or fail later during execution.
    REJECTED = "REJECTED"                            # The command was rejected by the receiving system. It won’t be executed at all and the message property provides the reason for the rejection. This is a final state. No further status updates will be sent.
    SCHEDULED = "SCHEDULED"                          # The command was validated and effectively scheduled by the receiving system. When this status code is used, the scheduled execution time must be provided.
    UPDATED = "UPDATED"                              # An update to the command was received and accepted. This code must be used if the system supports task updates.
    CANCELED = "CANCELED"                            # The command was canceled by an authorized user. This code must be used if the system supports user-driven task cancellations. The REJECTED state should be used instead if the command was canceled by the receiving system. This is a final state. No further status updates will be sent.
    EXECUTING = "EXECUTING"                          # The command is currently being executed by the receiving system. The status message can provide more information about the current progress. A system can send several status updates with this code but different time stamps to report progress incrementally. In particular, the progress percentage and the end of the (estimated) execution time period can be refined in each update.
    COMPLETED = "COMPLETED"                          # The command has completed after a successful execution. The actual execution time must be provided. This is a final state. No further status updates will be sent.
    FAILED = "FAILED"                                # The command has failed during execution. The error and/or status message provides the reason for failure. This is a final state. No further status updates will be sent.


class ResponseStatus(enum.Enum):
    STATUS_UNSPECIFIED = "STATUS_UNSPECIFIED"        # Default undefined status. Should not be used explicitly in normal cases.
    OK = "OK"                                        # The request was successfully processed without errors.
    ERROR = "ERROR"                                  # A generic error occurred while processing the request.
    NOT_FOUND = "NOT_FOUND"                          # The requested resource could not be found.
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"              # The requested functionality is not supported or not implemented.
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"  # The server encountered an unexpected condition that prevented it from fulfilling the request.
    UNAUTHORIZED = "UNAUTHORIZED"                    # The request is missing valid authentication credentials.
    INVALID_PARAMETERS = "INVALID_PARAMETERS"        # One or more input parameters are invalid or missing.
    RATE_LIMITED = "RATE_LIMITED"                    # The request was rejected due to exceeding rate limits or quotas.
    SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"  # The operation succeeded, but some non-fatal issues or warnings were encountered.
    TIMEOUT = "TIMEOUT"                              # The operation timed out before completion.


class AbstractConcreteBase(Base):
    __abstract__ = True

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment='Record creation timestamp')
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment='Record last update timestamp')


class System(AbstractConcreteBase):
    __tablename__ = "systems"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, comment='Human readable name')
    description = Column(Text, comment='Human readable description')
    system_type = Column(Enum(SystemTypes), nullable=False, comment='The type of system')
    external_id = Column(String, unique=True, index=True, comment="External reference ID (e.g., MQTT ID)")
    is_mobile = Column(Boolean, default=False, comment='Indicates if the system is mobile or stationary')
    is_gps_enabled = Column(Boolean, nullable=False, default=False, comment='Indicates if the system provides GPS location with observations')
    manufacturer = Column(String, comment='The manufacturer of the system')
    model = Column(String, comment='The model of the system')
    serial_number = Column(String, comment='The serial number of the system')
    properties = Column(JSON)
    media_links = Column(ARRAY(String), default=list, comment='Links to images, documents, or other media related to the system')


class Subsystem(AbstractConcreteBase):
    __tablename__ = "subsystems"

    system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), primary_key=True, comment='The subsystem itself, which is a System resource')
    parent_system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), primary_key=True, comment='The parent System that this subsystem is part of')
    composition = Column(Boolean, comment='Indicates if the relationship is composition (true) or aggregation (false)')


class Deployment(AbstractConcreteBase):
    __tablename__ = "deployments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), comment="The system deployed during the deployment")
    name = Column(String, nullable=False, comment='Human readable name of the deployment')
    description = Column(Text, comment='Human readable description of the deployment')
    deployment_type = Column(Enum(DeploymentTypes), nullable=False, comment='The type of deployment')
    location = Column(Text, comment='The location or area where the systems are deployed.')
    properties = Column(JSON)


class Procedure(AbstractConcreteBase):
    __tablename__ = "procedures"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human readable name of the procedure")
    description = Column(Text, comment="Human readable description of the procedure")
    procedure_type = Column(Enum(ProcedureTypes), comment="Type of procedure")
    reference = Column(String, comment="Reference or citation for the procedure (e.g., ISO standard, document link)")
    steps = Column(ARRAY(String), default=list, comment="Steps involved in the procedure")
    properties = Column(JSON)


class FeatureOfInterest(AbstractConcreteBase):
    __tablename__ = "features_of_interest"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human readable name of the feature of interest")
    description = Column(Text, comment="Human readable description of the feature of interest")
    feature_type = Column(Enum(FeatureOfInterestTypes), nullable=False, comment="The type of feature of interest")
    reference = Column(String, comment="Reference or citation for the feature of interest")
    location = Column(Text, comment='The location of the sampling feature.')
    properties = Column(JSON)
    media_links = Column(ARRAY(String), default=list, comment='Links to images, documents, or other media related to the feature of interest')


class ObservedProperty(AbstractConcreteBase):
    __tablename__ = "observed_properties"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human-readable name of the observed property")
    description = Column(String, comment="Description of the observed property")
    domain = Column(Enum(ObservedProperyDomains), nullable=False, comment="Domain or category of the observed property")
    property_definition = Column(String, comment="Reference to the base property definition")
    unit_definition = Column(String, comment="Unit of measurement for the observed property")
    unit_symbol = Column(String, comment="Symbol for the unit of measurement (e.g., °C, m/s)")
    reference = Column(String, comment="Wikipedia (or other knowledge base) link for human-readable reference")
    keywords = Column(ARRAY(String), default=list, comment="Synonyms or related search terms")
    value_type = Column(Enum(ValueTypes), nullable=False, comment="Data type of the observed property value")


class Datastream(AbstractConcreteBase):
    __tablename__ = "datastreams"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human readable name of the datastream")
    description = Column(Text, comment="Human readable description of the datastream")
    system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), nullable=False, comment="System generating this datastream")
    observed_property_id = Column(PG_UUID(as_uuid=True), ForeignKey("observed_properties.id"),  comment="Observed property linked to this datastream")
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("deployments.id"), comment="Deployment during which this datastream was generated")
    procedure_id = Column(PG_UUID(as_uuid=True), ForeignKey("procedures.id"), comment="Procedure used for generating observations")
    feature_of_interest_id = Column(PG_UUID(as_uuid=True), ForeignKey("features_of_interest.id"), comment="Optional feature of interest this datastream observes")
    external_id = Column(String, ForeignKey("systems.external_id"), index=True, comment="External reference ID (e.g., MQTT topic ID)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Indicates if the datastream is currently active")
    is_gps_enabled = Column(Boolean, nullable=False, comment="Indicates if the datastream provides GPS location with observations")
    observation_result_type = Column(Enum(ValueTypes), nullable=False, comment="Data type of the observation results in this datastream")
    properties = Column(JSON, comment="Additional metadata or custom properties of the datastream")


class Observation(AbstractConcreteBase):
    __tablename__ = "observations"

    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, index=True, comment="Primary key of the observation")
    datastream_id = Column(PG_UUID(as_uuid=True), ForeignKey("datastreams.id"), comment="The DataStream that this observation belongs to")
    result_time = Column(TIMESTAMP(timezone=True), nullable=False, comment="The time the result observation was obtained")
    # phenomenon_time = Column(TIMESTAMP(timezone=True), comment="The time the phenomenon occurred")
    result_complex = Column(JSON, comment="Complex result if applicable")
    result_numeric = Column(Float, comment="Numeric result if applicable")
    result_text = Column(Text, comment="Text result if applicable")
    result_boolean = Column(Boolean, comment="Boolean result if applicable") 
    parameters = Column(JSON, comment="Additional parameters associated with the observation")   

    __table_args__ = (
        PrimaryKeyConstraint("id", "result_time"),
        Index("ix_observations_datastream_time", "datastream_id", "result_time"),
    )


class TaskingCapability(AbstractConcreteBase):
    __tablename__ = "tasking_capabilities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human-readable name of the capability")
    description = Column(Text, comment="Description of what this tasking capability does")
    system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), comment="System this tasking capability applies to")
    input_schema = Column(JSON, nullable=False, comment="JSON Schema describing valid input parameters for commands")
    properties = Column(JSON, comment="Optional metadata for advanced capability configuration")


class ControlStream(AbstractConcreteBase):
    __tablename__ = "control_streams"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False, comment="Human readable name of the control stream")
    description = Column(Text, comment="Human readable description of the control stream")
    system_id = Column(PG_UUID(as_uuid=True), ForeignKey("systems.id"), nullable=False, comment="System receiving commands from this control stream")
    tasking_capability_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasking_capabilities.id"), comment="Defines allowed command structure for this stream")
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("deployments.id"), comment="Deployment during which this control stream is used")
    procedure_id = Column(PG_UUID(as_uuid=True), ForeignKey("procedures.id"), comment="Procedure used to process commands received in the control stream")
    feature_of_interest_id = Column(PG_UUID(as_uuid=True), ForeignKey("features_of_interest.id"), comment="Optional feature of interest this control stream affects")
    external_id = Column(String, ForeignKey("systems.external_id"), index=True, comment="External reference ID (e.g., MQTT topic ID)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Indicates if the control stream is currently active")
    control_stream_type = Column(Enum(ControlStreamTypes), nullable=False, comment="Data type of the control commands in this stream")
    properties = Column(JSON, comment="Additional metadata or custom properties of the control stream")


class Command(AbstractConcreteBase):
    __tablename__ = "commands"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    control_stream_id = Column(PG_UUID(as_uuid=True), ForeignKey("control_streams.id"), nullable=False, comment="The control stream to which this command belongs")
    issue_time = Column(TIMESTAMP(timezone=True), nullable=False, comment="The time the command was issued")
    parameters = Column(JSON, comment="Parameters associated with the command")
    # current_status = Column(Enum(StatusCode), nullable=False, comment="Current status of the command")
    status_message = Column(Text, comment="Additional information about the command status")
    scheduled_time = Column(TIMESTAMP(timezone=True), comment="Scheduled execution time for the command")
    execution_time_start = Column(TIMESTAMP(timezone=True), comment="Actual start time of command execution")
    execution_time_end = Column(TIMESTAMP(timezone=True), comment="Actual end time of command execution")
    sender = Column(String, comment="Identifier of the user or system that issued the command")

    __table_args__ = (
        Index("ix_commands_stream_time", "control_stream_id", "issue_time"),
    )


class CommandStatus(AbstractConcreteBase):
    __tablename__ = "command_status"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    command_id = Column(PG_UUID(as_uuid=True), ForeignKey("commands.id"), nullable=False, comment="Command this status entry belongs to")
    status_time = Column(TIMESTAMP(timezone=True), nullable=False, comment="Time at which this status update was reported")
    status_code = Column(Enum(StatusCode), nullable=False, comment="State of the command (queued, running, completed, failed, etc.)")
    status_message = Column(Text, comment="Optional human-readable status message")
    response_result = Column(JSON, comment="Any structured result returned by the system during or after execution")

    __table_args__ = (
        Index("ix_command_status_time", "command_id", "status_time"),
    )


class ControlStreamObservation(AbstractConcreteBase):
    __tablename__ = "control_stream_observations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_stream_id = Column(PG_UUID(as_uuid=True), ForeignKey("control_streams.id"), nullable=False)
    observation_time = Column(TIMESTAMP(timezone=True), nullable=False, comment="Time the observed state was recorded")
    state = Column(JSON, nullable=False, comment="Device state: battery, position, status, etc.")



# TimescaleDB hypertable for Observations
event.listen(
    Observation.__table__,
    'after_create',
    DDL(f"SELECT create_hypertable('{Observation.__tablename__}', 'result_time', if_not_exists => TRUE, chunk_time_interval => interval '1 day');")
)