import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError
from schemas.observation_schemas import ObservationBase, ObservationWrite, ObservationRead, ObservationUpdate


class TestObservationBase:
    """Test ObservationBase schema validation"""

    def test_observation_base_minimal(self):
        """Test creating observation with only required fields"""
        result_time = datetime.now()
        obs = ObservationBase(result_time=result_time)
        assert obs.result_time == result_time
        assert obs.datastream_id is None
        assert obs.result_numeric is None

    def test_observation_base_numeric_result(self):
        """Test observation with numeric result"""
        datastream_id = uuid4()
        result_time = datetime.now()
        obs = ObservationBase(
            datastream_id=datastream_id,
            result_time=result_time,
            result_numeric=23.5
        )
        assert obs.datastream_id == datastream_id
        assert obs.result_numeric == 23.5
        assert obs.result_text is None
        assert obs.result_boolean is None

    def test_observation_base_text_result(self):
        """Test observation with text result"""
        obs = ObservationBase(
            result_time=datetime.now(),
            result_text="test value"
        )
        assert obs.result_text == "test value"
        assert obs.result_numeric is None

    def test_observation_base_boolean_result(self):
        """Test observation with boolean result"""
        obs = ObservationBase(
            result_time=datetime.now(),
            result_boolean=True
        )
        assert obs.result_boolean is True

    def test_observation_base_complex_result(self):
        """Test observation with complex result (JSON)"""
        complex_data = {"temperature": 23.5, "humidity": 65}
        obs = ObservationBase(
            result_time=datetime.now(),
            result_complex=complex_data
        )
        assert obs.result_complex == complex_data

    def test_observation_base_with_parameters(self):
        """Test observation with additional parameters"""
        params = {"quality": "good", "source": "mqtt"}
        obs = ObservationBase(
            result_time=datetime.now(),
            result_numeric=20.0,
            parameters=params
        )
        assert obs.parameters == params

    def test_observation_base_missing_result_time_fails(self):
        """Test that missing result_time raises validation error"""
        with pytest.raises(ValidationError):
            ObservationBase()

    def test_observation_base_invalid_result_time_type(self):
        """Test that invalid result_time type raises validation error"""
        with pytest.raises(ValidationError):
            ObservationBase(result_time="not a datetime")

    def test_observation_base_invalid_numeric_result_type(self):
        """Test that non-numeric result_numeric raises validation error"""
        with pytest.raises(ValidationError):
            ObservationBase(
                result_time=datetime.now(),
                result_numeric="not a number"
            )

    def test_observation_base_invalid_datastream_uuid(self):
        """Test that invalid UUID for datastream_id raises validation error"""
        with pytest.raises(ValidationError):
            ObservationBase(
                result_time=datetime.now(),
                datastream_id="not-a-uuid"
            )


class TestObservationWrite:
    """Test ObservationWrite schema"""

    def test_observation_write_with_id(self):
        """Test creating observation write with ID"""
        obs_id = uuid4()
        result_time = datetime.now()
        obs = ObservationWrite(
            id=obs_id,
            result_time=result_time,
            result_numeric=25.0
        )
        assert obs.id == obs_id
        assert obs.result_numeric == 25.0

    def test_observation_write_without_id(self):
        """Test creating observation write without ID (optional)"""
        obs = ObservationWrite(
            result_time=datetime.now(),
            result_numeric=25.0
        )
        assert obs.id is None
        assert obs.result_numeric == 25.0


class TestObservationRead:
    """Test ObservationRead schema"""

    def test_observation_read_full(self):
        """Test creating complete observation read"""
        obs_id = uuid4()
        ds_id = uuid4()
        result_time = datetime.now()
        
        obs = ObservationRead(
            id=obs_id,
            datastream_id=ds_id,
            result_time=result_time,
            result_numeric=23.5,
            parameters={"quality": "good"}
        )
        
        assert obs.id == obs_id
        assert obs.datastream_id == ds_id
        assert obs.result_time == result_time
        assert obs.result_numeric == 23.5
        assert obs.parameters["quality"] == "good"

    def test_observation_read_json_serialization(self):
        """Test ObservationRead can be serialized to JSON"""
        obs = ObservationRead(
            id=uuid4(),
            datastream_id=uuid4(),
            result_time=datetime.now(),
            result_numeric=20.0
        )
        
        json_data = obs.model_dump_json()
        assert isinstance(json_data, str)
        assert "result_numeric" in json_data

    def test_observation_read_from_dict(self):
        """Test creating ObservationRead from dictionary"""
        obs_dict = {
            "id": str(uuid4()),
            "datastream_id": str(uuid4()),
            "result_time": datetime.now().isoformat(),
            "result_numeric": 22.5
        }
        
        obs = ObservationRead(**obs_dict)
        assert obs.result_numeric == 22.5


class TestObservationUpdate:
    """Test ObservationUpdate schema (all fields optional)"""

    def test_observation_update_empty(self):
        """Test creating empty observation update"""
        obs = ObservationUpdate()
        assert obs.datastream_id is None
        assert obs.result_numeric is None
        assert obs.result_time is None

    def test_observation_update_only_numeric(self):
        """Test updating only numeric result"""
        obs = ObservationUpdate(result_numeric=30.0)
        assert obs.result_numeric == 30.0
        assert obs.result_text is None

    def test_observation_update_multiple_fields(self):
        """Test updating multiple fields"""
        new_time = datetime.now()
        obs = ObservationUpdate(
            result_time=new_time,
            result_numeric=25.0,
            parameters={"updated": True}
        )
        assert obs.result_time == new_time
        assert obs.result_numeric == 25.0
        assert obs.parameters["updated"] is True

    def test_observation_update_invalid_numeric(self):
        """Test that invalid numeric in update raises error"""
        with pytest.raises(ValidationError):
            ObservationUpdate(result_numeric="invalid")


class TestObservationMultipleResults:
    """Test observations with multiple result types"""

    def test_observation_can_have_multiple_result_types(self):
        """Test that observation can have multiple result types (validation allows it)"""
        obs = ObservationBase(
            result_time=datetime.now(),
            result_numeric=25.0,
            result_text="temperature",
            result_boolean=True,
            result_complex={"unit": "celsius"}
        )
        
        # Schema allows multiple types, but typically only one should be used
        assert obs.result_numeric == 25.0
        assert obs.result_text == "temperature"
        assert obs.result_boolean is True
        assert obs.result_complex["unit"] == "celsius"
