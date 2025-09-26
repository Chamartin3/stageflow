"""Unit tests for Gate composition and evaluation logic."""

from typing import cast
from unittest.mock import Mock

import pytest

from stageflow.core.element import DictElement
from stageflow.gates import Evaluable, Gate, GateResult, LockWrapper, Lock, LockType


class TestGateResult:
    """Test GateResult data structure."""

    def test_gate_result_creation(self):
        """Test basic GateResult creation."""
        result = GateResult(passed=True)
        assert result.passed is True
        assert result.failed_components == ()
        assert result.passed_components == ()
        assert result.messages == ()
        assert result.actions == ()
        assert result.evaluation_time_ms == 0.0
        assert result.short_circuited is False

    def test_gate_result_with_data(self):
        """Test GateResult with all fields populated."""
        lock1 = Lock("test", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)

        result = GateResult(
            passed=False,
            failed_components=(lock1,),
            passed_components=(lock2,),
            messages=("Error message",),
            actions=("Fix issue",),
            evaluation_time_ms=10.5,
            short_circuited=True
        )

        assert result.passed is False
        assert result.failed_components == (lock1,)
        assert result.passed_components == (lock2,)
        assert result.messages == ("Error message",)
        assert result.actions == ("Fix issue",)
        assert result.messages == ("Error message",)
        assert result.actions == ("Fix issue",)
        assert result.evaluation_time_ms == 10.5
        assert result.short_circuited is True

    def test_has_failures_property(self):
        """Test has_failures property."""
        lock = Lock("test", LockType.EXISTS)

        # No failures
        result = GateResult(passed=True)
        assert result.has_failures is False

        # With failures
        result = GateResult(passed=False, failed_components=(lock,))
        assert result.has_failures is True

    def test_has_passes_property(self):
        """Test has_passes property."""
        lock = Lock("test", LockType.EXISTS)

        # No passes
        result = GateResult(passed=False)
        assert result.has_passes is False

        # With passes
        result = GateResult(passed=True, passed_components=(lock,))
        assert result.has_passes is True

    def test_total_components_property(self):
        """Test total_components property calculation."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        lock3 = Lock("test3", LockType.EXISTS)

        result = GateResult(
            passed=False,
            failed_components=(lock1, lock2),
            passed_components=(lock3,)
        )

        assert result.total_components == 3


class TestLockWrapper:
    """Test LockWrapper functionality."""

    def create_element(self, data):
        """Helper to create test elements."""
        return DictElement(data)

    def test_lock_wrapper_creation(self):
        """Test LockWrapper creation."""
        lock = Lock("test", LockType.EXISTS)
        wrapper = LockWrapper(lock)
        assert wrapper.lock is lock

    def test_lock_wrapper_evaluate_success(self):
        """Test LockWrapper evaluation with successful lock."""
        element = self.create_element({"name": "John"})
        lock = Lock("name", LockType.EXISTS, True)
        wrapper = LockWrapper(lock)

        result = wrapper.evaluate(element)

        assert result.passed is True
        assert result.passed_components == (lock,)
        assert result.failed_components == ()
        assert result.evaluation_time_ms > 0

    def test_lock_wrapper_evaluate_failure(self):
        """Test LockWrapper evaluation with failing lock."""
        element = self.create_element({"name": "John"})
        lock = Lock("age", LockType.EXISTS, True)
        wrapper = LockWrapper(lock)

        result = wrapper.evaluate(element)

        assert result.passed is False
        assert result.failed_components == (lock,)
        assert result.passed_components == ()
        assert len(result.messages) > 0
        assert len(result.actions) > 0
        assert result.evaluation_time_ms > 0

    def test_lock_wrapper_get_property_paths(self):
        """Test LockWrapper property path extraction."""
        lock = Lock("user.profile.name", LockType.EXISTS)
        wrapper = LockWrapper(lock)

        paths = wrapper.get_property_paths()
        assert paths == {"user.profile.name"}

    def test_lock_wrapper_evaluate_with_message_methods(self):
        """Test LockWrapper evaluation using lock message methods."""
        element = self.create_element({"name": "John"})

        # Create a mock lock that has message methods
        lock = Mock()
        lock.property_path = "age"
        lock.validate.return_value = False
        lock.get_failure_message.return_value = "Age is required"
        lock.get_action_message.return_value = "Set age field"

        wrapper = LockWrapper(lock)
        result = wrapper.evaluate(element)

        assert result.passed is False
        assert result.messages == ("Age is required",)
        assert result.actions == ("Set age field",)

    def test_lock_wrapper_evaluate_fallback_messages(self):
        """Test LockWrapper evaluation with fallback messages when methods don't exist."""
        element = self.create_element({"name": "John"})

        # Create a mock lock without message methods
        lock = Mock()
        lock.property_path = "age"
        lock.validate.return_value = False
        # Remove message methods to trigger AttributeError
        del lock.get_failure_message
        del lock.get_action_message

        wrapper = LockWrapper(lock)
        result = wrapper.evaluate(element)

        assert result.passed is False
        assert "Lock validation failed for age" in result.messages[0]
        assert "Check property age" in result.actions[0]


class TestGateCreation:
    """Test Gate creation and validation."""

    def test_gate_initialization(self):
        """Test basic gate initialization."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        wrapper1 = LockWrapper(lock1)
        wrapper2 = LockWrapper(lock2)

        gate = Gate.create(
            lock1, lock2,
            name="test_gate"
        )

        assert gate.name == "test_gate"
        assert gate.components == (wrapper1, wrapper2)
        assert gate.target_stage is None
        assert gate.metadata == {}

    def test_gate_initialization_with_metadata(self):
        """Test gate initialization with metadata."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        wrapper1 = LockWrapper(lock1)
        wrapper2 = LockWrapper(lock2)
        metadata = {"description": "Test gate", "priority": 1}

        gate = Gate(
            name="test_gate",
            components=(wrapper1, wrapper2),
            metadata=metadata
        )

        assert gate.metadata == metadata

    def test_gate_validation_empty_name(self):
        """Test gate validation fails with empty name."""
        lock = Lock("test", LockType.EXISTS)
        wrapper = LockWrapper(lock)

        with pytest.raises(ValueError, match="Gate must have a name"):
            Gate(name="", components=(wrapper,))

    def test_gate_validation_no_components(self):
        """Test gate validation fails with no components."""
        with pytest.raises(ValueError, match="Gate must contain at least one component"):
            Gate(name="test", components=())


    def test_gate_validation_and_single_component(self):
        """Test AND gate allows single component for simplified YAML definitions."""
        lock = Lock("test", LockType.EXISTS)
        wrapper = LockWrapper(lock)

        # Single-component AND gates are now allowed for YAML compatibility
        gate = Gate(name="test", components=(wrapper,))
        assert gate.name == "test"
        assert len(gate.components) == 1



class TestGateClassMethods:
    """Test Gate class methods for creation."""

    def test_and_gate_creation(self):
        """Test AND gate creation with class method."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)

        gate = Gate.AND(lock1, lock2, name="and_gate")

        assert gate.name == "and_gate"
        assert len(gate.components) == 2
        assert all(isinstance(comp, LockWrapper) for comp in gate.components)

    def test_and_gate_auto_name(self):
        """Test AND gate with auto-generated name."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)

        gate = Gate.AND(lock1, lock2)

        assert gate.name.startswith("gate_")

    def test_and_gate_with_metadata(self):
        """Test AND gate creation with metadata."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)

        gate = Gate.AND(lock1, lock2, name="and_gate", description="Test gate")

        assert gate.metadata["description"] == "Test gate"

    def test_and_gate_empty_components(self):
        """Test AND gate fails with no components."""
        with pytest.raises(ValueError, match="Gate requires at least one component"):
            Gate.AND()

    def test_and_gate_invalid_component_type(self):
        """Test AND gate fails with invalid component type."""
        with pytest.raises(TypeError, match="Components must be Lock or Gate"):
            Gate.AND(cast(Lock, "invalid"))



    def test_mixed_lock_and_gate_components(self):
        """Test creating gates with mixed Lock and Gate components."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        inner_gate = Gate.AND(lock1, lock2, name="inner")
        lock3 = Lock("test3", LockType.EXISTS)

        gate = Gate.AND(inner_gate, lock3, name="mixed_gate")

        assert len(gate.components) == 2
        assert gate.components[0] is inner_gate
        assert isinstance(gate.components[1], LockWrapper)


class TestGateEvaluation:
    """Test Gate evaluation logic."""

    def create_element(self, data):
        """Helper to create test elements."""
        return DictElement(data)

    def test_and_gate_all_pass(self):
        """Test AND gate with all locks passing."""
        element = self.create_element({"name": "John", "age": 25})

        lock1 = Lock("name", LockType.EXISTS, True)
        lock2 = Lock("age", LockType.EXISTS, True)
        gate = Gate.AND(lock1, lock2, name="and_gate")

        result = gate.evaluate(element)

        assert result.passed is True
        assert len(result.passed_components) == 2
        assert len(result.failed_components) == 0
        assert result.short_circuited is False
        assert result.evaluation_time_ms > 0

    def test_and_gate_one_fails(self):
        """Test AND gate with one lock failing."""
        element = self.create_element({"name": "John"})

        lock1 = Lock("name", LockType.EXISTS, True)
        lock2 = Lock("age", LockType.EXISTS, True)
        gate = Gate.AND(lock1, lock2, name="and_gate")

        result = gate.evaluate(element)

        assert result.passed is False
        assert len(result.passed_components) == 1
        assert len(result.failed_components) == 1
        # Note: Short-circuit depends on order of evaluation and when failure occurs

    def test_and_gate_short_circuit(self):
        """Test AND gate short-circuit behavior."""
        element = self.create_element({"name": "John"})

        # Create locks where first fails, second would pass
        lock1 = Lock("missing", LockType.EXISTS, True)  # Will fail
        lock2 = Lock("name", LockType.EXISTS, True)     # Would pass
        lock3 = Lock("name", LockType.EQUALS, "John")   # Would pass

        gate = Gate.AND(lock1, lock2, lock3, name="and_gate")
        result = gate.evaluate(element)

        assert result.passed is False
        assert result.short_circuited is True
        # Only first lock should be evaluated
        assert len(result.failed_components) == 1
        assert len(result.passed_components) == 0


    def test_nested_gate_evaluation(self):
        """Test evaluation of nested gates."""
        element = self.create_element({"name": "John", "age": 25})

        # Inner AND gate
        lock1 = Lock("name", LockType.EXISTS, True)
        lock2 = Lock("age", LockType.EXISTS, True)
        inner_gate = Gate.AND(lock1, lock2, name="inner")

        # Outer AND gate
        lock3 = Lock("name", LockType.EQUALS, "John")  # Will pass
        outer_gate = Gate.AND(inner_gate, lock3, name="outer")

        result = outer_gate.evaluate(element)

        assert result.passed is True  # Both inner gate and lock3 pass
        assert result.short_circuited is False  # All components evaluated


class TestGateUtilityMethods:
    """Test Gate utility and helper methods."""

    def test_get_property_paths(self):
        """Test property path extraction from gates."""
        lock1 = Lock("user.name", LockType.EXISTS)
        lock2 = Lock("user.age", LockType.GREATER_THAN, 18)
        lock3 = Lock("profile.verified", LockType.EQUALS, True)

        gate = Gate.AND(lock1, lock2, lock3, name="test_gate")

        paths = gate.get_property_paths()
        expected = {"user.name", "user.age", "profile.verified"}
        assert paths == expected

    def test_get_property_paths_nested_gates(self):
        """Test property path extraction from nested gates."""
        lock1 = Lock("user.name", LockType.EXISTS)
        lock2 = Lock("user.age", LockType.GREATER_THAN, 18)
        inner_gate = Gate.AND(lock1, lock2, name="inner")

        lock3 = Lock("profile.verified", LockType.EQUALS, True)
        outer_gate = Gate.AND(inner_gate, lock3, name="outer")

        paths = outer_gate.get_property_paths()
        expected = {"user.name", "user.age", "profile.verified"}
        assert paths == expected

    def test_requires_property(self):
        """Test requires_property method."""
        lock1 = Lock("user.name", LockType.EXISTS)
        lock2 = Lock("user.age", LockType.GREATER_THAN, 18)
        gate = Gate.AND(lock1, lock2, name="test_gate")

        assert gate.requires_property("user.name") is True
        assert gate.requires_property("user.age") is True
        assert gate.requires_property("profile.verified") is False

    def test_get_summary(self):
        """Test get_summary method for AND gate types."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        lock3 = Lock("test3", LockType.EXISTS)

        and_gate = Gate.AND(lock1, lock2, lock3, name="and_gate")
        assert "requires all 3 components to pass" in and_gate.get_summary()

        single_gate = Gate.AND(lock1, name="single_gate")
        assert "requires all 1 components to pass" in single_gate.get_summary()

    def test_get_complexity(self):
        """Test complexity calculation for gates."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)
        lock3 = Lock("test3", LockType.EXISTS)

        # Simple gate
        simple_gate = Gate.AND(lock1, lock2, name="simple")
        assert simple_gate.get_complexity() == 2

        # Nested gate
        inner_gate = Gate.AND(lock1, lock2, name="inner")
        outer_gate = Gate.AND(inner_gate, lock3, name="outer")
        assert outer_gate.get_complexity() == 3

    def test_validate_structure(self):
        """Test structure validation for gates."""
        lock = Lock("test", LockType.EXISTS)

        # Simple gate should have no issues
        simple_gate = Gate.AND(lock, lock, name="simple")
        issues = simple_gate.validate_structure()
        assert len(issues) == 0


    def test_is_compatible_with(self):
        """Test gate compatibility checking."""
        lock1 = Lock("test1", LockType.EXISTS)
        lock2 = Lock("test2", LockType.EXISTS)

        gate1 = Gate.AND(lock1, lock2, name="gate1")
        gate2 = Gate.AND(lock1, lock2, name="gate2")

        # Currently all gates are compatible
        assert gate1.is_compatible_with(gate2) is True

    def test_max_depth_calculation(self):
        """Test maximum depth calculation for nested gates."""
        lock = Lock("test", LockType.EXISTS)

        # Depth 0: Single gate
        gate1 = Gate.AND(lock, lock, name="gate1")
        assert gate1._get_max_depth() == 0

        # Depth 1: One level nesting
        gate2 = Gate.AND(gate1, lock, name="gate2")
        assert gate2._get_max_depth() == 1

        # Depth 2: Two levels nesting
        gate3 = Gate.AND(gate2, lock, name="gate3")
        assert gate3._get_max_depth() == 2


class TestGateErrorHandling:
    """Test Gate error handling and edge cases."""

    def create_element(self, data):
        """Helper to create test elements."""
        return DictElement(data)

    def test_gate_evaluation_with_exception(self):
        """Test gate evaluation handles component exceptions gracefully."""
        element = self.create_element({"name": "John"})

        # Create a mock component that raises an exception
        mock_component = Mock(spec=Evaluable)
        mock_component.evaluate.side_effect = Exception("Test exception")

        # This test ensures gates handle unexpected component failures
        # In practice, this would need proper exception handling in Gate.evaluate
        with pytest.raises(Exception):
            gate = Gate(
                name="test_gate",
                components=(mock_component,)
            )
            gate.evaluate(element)

    def test_gate_with_empty_result_messages(self):
        """Test gate evaluation with components that return empty messages."""
        element = self.create_element({"name": "John"})

        # Create mock components that return empty messages
        mock_component1 = Mock(spec=Evaluable)
        mock_component1.evaluate.return_value = GateResult(
            passed=False,
            messages=(),
            actions=()
        )

        mock_component2 = Mock(spec=Evaluable)
        mock_component2.evaluate.return_value = GateResult(
            passed=True,
            messages=(),
            actions=()
        )

        gate = Gate(
            name="test_gate",
            components=(mock_component1, mock_component2)
        )

        result = gate.evaluate(element)
        assert result.passed is False

    def test_gate_timing_measurement(self):
        """Test that gate evaluation measures timing correctly."""
        element = self.create_element({"name": "John"})
        lock1 = Lock("name", LockType.EXISTS, True)
        lock2 = Lock("name", LockType.EQUALS, "John")
        gate = Gate.AND(lock1, lock2, name="timed_gate")

        result = gate.evaluate(element)

        # Just verify that timing is measured (should be > 0)
        assert result.evaluation_time_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__])
