"""Unit tests for pydantic schema validation models."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError as PydanticValidationError

from stageflow.process.schema.models import (
    FieldDefinitionModel,
    GateModel,
    ItemSchemaModel,
    LockModel,
    ProcessModel,
    StageFlowSchemaModel,
    StageModel,
    ValidationContext,
    validate_process_definition,
    validate_stageflow_schema,
)


class TestFieldDefinitionModel:
    """Test FieldDefinitionModel validation."""

    def test_valid_field_definition(self):
        """Test valid field definition creation."""
        field_def = FieldDefinitionModel(
            type="string",
            required=True,
            min_length=1,
            max_length=100,
            pattern=r"^[a-zA-Z]+$"
        )
        assert field_def.type == "string"
        assert field_def.required is True
        assert field_def.min_length == 1
        assert field_def.max_length == 100
        assert field_def.pattern == r"^[a-zA-Z]+$"

    def test_numeric_field_constraints(self):
        """Test numeric field with min/max values."""
        field_def = FieldDefinitionModel(
            type="number",
            min_value=0.0,
            max_value=100.0,
            default=50.0
        )
        assert field_def.min_value == 0.0
        assert field_def.max_value == 100.0
        assert field_def.default == 50.0

    def test_invalid_regex_pattern(self):
        """Test validation of invalid regex pattern."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FieldDefinitionModel(type="string", pattern="[invalid")

        assert "Invalid regex pattern" in str(exc_info.value)

    def test_invalid_constraints_for_type(self):
        """Test that type-incompatible constraints are rejected."""
        # String type with numeric constraints
        with pytest.raises(PydanticValidationError) as exc_info:
            FieldDefinitionModel(type="string", min_value=10)

        assert "Numeric constraints not allowed for type 'string'" in str(exc_info.value)

        # Number type with pattern constraint
        with pytest.raises(PydanticValidationError) as exc_info:
            FieldDefinitionModel(type="number", pattern="test")

        assert "Pattern constraint not allowed for type 'number'" in str(exc_info.value)

    def test_min_max_value_relationship(self):
        """Test that min_value cannot be greater than max_value."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FieldDefinitionModel(type="number", min_value=100, max_value=50)

        assert "min_value (100) cannot be greater than max_value (50)" in str(exc_info.value)

    def test_min_max_length_relationship(self):
        """Test that min_length cannot be greater than max_length."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FieldDefinitionModel(type="string", min_length=10, max_length=5)

        assert "min_length (10) cannot be greater than max_length (5)" in str(exc_info.value)


class TestItemSchemaModel:
    """Test ItemSchemaModel validation."""

    def test_valid_item_schema(self):
        """Test valid item schema creation."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["name", "email"],
            optional_fields=["age", "city"],
            field_types={"name": "string", "email": "string", "age": "integer"},
            default_values={"age": 18}
        )
        assert schema.name == "test_schema"
        assert "name" in schema.required_fields
        assert "age" in schema.optional_fields

    def test_invalid_field_paths(self):
        """Test validation of invalid field paths."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ItemSchemaModel(
                name="test",
                required_fields=["", "..invalid", "valid"]
            )

        error_str = str(exc_info.value)
        assert "Invalid field path" in error_str

    def test_invalid_field_types(self):
        """Test validation of invalid field types."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ItemSchemaModel(
                name="test",
                field_types={"name": "invalid_type"}
            )

        assert "Invalid type 'invalid_type'" in str(exc_info.value)

    def test_overlapping_required_optional_fields(self):
        """Test that fields cannot be both required and optional."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ItemSchemaModel(
                name="test",
                required_fields=["name"],
                optional_fields=["name"]
            )

        assert "Fields cannot be both required and optional" in str(exc_info.value)

    def test_default_values_for_required_fields(self):
        """Test that default values are not allowed for required fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ItemSchemaModel(
                name="test",
                required_fields=["name"],
                default_values={"name": "default"}
            )

        assert "Default values provided for non-optional fields" in str(exc_info.value)

    def test_field_definitions_consistency(self):
        """Test consistency between field_definitions and legacy fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ItemSchemaModel(
                name="test",
                required_fields=["name"],
                field_definitions={
                    "name": FieldDefinitionModel(type="string", required=False)
                }
            )

        assert "marked as optional in definition but listed as required" in str(exc_info.value)


class TestLockModel:
    """Test LockModel validation."""

    def test_valid_lock(self):
        """Test valid lock creation."""
        lock = LockModel(
            name="test_lock",
            type="EXISTS",
            property="user.name"
        )
        assert lock.name == "test_lock"
        assert lock.type == "EXISTS"
        assert lock.property == "user.name"

    def test_lock_with_benchmark(self):
        """Test lock with benchmark value."""
        lock = LockModel(
            name="equals_lock",
            type="EQUALS",
            property="status",
            benchmark="active"
        )
        assert lock.benchmark == "active"

    def test_invalid_property_path(self):
        """Test validation of invalid property paths."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LockModel(
                name="test",
                type="EXISTS",
                property="..invalid"
            )

        assert "Invalid property path format" in str(exc_info.value)

    def test_empty_property_path(self):
        """Test that empty property paths are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LockModel(
                name="test",
                type="EXISTS",
                property=""
            )

        assert "Property path cannot be empty" in str(exc_info.value)

    def test_lock_type_benchmark_requirements(self):
        """Test that certain lock types require benchmarks."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LockModel(
                name="equals_without_benchmark",
                type="EQUALS",
                property="field"
            )

        assert "Lock type 'EQUALS' requires a benchmark value" in str(exc_info.value)


class TestGateModel:
    """Test GateModel validation."""

    def test_valid_gate(self):
        """Test valid gate creation."""
        lock1 = LockModel(name="lock1", type="EXISTS", property="field1")
        lock2 = LockModel(name="lock2", type="EXISTS", property="field2")

        gate = GateModel(
            name="test_gate",
            locks=[lock1, lock2],
            target_stage="next_stage"
        )

        assert gate.name == "test_gate"
        assert len(gate.locks) == 2

    def test_duplicate_lock_names(self):
        """Test that duplicate lock names in a gate are rejected."""
        lock1 = LockModel(name="duplicate", type="EXISTS", property="field1")
        lock2 = LockModel(name="duplicate", type="EXISTS", property="field2")

        with pytest.raises(PydanticValidationError) as exc_info:
            GateModel(
                name="test_gate",
                locks=[lock1, lock2]
            )

        assert "Duplicate lock names in gate" in str(exc_info.value)

    def test_empty_locks_list(self):
        """Test that gates must have at least one lock."""
        with pytest.raises(PydanticValidationError) as exc_info:
            GateModel(
                name="empty_gate",
                locks=[]
            )

        assert "at least 1 item" in str(exc_info.value).lower()


class TestStageModel:
    """Test StageModel validation."""

    def test_valid_stage(self):
        """Test valid stage creation."""
        lock = LockModel(name="lock1", type="EXISTS", property="field1")
        gate = GateModel(name="gate1", locks=[lock])
        schema = ItemSchemaModel(name="stage_schema", required_fields=["field1"])

        stage = StageModel(
            name="test_stage",
            gates=[gate],
            schema=schema,
            allow_partial=True
        )

        assert stage.name == "test_stage"
        assert len(stage.gates) == 1
        assert stage.schema.name == "stage_schema"

    def test_duplicate_gate_names(self):
        """Test that duplicate gate names in a stage are rejected."""
        lock = LockModel(name="lock1", type="EXISTS", property="field1")
        gate1 = GateModel(name="duplicate", locks=[lock])
        gate2 = GateModel(name="duplicate", locks=[lock])

        with pytest.raises(PydanticValidationError) as exc_info:
            StageModel(
                name="test_stage",
                gates=[gate1, gate2]
            )

        assert "Duplicate gate names in stage" in str(exc_info.value)

    def test_expected_schema_alias(self):
        """Test that expected_schema alias works correctly."""
        schema = ItemSchemaModel(name="test_schema", required_fields=["field1"])

        stage = StageModel(
            name="test_stage",
            expected_schema=schema
        )

        assert stage.schema == schema
        assert stage.expected_schema == schema

    def test_conflicting_schema_fields(self):
        """Test that schema and expected_schema cannot conflict."""
        schema1 = ItemSchemaModel(name="schema1", required_fields=["field1"])
        schema2 = ItemSchemaModel(name="schema2", required_fields=["field2"])

        with pytest.raises(PydanticValidationError) as exc_info:
            StageModel(
                name="test_stage",
                schema=schema1,
                expected_schema=schema2
            )

        assert "Cannot specify both 'schema' and 'expected_schema'" in str(exc_info.value)


class TestProcessModel:
    """Test ProcessModel validation."""

    def test_valid_process(self):
        """Test valid process creation."""
        lock = LockModel(name="lock1", type="EXISTS", property="field1")
        gate = GateModel(name="gate1", locks=[lock])
        stage = StageModel(name="stage1", gates=[gate])

        process = ProcessModel(
            name="test_process",
            stages=[stage],
            initial_stage="stage1",
            final_stage="stage1"
        )

        assert process.name == "test_process"
        assert len(process.stages) == 1
        assert process.stage_count == 1
        assert process.total_gates == 1
        assert process.total_locks == 1

    def test_duplicate_stage_names(self):
        """Test that duplicate stage names are rejected."""
        stage1 = StageModel(name="duplicate", gates=[])
        stage2 = StageModel(name="duplicate", gates=[])

        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test_process",
                stages=[stage1, stage2]
            )

        assert "Duplicate stage names in process" in str(exc_info.value)

    def test_empty_stages_list(self):
        """Test that processes must have at least one stage."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="empty_process",
                stages=[]
            )

        assert "Process must contain at least one stage" in str(exc_info.value)

    def test_stage_order_validation(self):
        """Test stage_order validation."""
        stage1 = StageModel(name="stage1", gates=[])
        stage2 = StageModel(name="stage2", gates=[])

        # Missing stage in order
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test_process",
                stages=[stage1, stage2],
                stage_order=["stage1"]
            )

        assert "Stages missing from stage_order" in str(exc_info.value)

        # Extra stage in order
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test_process",
                stages=[stage1],
                stage_order=["stage1", "nonexistent"]
            )

        assert "stage_order contains non-existent stages" in str(exc_info.value)

    def test_initial_stage_reference(self):
        """Test that initial_stage must reference existing stage."""
        stage = StageModel(name="stage1", gates=[])

        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test_process",
                stages=[stage],
                initial_stage="nonexistent"
            )

        assert "initial_stage 'nonexistent' does not exist in stages" in str(exc_info.value)

    def test_gate_target_stage_references(self):
        """Test that gate target_stage references are validated."""
        lock = LockModel(name="lock1", type="EXISTS", property="field1")
        gate = GateModel(name="gate1", locks=[lock], target_stage="nonexistent")
        stage = StageModel(name="stage1", gates=[gate])

        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test_process",
                stages=[stage]
            )

        assert "references non-existent target_stage 'nonexistent'" in str(exc_info.value)

    def test_auto_generated_stage_order(self):
        """Test that stage_order is auto-generated when not provided."""
        stage1 = StageModel(name="stage1", gates=[])
        stage2 = StageModel(name="stage2", gates=[])

        process = ProcessModel(
            name="test_process",
            stages=[stage1, stage2]
        )

        assert process.stage_order == ["stage1", "stage2"]


class TestStageFlowSchemaModel:
    """Test StageFlowSchemaModel validation."""

    def test_valid_stageflow_schema(self):
        """Test valid complete schema creation."""
        stage = StageModel(name="stage1", gates=[])
        process = ProcessModel(name="test_process", stages=[stage])

        schema = StageFlowSchemaModel(
            version="1.0",
            process=process,
            created_by="test_user"
        )

        assert schema.version == "1.0"
        assert schema.process.name == "test_process"
        assert schema.created_by == "test_user"
        assert isinstance(schema.created_at, datetime)
        assert isinstance(schema.schema_id, UUID)

    def test_invalid_version_format(self):
        """Test validation of invalid version format."""
        stage = StageModel(name="stage1", gates=[])
        process = ProcessModel(name="test_process", stages=[stage])

        with pytest.raises(PydanticValidationError) as exc_info:
            StageFlowSchemaModel(
                version="invalid",
                process=process
            )

        assert "Invalid version format" in str(exc_info.value)


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_stageflow_schema_function(self):
        """Test validate_stageflow_schema function."""
        data = {
            "version": "1.0",
            "process": {
                "name": "test_process",
                "stages": [
                    {
                        "name": "stage1",
                        "gates": [
                            {
                                "name": "gate1",
                                "locks": [
                                    {
                                        "name": "lock1",
                                        "type": "EXISTS",
                                        "property": "field1"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        result = validate_stageflow_schema(data)
        assert isinstance(result, StageFlowSchemaModel)
        assert result.process.name == "test_process"

    def test_validate_process_definition_function(self):
        """Test validate_process_definition function."""
        data = {
            "name": "test_process",
            "stages": [
                {
                    "name": "stage1",
                    "gates": []
                }
            ]
        }

        result = validate_process_definition(data)
        assert isinstance(result, ProcessModel)
        assert result.name == "test_process"

    def test_validation_context_warnings(self):
        """Test ValidationContext warning collection."""
        context = ValidationContext()
        context.push_path("process")
        context.push_path("stages")
        context.add_warning("Test warning message")

        assert len(context.warnings) == 1
        assert "process.stages: Test warning message" in context.warnings[0]

    def test_validation_with_process_data_only(self):
        """Test validation when only process data is provided."""
        process_data = {
            "name": "test_process",
            "stages": [
                {
                    "name": "stage1",
                    "gates": []
                }
            ]
        }

        # Should wrap in process field automatically
        result = validate_stageflow_schema(process_data)
        assert result.process.name == "test_process"


class TestValidationErrorMessages:
    """Test that validation provides helpful error messages."""

    def test_missing_required_fields(self):
        """Test error messages for missing required fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(stages=[])

        error_str = str(exc_info.value)
        assert "name" in error_str.lower()
        assert "required" in error_str.lower()

    def test_field_validation_errors(self):
        """Test field-specific validation error messages."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="",  # Empty name
                stages=[]
            )

        error_str = str(exc_info.value)
        assert "at least 1 character" in error_str.lower()

    def test_nested_validation_errors(self):
        """Test that nested validation errors are properly reported."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ProcessModel(
                name="test",
                stages=[
                    {
                        "name": "",  # Invalid nested field
                        "gates": []
                    }
                ]
            )

        error_str = str(exc_info.value)
        assert "stages.0.name" in error_str or "name" in error_str
