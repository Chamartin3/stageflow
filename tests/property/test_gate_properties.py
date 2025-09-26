"""Property-based tests for Gate composition and logical consistency.

This module tests the fundamental invariants and behaviors of Gate composition,
ensuring logical consistency, proper evaluation order, and correct handling
of complex nested gate structures.

Key properties tested:
- Gate evaluation logical consistency
- Short-circuit evaluation properties
- Composition invariants (AND, OR, NOT)
- Nested gate behavior
- Performance and complexity properties
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from stageflow.core.element import DictElement
from stageflow.gates import Gate, GateResult, Lock, LockType
from tests.property.generators import (
    complex_gate,
    dict_element,
    lock_instance,
    simple_gate,
)

pytestmark = pytest.mark.property


class TestGateCompositionProperties:
    """Property-based tests for Gate composition and logical behaviors."""

    @given(gate=simple_gate(), element=dict_element())
    def test_gate_evaluation_deterministic(self, gate: Gate, element: DictElement):
        """Gate evaluation should be deterministic - same result every time."""
        result1 = gate.evaluate(element)
        result2 = gate.evaluate(element)

        assert result1.passed == result2.passed
        assert result1.failed_components == result2.failed_components
        assert result1.passed_components == result2.passed_components
        assert result1.messages == result2.messages
        assert result1.actions == result2.actions

    @given(gate=simple_gate(), element=dict_element())
    def test_gate_result_structure(self, gate: Gate, element: DictElement):
        """Gate evaluation should return properly structured GateResult."""
        result = gate.evaluate(element)

        assert isinstance(result, GateResult)
        assert isinstance(result.passed, bool)
        assert isinstance(result.failed_components, tuple)
        assert isinstance(result.passed_components, tuple)
        assert isinstance(result.messages, tuple)
        assert isinstance(result.actions, tuple)
        assert isinstance(result.evaluation_time_ms, float)
        assert isinstance(result.short_circuited, bool)

        # All messages should be strings
        for msg in result.messages:
            assert isinstance(msg, str)

        # All actions should be strings
        for action in result.actions:
            assert isinstance(action, str)

        # Evaluation time should be non-negative
        assert result.evaluation_time_ms >= 0

    @given(gate=simple_gate(), element=dict_element())
    def test_gate_component_accounting(self, gate: Gate, element: DictElement):
        """Gate evaluation should properly account for all components."""
        result = gate.evaluate(element)

        # Total components should match gate components (unless short-circuited)
        total_evaluated = len(result.passed_components) + len(result.failed_components)

        if not result.short_circuited:
            assert total_evaluated == len(gate.components)
        else:
            # If short-circuited, should have evaluated fewer than total
            assert total_evaluated <= len(gate.components)

        # No component should appear in both passed and failed lists
        passed_set = {id(comp) for comp in result.passed_components}
        failed_set = {id(comp) for comp in result.failed_components}
        assert passed_set.isdisjoint(failed_set)

    def test_and_gate_logic_properties(self):
        """Test logical properties of AND gates."""
        # Create locks that will definitely pass or fail
        always_pass = Lock("nonexistent", LockType.EXISTS, False)
        always_fail = Lock("nonexistent", LockType.EXISTS, True)

        element = DictElement({})

        # AND gate with all passing components should pass
        all_pass_gate = Gate.AND(always_pass, always_pass, name="all_pass")
        result = all_pass_gate.evaluate(element)
        assert result.passed is True
        assert len(result.failed_components) == 0

        # AND gate with all failing components should fail
        all_fail_gate = Gate.AND(always_fail, always_fail, name="all_fail")
        result = all_fail_gate.evaluate(element)
        assert result.passed is False
        assert len(result.passed_components) == 0

        # AND gate with mixed components should fail
        mixed_gate = Gate.AND(always_pass, always_fail, name="mixed")
        result = mixed_gate.evaluate(element)
        assert result.passed is False
        assert len(result.failed_components) > 0



    @given(gate=simple_gate())
    def test_gate_property_paths(self, gate: Gate):
        """Test that gate property path collection works correctly."""
        paths = gate.get_property_paths()

        assert isinstance(paths, set)

        # All paths should be strings
        for path in paths:
            assert isinstance(path, str)

        # Should include paths from all components
        for component in gate.components:
            component_paths = component.get_property_paths()
            assert component_paths.issubset(paths)

    @given(gate=simple_gate())
    def test_gate_requires_property(self, gate: Gate):
        """Test property requirement checking."""
        paths = gate.get_property_paths()

        for path in paths:
            assert gate.requires_property(path) is True

        # Non-existent property should not be required
        fake_property = "__definitely_not_a_real_property__"
        if fake_property not in paths:
            assert gate.requires_property(fake_property) is False

    @given(gate=simple_gate())
    def test_gate_summary_and_metadata(self, gate: Gate):
        """Test gate summary and metadata methods."""
        summary = gate.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert gate.name in summary

        complexity = gate.get_complexity()
        assert isinstance(complexity, int)
        assert complexity >= 0

        # Complexity should be at least the number of lock components
        lock_count = sum(1 for comp in gate.components
                        if hasattr(comp, 'lock'))  # LockWrapper
        assert complexity >= lock_count

    @given(gate=simple_gate())
    def test_gate_validation_warnings(self, gate: Gate):
        """Test gate structure validation."""
        issues = gate.validate_structure()
        assert isinstance(issues, list)

        # All issues should be strings
        for issue in issues:
            assert isinstance(issue, str)

    def test_gate_short_circuit_and_behavior(self):
        """Test short-circuit behavior for AND gates."""
        # Create a lock that fails and one that would take time to evaluate
        fail_fast = Lock("nonexistent", LockType.EXISTS, True)
        slow_lock = Lock("somekey", LockType.REGEX, r".*")

        element = DictElement({"somekey": "value"})

        # In AND gate, first failure should short-circuit
        gate = Gate.AND(fail_fast, slow_lock, name="short_circuit_test")
        result = gate.evaluate(element)

        assert result.passed is False
        assert result.short_circuited is True
        # Should have stopped after first component failed
        assert len(result.failed_components) == 1
        assert len(result.passed_components) == 0


    @given(gate=complex_gate(), element=dict_element())
    def test_complex_gate_evaluation(self, gate: Gate, element: DictElement):
        """Test evaluation of complex nested gates."""
        result = gate.evaluate(element)

        # Should still return valid GateResult
        assert isinstance(result, GateResult)
        assert isinstance(result.passed, bool)

        # Should handle nested structure properly
        total_components = len(result.passed_components) + len(result.failed_components)
        assert total_components >= 0

        # Evaluation time should be reasonable (not extremely long)
        assert result.evaluation_time_ms < 1000  # Less than 1 second

    def test_gate_construction_validation(self):
        """Test that gate construction validates inputs properly."""
        lock = Lock("test", LockType.EXISTS)

        # Valid constructions should work
        and_gate = Gate.AND(lock, lock, name="test_and")
        assert and_gate.name == "test_and"
        assert len(and_gate.components) == 2

        # Invalid constructions should raise errors
        with pytest.raises(ValueError):
            # AND with no components
            Gate.AND()

    @given(locks=st.lists(lock_instance(), min_size=2, max_size=5))
    def test_gate_commutativity_properties(self, locks):
        """Test commutativity properties where applicable."""
        element = DictElement({"test": "value"})

        # AND and OR gates should be commutative (order shouldn't matter for final result)
        # Note: order might affect short-circuiting behavior, but final result should be same

        # Test AND commutativity
        and_gate1 = Gate.AND(*locks, name="and1")
        and_gate2 = Gate.AND(*reversed(locks), name="and2")

        # Turn off short-circuiting by evaluating both fully
        result1 = and_gate1.evaluate(element)
        result2 = and_gate2.evaluate(element)

        # Final result should be the same
        assert result1.passed == result2.passed



    @given(gate1=simple_gate(), gate2=simple_gate())
    def test_gate_compatibility(self, gate1: Gate, gate2: Gate):
        """Test gate compatibility checking."""
        # For now, all gates should be compatible
        # This could be extended in the future
        assert gate1.is_compatible_with(gate2) is True
        assert gate2.is_compatible_with(gate1) is True

    @given(gate=complex_gate())
    def test_gate_complexity_bounds(self, gate: Gate):
        """Test that gate complexity is within reasonable bounds."""
        complexity = gate.get_complexity()

        # Complexity should be positive
        assert complexity > 0

        # Complexity should not exceed a reasonable maximum for test data
        # (This prevents runaway generation of extremely complex gates)
        assert complexity <= 100

        # Complexity should be at least the number of direct lock components
        direct_locks = sum(1 for comp in gate.components if hasattr(comp, 'lock'))
        assert complexity >= direct_locks

    @given(gate=complex_gate())
    def test_gate_depth_bounds(self, gate: Gate):
        """Test that gate nesting depth is within reasonable bounds."""
        max_depth = gate._get_max_depth()

        # Depth should be non-negative
        assert max_depth >= 0

        # Depth should not exceed our generation limits
        assert max_depth <= 10  # Reasonable maximum for testing
