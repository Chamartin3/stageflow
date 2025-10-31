"""
Test suite for ConditionalLock functionality.

Tests the ConditionalLock class with if-then-else validation logic,
nested conditionals, depth limits, and error handling.
"""

import pytest

from stageflow.element import DictElement
from stageflow.lock import ConditionalLock, SimpleLock


class TestConditionalLockBasic:
    """Test basic ConditionalLock functionality."""

    def test_conditional_if_true_then_passes(self):
        """IF passes, THEN passes → success."""
        element = DictElement({"type": "feature", "testing": "done"})

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)
        assert result.success is True

    def test_conditional_if_true_then_fails(self):
        """IF passes, THEN fails → failure."""
        element = DictElement({"type": "feature"})  # Missing testing

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)
        assert result.success is False
        assert result.context == "then branch"
        assert len(result.nested_failures) > 0

    def test_conditional_if_false_no_else_passes(self):
        """IF fails, no ELSE → success (not applicable)."""
        element = DictElement({"type": "bug"})

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)
        assert result.success is True
        assert result.context == "condition not applicable"

    def test_conditional_if_false_else_evaluated(self):
        """IF fails, ELSE exists → evaluate ELSE."""
        element = DictElement({"type": "bug", "verification": "done"})

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})],
            else_locks=[SimpleLock({"type": "EXISTS", "property_path": "verification"})]
        )

        result = conditional.validate(element)
        assert result.success is True
        assert result.context == "else branch"


class TestConditionalLockLogic:
    """Test ConditionalLock logic and edge cases."""

    def test_conditional_multiple_if_conditions_and_logic(self):
        """Multiple IF locks use AND logic."""
        element = DictElement({"type": "feature", "priority": 1, "testing": "done"})

        conditional = ConditionalLock(
            if_locks=[
                SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"}),
                SimpleLock({"type": "EQUALS", "property_path": "priority", "expected_value": 1})
            ],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)
        assert result.success is True

    def test_conditional_multiple_if_conditions_and_fails(self):
        """Multiple IF locks - one fails → condition fails."""
        element = DictElement({"type": "feature", "priority": 2, "testing": "done"})  # priority != 1

        conditional = ConditionalLock(
            if_locks=[
                SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"}),
                SimpleLock({"type": "EQUALS", "property_path": "priority", "expected_value": 1})
            ],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)
        assert result.success is True  # Condition not applicable
        assert result.context == "condition not applicable"

    def test_conditional_multiple_then_conditions_and_logic(self):
        """Multiple THEN locks use AND logic."""
        element = DictElement({"type": "feature", "testing": "done", "docs": "written"})

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[
                SimpleLock({"type": "EXISTS", "property_path": "testing"}),
                SimpleLock({"type": "EXISTS", "property_path": "docs"})
            ]
        )

        result = conditional.validate(element)
        assert result.success is True

    def test_conditional_multiple_then_conditions_and_fails(self):
        """Multiple THEN locks - one fails → failure."""
        element = DictElement({"type": "feature", "testing": "done"})  # Missing docs

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[
                SimpleLock({"type": "EXISTS", "property_path": "testing"}),
                SimpleLock({"type": "EXISTS", "property_path": "docs"})
            ]
        )

        result = conditional.validate(element)
        assert result.success is False
        assert result.context == "then branch"
        assert len(result.nested_failures) == 1


class TestConditionalLockNested:
    """Test nested ConditionalLock functionality."""

    def test_conditional_nested(self):
        """Conditional within conditional."""
        element = DictElement({"type": "feature", "priority": 1, "perf_tests": "done"})

        inner = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "priority", "expected_value": 1})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "perf_tests"})]
        )

        outer = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[inner]
        )

        result = outer.validate(element)
        assert result.success is True

    def test_conditional_nested_failure_propagation(self):
        """Nested conditional failure propagates correctly."""
        element = DictElement({"type": "feature", "priority": 1})  # Missing perf_tests

        inner = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "priority", "expected_value": 1})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "perf_tests"})]
        )

        outer = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[inner]
        )

        result = outer.validate(element)
        assert result.success is False
        assert result.context == "then branch"
        assert len(result.nested_failures) == 1
        # The nested failure should also have nested failures
        nested_result = result.nested_failures[0]
        assert nested_result.context == "then branch"


class TestConditionalLockDepthLimit:
    """Test ConditionalLock depth limit enforcement."""

    def test_conditional_max_depth_exceeded(self):
        """Verify recursion limit enforced."""
        element = DictElement({"value": 1})

        # Create deeply nested conditionals (7 levels to exceed max_depth=5)
        lock = SimpleLock({"type": "EXISTS", "property_path": "value"})

        for _ in range(7):
            lock = ConditionalLock(
                if_locks=[SimpleLock({"type": "EXISTS", "property_path": "value"})],
                then_locks=[lock],
                max_depth=5
            )

        result = lock.validate(element)
        assert result.success is False

        # Check that depth limit error exists somewhere in the nested failures
        def find_depth_error(r):
            if "maximum" in r.error_message.lower() and "depth" in r.error_message.lower():
                return True
            for nested in r.nested_failures:
                if find_depth_error(nested):
                    return True
            return False

        assert find_depth_error(result)

    def test_conditional_depth_limit_configurable(self):
        """Verify depth limit is configurable."""
        element = DictElement({"value": 1})

        # Create 4 levels of nesting with limit of 2 (should exceed limit)
        lock = SimpleLock({"type": "EXISTS", "property_path": "value"})

        for _ in range(4):
            lock = ConditionalLock(
                if_locks=[SimpleLock({"type": "EXISTS", "property_path": "value"})],
                then_locks=[lock],
                max_depth=2
            )

        result = lock.validate(element)
        assert result.success is False

        # Check that depth limit error exists somewhere in the nested failures
        def find_depth_error(r):
            if "maximum" in r.error_message.lower() and "depth" in r.error_message.lower():
                return True
            for nested in r.nested_failures:
                if find_depth_error(nested):
                    return True
            return False

        assert find_depth_error(result)


class TestConditionalLockValidation:
    """Test ConditionalLock input validation."""

    def test_conditional_empty_if_raises(self):
        """Empty IF locks raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ConditionalLock(
                if_locks=[],
                then_locks=[SimpleLock({"type": "EXISTS", "property_path": "field"})]
            )
        assert "IF lock" in str(exc_info.value)

    def test_conditional_empty_then_raises(self):
        """Empty THEN locks raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ConditionalLock(
                if_locks=[SimpleLock({"type": "EXISTS", "property_path": "field"})],
                then_locks=[]
            )
        assert "THEN lock" in str(exc_info.value)

    def test_conditional_none_else_locks_converts_to_empty(self):
        """None else_locks converts to empty list."""
        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EXISTS", "property_path": "field"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "other"})],
            else_locks=None
        )

        assert conditional.else_locks == []


class TestConditionalLockErrorReporting:
    """Test ConditionalLock error reporting."""

    def test_conditional_error_tree_format(self):
        """Verify error tree formatting for conditional failures."""
        element = DictElement({"type": "feature"})  # Missing testing

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[SimpleLock({"type": "EXISTS", "property_path": "testing"})]
        )

        result = conditional.validate(element)

        tree = result.format_error_tree()
        assert "[then branch]" in tree
        assert "→ Conditional then branch failed" in tree
        assert "Property 'testing' is required" in tree

    def test_conditional_error_tree_with_nested_failures(self):
        """Verify error tree with multiple nested failures."""
        element = DictElement({"type": "feature"})  # Missing testing and docs

        conditional = ConditionalLock(
            if_locks=[SimpleLock({"type": "EQUALS", "property_path": "type", "expected_value": "feature"})],
            then_locks=[
                SimpleLock({"type": "EXISTS", "property_path": "testing"}),
                SimpleLock({"type": "EXISTS", "property_path": "docs"})
            ]
        )

        result = conditional.validate(element)

        tree = result.format_error_tree()
        assert "[then branch]" in tree
        assert "→ Conditional then branch failed" in tree
        # Should have two nested failures
        assert tree.count("Property '") == 2
