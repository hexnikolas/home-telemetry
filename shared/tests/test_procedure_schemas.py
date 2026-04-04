import pytest
from uuid import uuid4
from pydantic import ValidationError
from schemas.procedure_schemas import ProcedureTypes, ProcedureBase, ProcedureWrite, ProcedureRead, ProcedureUpdate


class TestProcedureTypes:
    """Test ProcedureTypes enum"""

    def test_all_procedure_types(self):
        """Test all procedure type enums exist"""
        expected_types = [
            ProcedureTypes.DATA_COLLECTION,
            ProcedureTypes.DATA_PROCESSING,
            ProcedureTypes.SENSOR_CALIBRATION,
            ProcedureTypes.ACTUATOR_OPERATION,
            ProcedureTypes.MAINTENANCE,
            ProcedureTypes.SHUTDOWN,
            ProcedureTypes.STARTUP,
            ProcedureTypes.ALGORITHM_EXECUTION,
            ProcedureTypes.USER_DEFINED
        ]
        assert len(expected_types) == 9


class TestProcedureBase:
    """Test ProcedureBase schema"""

    def test_procedure_base_minimal(self):
        """Test creating procedure with required fields"""
        proc = ProcedureBase(
            name="Data Collection",
            procedure_type=ProcedureTypes.DATA_COLLECTION
        )
        assert proc.name == "Data Collection"
        assert proc.procedure_type == ProcedureTypes.DATA_COLLECTION

    def test_procedure_base_with_description(self):
        """Test procedure with description"""
        proc = ProcedureBase(
            name="Setup",
            procedure_type=ProcedureTypes.STARTUP,
            description="Initial sensor setup"
        )
        assert proc.description == "Initial sensor setup"

    def test_procedure_base_with_steps(self):
        """Test procedure with steps"""
        steps = [
            "Connect to power",
            "Wait for warmup",
            "Run diagnostics"
        ]
        proc = ProcedureBase(
            name="Startup Procedure",
            procedure_type=ProcedureTypes.STARTUP,
            steps=steps
        )
        assert len(proc.steps) == 3
        assert proc.steps[0] == "Connect to power"

    def test_procedure_base_with_reference(self):
        """Test procedure with reference URL"""
        proc = ProcedureBase(
            name="Procedure",
            procedure_type=ProcedureTypes.SENSOR_CALIBRATION,
            reference="https://example.com/procedures/cal-001"
        )
        assert proc.reference == "https://example.com/procedures/cal-001"

    def test_procedure_base_with_properties(self):
        """Test procedure with custom properties"""
        props = {"duration_minutes": 30, "requires_approval": True}
        proc = ProcedureBase(
            name="Maintenance",
            procedure_type=ProcedureTypes.MAINTENANCE,
            properties=props
        )
        assert proc.properties["duration_minutes"] == 30
        assert proc.properties["requires_approval"] is True

    def test_procedure_base_all_types(self):
        """Test creating procedures with each type"""
        for proc_type in [
            ProcedureTypes.DATA_COLLECTION,
            ProcedureTypes.DATA_PROCESSING,
            ProcedureTypes.SENSOR_CALIBRATION,
            ProcedureTypes.ACTUATOR_OPERATION,
            ProcedureTypes.MAINTENANCE,
            ProcedureTypes.SHUTDOWN,
            ProcedureTypes.STARTUP,
            ProcedureTypes.ALGORITHM_EXECUTION,
            ProcedureTypes.USER_DEFINED
        ]:
            proc = ProcedureBase(
                name=f"Procedure {proc_type.value}",
                procedure_type=proc_type
            )
            assert proc.procedure_type == proc_type

    def test_procedure_base_missing_name_fails(self):
        """Test that missing name raises validation error"""
        with pytest.raises(ValidationError):
            ProcedureBase(procedure_type=ProcedureTypes.DATA_COLLECTION)

    def test_procedure_base_missing_type_fails(self):
        """Test that missing procedure_type raises validation error"""
        with pytest.raises(ValidationError):
            ProcedureBase(name="Procedure")

    def test_procedure_base_invalid_type_fails(self):
        """Test that invalid procedure type raises validation error"""
        with pytest.raises(ValidationError):
            ProcedureBase(
                name="Procedure",
                procedure_type="INVALID_TYPE"
            )


class TestProcedureRead:
    """Test ProcedureRead schema"""

    def test_procedure_read_full(self):
        """Test creating complete procedure read"""
        proc_id = uuid4()
        proc = ProcedureRead(
            id=proc_id,
            name="Data Collection",
            procedure_type=ProcedureTypes.DATA_COLLECTION,
            description="Standard data collection procedure",
            steps=["Step 1", "Step 2"]
        )
        assert proc.id == proc_id
        assert proc.name == "Data Collection"

    def test_procedure_read_without_id(self):
        """Test procedure read without ID"""
        proc = ProcedureRead(
            name="Shutdown",
            procedure_type=ProcedureTypes.SHUTDOWN
        )
        assert proc.id is None


class TestProcedureUpdate:
    """Test ProcedureUpdate schema"""

    def test_procedure_update_empty(self):
        """Test empty procedure update"""
        proc = ProcedureUpdate()
        assert proc.name is None
        assert proc.procedure_type is None

    def test_procedure_update_name(self):
        """Test updating name"""
        proc = ProcedureUpdate(name="Updated Name")
        assert proc.name == "Updated Name"

    def test_procedure_update_type(self):
        """Test updating type"""
        proc = ProcedureUpdate(procedure_type=ProcedureTypes.MAINTENANCE)
        assert proc.procedure_type == ProcedureTypes.MAINTENANCE

