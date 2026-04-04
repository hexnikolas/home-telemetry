import pytest
from uuid import uuid4
from pydantic import ValidationError, HttpUrl
from schemas.system_schemas import SystemTypes, SystemBase, SystemWrite, SystemRead


class TestSystemTypes:
    """Test SystemTypes enum"""

    def test_system_type_sensor(self):
        """Test SENSOR system type"""
        assert SystemTypes.SENSOR == "SENSOR"
        assert SystemTypes.SENSOR.value == "SENSOR"

    def test_system_type_actuator(self):
        """Test ACTUATOR system type"""
        assert SystemTypes.ACTUATOR == "ACTUATOR"

    def test_system_type_platform(self):
        """Test PLATFORM system type"""
        assert SystemTypes.PLATFORM == "PLATFORM"

    def test_system_type_system(self):
        """Test SYSTEM system type"""
        assert SystemTypes.SYSTEM == "SYSTEM"

    def test_system_type_custom(self):
        """Test CUSTOM system type"""
        assert SystemTypes.CUSTOM == "CUSTOM"

    def test_all_system_types_valid(self):
        """Test all system types are valid"""
        valid_types = ["SENSOR", "ACTUATOR", "PLATFORM", "SYSTEM", "CUSTOM"]
        for type_str in valid_types:
            assert SystemTypes(type_str) in SystemTypes


class TestSystemBase:
    """Test SystemBase schema validation"""

    def test_system_base_minimal(self):
        """Test creating system with only required fields"""
        sys = SystemBase(
            name="Test System",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False
        )
        assert sys.name == "Test System"
        assert sys.system_type == SystemTypes.SENSOR
        assert sys.is_gps_enabled is False
        assert sys.description is None

    def test_system_base_full(self):
        """Test creating system with all fields"""
        sys = SystemBase(
            name="Temperature Sensor",
            description="A temperature measurement sensor",
            system_type=SystemTypes.SENSOR,
            external_id="mqtt-sensor-001",
            is_mobile=False,
            is_gps_enabled=False,
            manufacturer="SensorCorp",
            model="SC-2000",
            serial_number="SN123456",
            properties={"accuracy": "±0.5°C", "range": "-40 to 125°C"},
            media_links=["https://example.com/sensor.jpg"]
        )
        
        assert sys.name == "Temperature Sensor"
        assert sys.manufacturer == "SensorCorp"
        assert sys.is_mobile is False
        assert sys.properties["accuracy"] == "±0.5°C"
        assert len(sys.media_links) == 1

    def test_system_base_with_media_links(self):
        """Test system with media links (URLs)"""
        urls = [
            "https://example.com/image1.jpg",
            "https://example.com/datasheet.pdf"
        ]
        sys = SystemBase(
            name="Sensor",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False,
            media_links=urls
        )
        assert len(sys.media_links) == 2

    def test_system_base_missing_name_fails(self):
        """Test that missing name raises validation error"""
        with pytest.raises(ValidationError):
            SystemBase(
                system_type=SystemTypes.SENSOR,
                is_gps_enabled=False
            )

    def test_system_base_missing_system_type_fails(self):
        """Test that missing system_type raises validation error"""
        with pytest.raises(ValidationError):
            SystemBase(
                name="Test",
                is_gps_enabled=False
            )

    def test_system_base_missing_is_gps_enabled_fails(self):
        """Test that missing is_gps_enabled raises validation error"""
        with pytest.raises(ValidationError):
            SystemBase(
                name="Test",
                system_type=SystemTypes.SENSOR
            )

    def test_system_base_invalid_system_type_string(self):
        """Test that invalid system type string raises validation error"""
        with pytest.raises(ValidationError):
            SystemBase(
                name="Test",
                system_type="INVALID_TYPE",
                is_gps_enabled=False
            )

    def test_system_base_invalid_media_link_url(self):
        """Test that invalid URL in media_links raises validation error"""
        with pytest.raises(ValidationError):
            SystemBase(
                name="Test",
                system_type=SystemTypes.SENSOR,
                is_gps_enabled=False,
                media_links=["not a url"]
            )

    def test_system_base_gps_enabled_true(self):
        """Test system with GPS enabled"""
        sys = SystemBase(
            name="Mobile Sensor",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=True,
            is_mobile=True
        )
        assert sys.is_gps_enabled is True
        assert sys.is_mobile is True

    def test_system_base_properties_dict(self):
        """Test system with arbitrary JSON properties"""
        props = {
            "frequency": "1Hz",
            "resolution": 12,
            "power_consumption": 0.5,
            "nested": {"key": "value"}
        }
        sys = SystemBase(
            name="Advanced Sensor",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False,
            properties=props
        )
        assert sys.properties["frequency"] == "1Hz"
        assert sys.properties["nested"]["key"] == "value"


class TestSystemWrite:
    """Test SystemWrite schema"""

    def test_system_write_with_id(self):
        """Test creating system write with ID"""
        sys_id = uuid4()
        sys = SystemWrite(
            id=sys_id,
            name="Test",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False
        )
        assert sys.id == sys_id

    def test_system_write_without_id(self):
        """Test creating system write without ID (optional)"""
        sys = SystemWrite(
            name="Test",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False
        )
        assert sys.id is None


class TestSystemRead:
    """Test SystemRead schema with subsystems"""

    def test_system_read_minimal(self):
        """Test creating system read"""
        sys = SystemRead(
            id=uuid4(),
            name="Platform",
            system_type=SystemTypes.PLATFORM,
            is_gps_enabled=False
        )
        assert sys.subsystems == []

    def test_system_read_with_subsystems(self):
        """Test system read with subsystems"""
        parent = SystemRead(
            id=uuid4(),
            name="Parent System",
            system_type=SystemTypes.PLATFORM,
            is_gps_enabled=False,
            subsystems=[
                SystemRead(
                    id=uuid4(),
                    name="Child 1",
                    system_type=SystemTypes.SENSOR,
                    is_gps_enabled=False
                ),
                SystemRead(
                    id=uuid4(),
                    name="Child 2",
                    system_type=SystemTypes.SENSOR,
                    is_gps_enabled=False
                )
            ]
        )
        assert len(parent.subsystems) == 2
        assert parent.subsystems[0].name == "Child 1"

    def test_system_read_json_serialization(self):
        """Test SystemRead can be serialized to JSON"""
        sys = SystemRead(
            id=uuid4(),
            name="Test System",
            system_type=SystemTypes.SENSOR,
            is_gps_enabled=False
        )
        
        json_data = sys.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test System" in json_data

    def test_system_read_all_system_types(self):
        """Test creating systems with each type"""
        for sys_type in [SystemTypes.SENSOR, SystemTypes.ACTUATOR, 
                         SystemTypes.PLATFORM, SystemTypes.SYSTEM, SystemTypes.CUSTOM]:
            sys = SystemRead(
                name=f"System {sys_type}",
                system_type=sys_type,
                is_gps_enabled=False
            )
            assert sys.system_type == sys_type


class TestSystemIntegration:
    """Integration tests for systems"""

    def test_system_workflow(self):
        """Test complete system creation workflow"""
        # Create parent system
        parent = SystemRead(
            id=uuid4(),
            name="Smart Home Hub",
            system_type=SystemTypes.PLATFORM,
            is_gps_enabled=False,
            description="Central hub for smart home",
            properties={"version": "2.0", "features": ["mqtt", "zigbee", "wifi"]}
        )
        
        # Create child sensors
        sensors = [
            SystemRead(
                id=uuid4(),
                name="Temperature Sensor",
                system_type=SystemTypes.SENSOR,
                is_gps_enabled=False,
                manufacturer="SensorCorp",
                model="SC-100"
            ),
            SystemRead(
                id=uuid4(),
                name="Motion Detector",
                system_type=SystemTypes.SENSOR,
                is_gps_enabled=False,
                properties={"detection_range": "10m"}
            )
        ]
        
        # Verify relationships
        assert parent.system_type == SystemTypes.PLATFORM
        assert all(s.system_type == SystemTypes.SENSOR for s in sensors)
        assert len(sensors) == 2

    def test_mobile_gps_systems(self):
        """Test creating mobile systems with GPS"""
        mobile_sys = SystemRead(
            name="Tracking Device",
            system_type=SystemTypes.SENSOR,
            is_mobile=True,
            is_gps_enabled=True,
            external_id="tracker-001"
        )
        
        assert mobile_sys.is_mobile is True
        assert mobile_sys.is_gps_enabled is True
        assert mobile_sys.external_id == "tracker-001"
