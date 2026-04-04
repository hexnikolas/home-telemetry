"""
Unit tests for message handlers - sensor data transformation
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.handlers import handle_sensor_SHT40, handle_sensor_A1T, _parse_time


class TestParseTime:
    """Test time parsing and UTC+1 to UTC conversion"""

    def test_parse_time_with_valid_iso_format(self):
        """Test parsing valid ISO format time string"""
        time_str = "2026-04-04T12:30:45"
        result = _parse_time({"Time": time_str})
        
        assert result is not None
        assert isinstance(result, datetime)
        # Should be converted to UTC
        assert result.tzinfo == timezone.utc

    def test_parse_time_converts_utc_plus_1_to_utc(self):
        """Test that UTC+1 timestamps are converted to UTC"""
        # Create a time in UTC+1
        time_str = "2026-04-04T12:00:00"
        result = _parse_time({"Time": time_str})
        
        # The time should be adjusted (minus 1 hour)
        assert result.hour == 11  # 12:00 UTC+1 = 11:00 UTC

    def test_parse_time_missing_time_field_returns_now(self):
        """Test that missing Time field returns current UTC datetime"""
        result = _parse_time({})
        
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        # Should be approximately now
        assert (datetime.now(timezone.utc) - result).total_seconds() < 1

    def test_parse_time_invalid_time_string_returns_now(self):
        """Test that invalid time string returns current UTC datetime"""
        result = _parse_time({"Time": "invalid-time"})
        
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_time_none_value_returns_now(self):
        """Test that None time value returns current UTC datetime"""
        result = _parse_time({"Time": None})
        
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestHandlerSHT40:
    """Test SHT40 sensor handler"""

    @pytest.mark.asyncio
    async def test_handle_sht40_all_readings(self):
        """Test SHT40 handler with all sensor readings"""
        ds_id_temp = uuid4()
        ds_id_humid = uuid4()
        ds_id_dew = uuid4()
        
        datastreams = {
            "Temperature": str(ds_id_temp),
            "Humidity": str(ds_id_humid),
            "DewPoint": str(ds_id_dew),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 22.5,
                "Humidity": 65.0,
                "DewPoint": 14.2,
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        assert len(observations) == 3
        assert observations[0].result_numeric == 22.5
        assert observations[1].result_numeric == 65.0
        assert observations[2].result_numeric == 14.2

    @pytest.mark.asyncio
    async def test_handle_sht40_partial_readings(self):
        """Test SHT40 handler with partial sensor data"""
        ds_id_temp = uuid4()
        ds_id_humid = uuid4()
        
        datastreams = {
            "Temperature": str(ds_id_temp),
            "Humidity": str(ds_id_humid),
            "DewPoint": str(uuid4()),
        }
        
        # Only Temperature and Humidity available
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 20.0,
                "Humidity": 60.0,
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        # Should only have 2 observations
        assert len(observations) == 2
        assert observations[0].result_numeric == 20.0
        assert observations[1].result_numeric == 60.0

    @pytest.mark.asyncio
    async def test_handle_sht40_missing_sensor_key(self):
        """Test SHT40 handler when SHT4X key is missing"""
        datastreams = {
            "Temperature": str(uuid4()),
            "Humidity": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            # SHT4X key is missing
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        # Should have no observations
        assert len(observations) == 0

    @pytest.mark.asyncio
    async def test_handle_sht40_no_matching_datastreams(self):
        """Test SHT40 handler when datastreams don't have required keys"""
        datastreams = {
            "OtherKey": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 22.5,
                "Humidity": 65.0,
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        assert len(observations) == 0

    @pytest.mark.asyncio
    async def test_handle_sht40_result_time_set(self):
        """Test that SHT40 observations have correct result_time"""
        datastreams = {
            "Temperature": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 22.5,
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        assert len(observations) == 1
        assert observations[0].result_time is not None
        assert observations[0].result_time.tzinfo == timezone.utc


class TestHandlerA1T:
    """Test A1T power sensor handler"""

    @pytest.mark.asyncio
    async def test_handle_a1t_all_readings(self):
        """Test A1T handler with all energy readings"""
        ds_id_power = uuid4()
        ds_id_voltage = uuid4()
        ds_id_total = uuid4()
        
        datastreams = {
            "Power": str(ds_id_power),
            "Voltage": str(ds_id_voltage),
            "Total": str(ds_id_total),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "ENERGY": {
                "Power": 250.5,
                "Voltage": 230.0,
                "Total": 1234.56,
            }
        }
        
        observations = await handle_sensor_A1T(data, datastreams)
        
        assert len(observations) == 3
        assert observations[0].result_numeric == 250.5
        assert observations[1].result_numeric == 230.0
        assert observations[2].result_numeric == 1234.56

    @pytest.mark.asyncio
    async def test_handle_a1t_partial_readings(self):
        """Test A1T handler with partial energy data"""
        ds_id_power = uuid4()
        
        datastreams = {
            "Power": str(ds_id_power),
            "Voltage": str(uuid4()),
            "Total": str(uuid4()),
        }
        
        # Only Power available
        data = {
            "Time": "2026-04-04T12:00:00",
            "ENERGY": {
                "Power": 200.0,
            }
        }
        
        observations = await handle_sensor_A1T(data, datastreams)
        
        # Should only have 1 observation
        assert len(observations) == 1
        assert observations[0].result_numeric == 200.0

    @pytest.mark.asyncio
    async def test_handle_a1t_missing_energy_key(self):
        """Test A1T handler when ENERGY key is missing"""
        datastreams = {
            "Power": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            # ENERGY key is missing
        }
        
        observations = await handle_sensor_A1T(data, datastreams)
        
        assert len(observations) == 0

    @pytest.mark.asyncio
    async def test_handle_a1t_zero_values(self):
        """Test A1T handler with zero energy values"""
        datastreams = {
            "Power": str(uuid4()),
            "Total": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "ENERGY": {
                "Power": 0.0,
                "Total": 0.0,
            }
        }
        
        observations = await handle_sensor_A1T(data, datastreams)
        
        # Zero values should still create observations
        assert len(observations) == 2
        assert observations[0].result_numeric == 0.0
        assert observations[1].result_numeric == 0.0

    @pytest.mark.asyncio
    async def test_handle_a1t_negative_values(self):
        """Test A1T handler with negative values (power export)"""
        datastreams = {
            "Power": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "ENERGY": {
                "Power": -50.0,  # Negative = power export
            }
        }
        
        observations = await handle_sensor_A1T(data, datastreams)
        
        assert len(observations) == 1
        assert observations[0].result_numeric == -50.0


class TestHandlerDataValidation:
    """Test data validation in handlers"""

    @pytest.mark.asyncio
    async def test_handler_creates_valid_observations(self):
        """Test that handlers create valid ObservationWrite objects"""
        datastreams = {
            "Temperature": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 22.5,
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        assert len(observations) == 1
        obs = observations[0]
        
        # Verify ObservationWrite fields
        assert obs.datastream_id is not None
        assert obs.result_time is not None
        assert obs.result_numeric == 22.5
        assert obs.result_text is None
        assert obs.result_boolean is None

    @pytest.mark.asyncio
    async def test_handler_ignores_none_values(self):
        """Test that handlers ignore None values from sensors"""
        datastreams = {
            "Temperature": str(uuid4()),
            "Humidity": str(uuid4()),
        }
        
        data = {
            "Time": "2026-04-04T12:00:00",
            "SHT4X": {
                "Temperature": 22.5,
                "Humidity": None,  # None value
            }
        }
        
        observations = await handle_sensor_SHT40(data, datastreams)
        
        # Should only have Temperature observation
        assert len(observations) == 1
        assert observations[0].result_numeric == 22.5
