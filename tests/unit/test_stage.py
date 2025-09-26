"""Tests for Stage class and stage evaluation."""

import pytest

from stageflow.core import Stage
from stageflow.core.element import create_element
from stageflow.core.stage import StageResult
from stageflow.gates import Gate, Lock, LockType, GateResult
from stageflow.process.schema.core import FieldDefinition, ItemSchema


class TestStageResult:
    """Test StageResult data class."""

    def test_stage_result_initialization(self):
        """Test StageResult proper initialization."""
        result = StageResult(
            stage_name="test_stage",
            schema_valid=True,
            schema_errors=[],
            gate_results={},
            overall_passed=True,
            actions=["action1"],
            metadata={"key": "value"}
        )

        assert result.stage_name == "test_stage"
        assert result.schema_valid is True
        assert result.schema_errors == []
        assert result.gate_results == {}
        assert result.overall_passed is True
        assert result.actions == ["action1"]
        assert result.metadata == {"key": "value"}

    def test_has_failures_property(self):
        """Test has_failures property for different scenarios."""
        # No failures
        result = StageResult(
            stage_name="test",
            schema_valid=True,
            schema_errors=[],
            gate_results={},
            overall_passed=True,
            actions=[],
            metadata={}
        )
        assert not result.has_failures

        # Schema failure
        result = StageResult(
            stage_name="test",
            schema_valid=False,
            schema_errors=["error"],
            gate_results={},
            overall_passed=True,
            actions=[],
            metadata={}
        )
        assert result.has_failures

        # Overall failure
        result = StageResult(
            stage_name="test",
            schema_valid=True,
            schema_errors=[],
            gate_results={},
            overall_passed=False,
            actions=[],
            metadata={}
        )
        assert result.has_failures

    def test_passed_failed_gates_properties(self):
        """Test passed_gates and failed_gates properties."""
        gate_results = {
            "gate1": GateResult(
                passed=True,
                failed_components=(),
                passed_components=(),
                messages=(),
                actions=()
            ),
            "gate2": GateResult(
                passed=False,
                failed_components=(),
                passed_components=(),
                messages=(),
                actions=()
            ),
            "gate3": GateResult(
                passed=True,
                failed_components=(),
                passed_components=(),
                messages=(),
                actions=()
            )
        }

        result = StageResult(
            stage_name="test",
            schema_valid=True,
            schema_errors=[],
            gate_results=gate_results,
            overall_passed=True,
            actions=[],
            metadata={}
        )

        assert result.passed_gates == ["gate1", "gate3"]
        assert result.failed_gates == ["gate2"]


class TestStage:
    """Test Stage class functionality."""

    def test_stage_initialization_basic(self):
        """Test basic Stage initialization."""
        stage = Stage(name="test_stage")

        assert stage.name == "test_stage"
        assert stage.gates == []
        assert stage.schema is None
        assert stage.metadata == {}
        assert stage.allow_partial is False

    def test_stage_initialization_with_components(self):
        """Test Stage initialization with gates and schema."""
        # Create schema
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=25)
        }
        schema = ItemSchema(name="test_schema", fields=fields)

        # Create gates (AND gates require at least 2 components)
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.EXISTS, "age")
        gate1 = Gate.AND(lock1, lock2, name="validation_gate")

        # Create stage
        stage = Stage(
            name="test_stage",
            gates=[gate1],
            schema=schema,
            metadata={"version": "1.0"},
            allow_partial=True
        )

        assert stage.name == "test_stage"
        assert len(stage.gates) == 1
        assert stage.gates[0].name == "validation_gate"
        assert stage.schema == schema
        assert stage.metadata == {"version": "1.0"}
        assert stage.allow_partial is True

    def test_stage_initialization_validation_empty_name(self):
        """Test Stage initialization fails with empty name."""
        with pytest.raises(ValueError, match="Stage must have a name"):
            Stage(name="")

    def test_stage_initialization_validation_duplicate_gates(self):
        """Test Stage initialization fails with duplicate gate names."""
        lock1 = Lock(LockType.EXISTS, "prop1")
        lock2 = Lock(LockType.EXISTS, "prop2")
        dummy_lock1 = Lock(LockType.EXISTS, "dummy1")
        dummy_lock2 = Lock(LockType.EXISTS, "dummy2")

        gate1 = Gate.AND(lock1, dummy_lock1, name="duplicate_gate")
        gate2 = Gate.AND(lock2, dummy_lock2, name="duplicate_gate")

        with pytest.raises(ValueError, match="duplicate gate names"):
            Stage(name="test_stage", gates=[gate1, gate2])

    def test_evaluate_with_schema_only(self):
        """Test stage evaluation with schema only (no gates)."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=25)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        stage = Stage(name="schema_stage", schema=schema)

        # Valid element
        element = create_element({"name": "John", "age": 30})
        result = stage.evaluate(element)

        assert result.stage_name == "schema_stage"
        assert result.schema_valid is True
        assert result.schema_errors == []
        assert result.gate_results == {}
        assert result.overall_passed is True
        assert result.actions == []

    def test_evaluate_with_schema_failure(self):
        """Test stage evaluation with schema validation failure."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=True)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        stage = Stage(name="schema_stage", schema=schema)

        # Missing required field
        element = create_element({"name": "John"})
        result = stage.evaluate(element)

        assert result.stage_name == "schema_stage"
        assert result.schema_valid is False
        assert len(result.schema_errors) > 0
        assert result.overall_passed is False

    def test_evaluate_with_gates_only(self):
        """Test stage evaluation with gates only (no schema)."""
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.GREATER_THAN, "age", 18)

        gate1 = Gate.AND(lock1, lock2, name="validation_gate")
        stage = Stage(name="gate_stage", gates=[gate1])

        # Valid element
        element = create_element({"name": "John", "age": 25})
        result = stage.evaluate(element)

        assert result.stage_name == "gate_stage"
        assert result.schema_valid is True  # No schema means valid
        assert result.schema_errors == []
        assert len(result.gate_results) == 1
        assert result.gate_results["validation_gate"].passed is True
        assert result.overall_passed is True

    def test_evaluate_with_gate_failure(self):
        """Test stage evaluation with gate failure."""
        lock1 = Lock(LockType.GREATER_THAN, "age", 18)
        # Add a second lock to meet AND gate requirement
        lock2 = Lock(LockType.EXISTS, "name")
        gate1 = Gate.AND(lock1, lock2, name="age_gate")
        stage = Stage(name="gate_stage", gates=[gate1])

        # Invalid element (under age but has name)
        element = create_element({"name": "John", "age": 15})
        result = stage.evaluate(element)

        assert result.stage_name == "gate_stage"
        assert result.schema_valid is True
        assert result.gate_results["age_gate"].passed is False
        assert result.overall_passed is False

    def test_evaluate_with_partial_fulfillment(self):
        """Test stage evaluation with partial fulfillment allowed."""
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.EXISTS, "nonexistent")

        # Create dummy locks to satisfy AND gate requirements
        dummy_lock1 = Lock(LockType.EXISTS, "dummy1")
        dummy_lock2 = Lock(LockType.EXISTS, "dummy2")

        gate1 = Gate.AND(lock1, dummy_lock1, name="gate1")
        gate2 = Gate.AND(lock2, dummy_lock2, name="gate2")

        stage = Stage(name="partial_stage", gates=[gate1, gate2], allow_partial=True)

        element = create_element({"name": "John", "dummy1": "exists"})
        result = stage.evaluate(element)

        assert result.overall_passed is True  # Partial fulfillment allowed
        assert len(result.passed_gates) == 1
        assert len(result.failed_gates) == 1

    def test_evaluate_without_partial_fulfillment(self):
        """Test stage evaluation without partial fulfillment."""
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.EXISTS, "nonexistent")

        # Create dummy locks to satisfy AND gate requirements
        dummy_lock1 = Lock(LockType.EXISTS, "dummy1")
        dummy_lock2 = Lock(LockType.EXISTS, "dummy2")

        gate1 = Gate.AND(lock1, dummy_lock1, name="gate1")
        gate2 = Gate.AND(lock2, dummy_lock2, name="gate2")

        stage = Stage(name="strict_stage", gates=[gate1, gate2], allow_partial=False)

        element = create_element({"name": "John", "dummy1": "exists"})
        result = stage.evaluate(element)

        assert result.overall_passed is False  # All gates must pass
        assert len(result.passed_gates) == 1
        assert len(result.failed_gates) == 1

    def test_get_required_properties(self):
        """Test getting required properties from stage."""
        # Create schema with required fields
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False)
        }
        schema = ItemSchema(name="test_schema", fields=fields)

        # Create gates with property requirements
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.EXISTS, "email")
        gate1 = Gate.AND(lock1, lock2, name="gate1")

        stage = Stage(name="test_stage", gates=[gate1], schema=schema)

        required_props = stage.get_required_properties()

        # Should include properties from both schema and gates
        assert "name" in required_props
        assert "email" in required_props

    def test_has_gate(self):
        """Test has_gate method."""
        lock1 = Lock(LockType.EXISTS, "prop1")
        dummy_lock = Lock(LockType.EXISTS, "dummy")
        gate1 = Gate.AND(lock1, dummy_lock, name="test_gate")
        stage = Stage(name="test_stage", gates=[gate1])

        assert stage.has_gate("test_gate") is True
        assert stage.has_gate("nonexistent_gate") is False

    def test_get_gate(self):
        """Test get_gate method."""
        lock1 = Lock(LockType.EXISTS, "prop1")
        dummy_lock = Lock(LockType.EXISTS, "dummy")
        gate1 = Gate.AND(lock1, dummy_lock, name="test_gate")
        stage = Stage(name="test_stage", gates=[gate1])

        retrieved_gate = stage.get_gate("test_gate")
        assert retrieved_gate == gate1

        assert stage.get_gate("nonexistent_gate") is None

    def test_is_compatible_with_element(self):
        """Test is_compatible_with_element method."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=True)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        stage = Stage(name="test_stage", schema=schema)

        # Compatible element
        compatible_element = create_element({"name": "John", "age": 25})
        assert stage.is_compatible_with_element(compatible_element) is True

        # Incompatible element (missing required field)
        incompatible_element = create_element({"name": "John"})
        # The implementation checks if required fields exist via has_property
        # This should return False since age is missing
        assert stage.is_compatible_with_element(incompatible_element) is False

    def test_get_completion_percentage_no_gates(self):
        """Test completion percentage calculation with no gates."""
        # Stage with schema only
        fields = {"name": FieldDefinition(type_=str, required=True)}
        schema = ItemSchema(name="test_schema", fields=fields)
        stage = Stage(name="test_stage", schema=schema)

        # Valid element
        element = create_element({"name": "John"})
        percentage = stage.get_completion_percentage(element)
        assert percentage == 1.0

        # Stage with no schema and no gates
        empty_stage = Stage(name="empty_stage")
        percentage = empty_stage.get_completion_percentage(element)
        assert percentage == 1.0

    def test_get_completion_percentage_with_gates(self):
        """Test completion percentage calculation with gates."""
        lock1 = Lock(LockType.EXISTS, "name")
        lock2 = Lock(LockType.EXISTS, "age")

        # Create dummy locks to satisfy AND gate requirements
        dummy_lock1 = Lock(LockType.EXISTS, "dummy1")
        dummy_lock2 = Lock(LockType.EXISTS, "dummy2")

        gate1 = Gate.AND(lock1, dummy_lock1, name="gate1")
        gate2 = Gate.AND(lock2, dummy_lock2, name="gate2")

        stage = Stage(name="test_stage", gates=[gate1, gate2])

        # Element passes first gate only (has name and dummy1)
        element = create_element({"name": "John", "dummy1": "exists"})
        percentage = stage.get_completion_percentage(element)
        # Should be 0.75 (50% gates + 100% schema) / 2
        assert percentage == 0.75

    def test_get_summary(self):
        """Test get_summary method."""
        # Stage with no gates, no schema
        stage = Stage(name="empty_stage")
        summary = stage.get_summary()
        assert "empty_stage" in summary
        assert "no gates" in summary

        # Stage with gates and schema
        fields = {"name": FieldDefinition(type_=str, required=True)}
        schema = ItemSchema(name="test_schema", fields=fields)

        lock1 = Lock(LockType.EXISTS, "name")
        dummy_lock = Lock(LockType.EXISTS, "dummy")
        gate1 = Gate.AND(lock1, dummy_lock, name="gate1")

        stage = Stage(
            name="full_stage",
            gates=[gate1],
            schema=schema,
            allow_partial=True
        )

        summary = stage.get_summary()
        assert "full_stage" in summary
        assert "1 gate(s)" in summary
        assert "test_schema" in summary
        assert "partial fulfillment allowed" in summary

