import pytest
from uuid import uuid4
from pydantic import ValidationError
from schemas.datastream_schemas import ValueTypes, DatastreamBase, DatastreamWrite, DatastreamRead, DatastreamUpdate


class TestDatastreamBase:
    """Test DatastreamBase schema"""

    def test_datastream_base_minimal(self):
        """Test creating datastream with required fields"""
        ds = DatastreamBase(
            name="Stream 1",
            system_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        assert ds.name == "Stream 1"
        assert ds.system_id is not None
        assert ds.observation_result_type == ValueTypes.FLOAT

    def test_datastream_base_with_description(self):
        """Test datastream with description"""
        ds = DatastreamBase(
            name="Temperature Stream",
            description="Ambient temperature measurements",
            system_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        assert ds.description == "Ambient temperature measurements"

    def test_datastream_base_with_observed_property(self):
        """Test datastream with observed property"""
        ds = DatastreamBase(
            name="Stream",
            system_id=uuid4(),
            observed_property_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        assert ds.observed_property_id is not None

    def test_datastream_base_all_value_types(self):
        """Test datastream with each value type"""
        for val_type in [ValueTypes.BOOLEAN, ValueTypes.INTEGER, ValueTypes.FLOAT, 
                         ValueTypes.STRING, ValueTypes.JSON]:
            ds = DatastreamBase(
                name=f"Stream {val_type}",
                system_id=uuid4(),
                is_gps_enabled=False,
                observation_result_type=val_type
            )
            assert ds.observation_result_type == val_type

    def test_datastream_base_missing_name_fails(self):
        """Test that missing name raises validation error"""
        with pytest.raises(ValidationError):
            DatastreamBase(
                system_id=uuid4(),
                is_gps_enabled=False,
                observation_result_type=ValueTypes.FLOAT
            )

    def test_datastream_base_missing_system_id_fails(self):
        """Test that missing system_id raises validation error"""
        with pytest.raises(ValidationError):
            DatastreamBase(
                name="Stream",
                is_gps_enabled=False,
                observation_result_type=ValueTypes.FLOAT
            )

    def test_datastream_base_missing_observation_result_type_fails(self):
        """Test that missing observation_result_type raises validation error"""
        with pytest.raises(ValidationError):
            DatastreamBase(
                name="Stream",
                system_id=uuid4(),
                is_gps_enabled=False
            )

    def test_datastream_base_invalid_system_id(self):
        """Test that invalid UUID raises validation error"""
        with pytest.raises(ValidationError):
            DatastreamBase(
                name="Stream",
                system_id="not-a-uuid",
                is_gps_enabled=False,
                observation_result_type=ValueTypes.FLOAT
            )

    def test_datastream_base_with_gps(self):
        """Test datastream with GPS enabled"""
        ds = DatastreamBase(
            name="GPS Stream",
            system_id=uuid4(),
            is_gps_enabled=True,
            observation_result_type=ValueTypes.JSON
        )
        assert ds.is_gps_enabled is True


class TestDatastreamWrite:
    """Test DatastreamWrite schema"""

    def test_datastream_write_with_id(self):
        """Test datastream write with ID"""
        ds_id = uuid4()
        system_id = uuid4()
        ds = DatastreamWrite(
            id=ds_id,
            name="Stream",
            system_id=system_id,
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        assert ds.id == ds_id

    def test_datastream_write_without_id(self):
        """Test datastream write without ID"""
        ds = DatastreamWrite(
            name="Stream",
            system_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        assert ds.id is None


class TestDatastreamRead:
    """Test DatastreamRead schema"""

    def test_datastream_read_full(self):
        """Test creating complete datastream read"""
        ds = DatastreamRead(
            id=uuid4(),
            name="Temperature Stream",
            description="Temperature observations",
            system_id=uuid4(),
            observed_property_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT,
            properties={"unit": "°C"}
        )
        
        assert ds.name == "Temperature Stream"
        assert ds.system_id is not None
        assert ds.observation_result_type == ValueTypes.FLOAT

    def test_datastream_read_json_serialization(self):
        """Test DatastreamRead can be serialized to JSON"""
        ds = DatastreamRead(
            id=uuid4(),
            name="Stream",
            system_id=uuid4(),
            is_gps_enabled=False,
            observation_result_type=ValueTypes.FLOAT
        )
        
        json_data = ds.model_dump_json()
        assert isinstance(json_data, str)
        assert "Stream" in json_data


class TestDatastreamUpdate:
    """Test DatastreamUpdate schema (all fields optional)"""

    def test_datastream_update_empty(self):
        """Test empty datastream update"""
        ds = DatastreamUpdate()
        assert ds.name is None
        assert ds.system_id is None

    def test_datastream_update_name(self):
        """Test updating only name"""
        ds = DatastreamUpdate(name="New Name")
        assert ds.name == "New Name"
        assert ds.system_id is None

    def test_datastream_update_description(self):
        """Test updating description"""
        ds = DatastreamUpdate(description="New description")
        assert ds.description == "New description"

