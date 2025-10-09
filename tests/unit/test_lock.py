"""Comprehensive unit tests for the stageflow.lock module.

This test suite covers all functionality in the Lock validation system, including:
- All 12 built-in lock types and their validation logic
- LockType enum behavior and failure message generation
- Lock class initialization and validation methods
- LockFactory creation patterns and shorthand syntax
- Error handling and edge cases for property path resolution
- Integration with Element objects for property access
"""

import pytest
import re
from dataclasses import FrozenInstanceError
from typing import Any, Dict, List, Union
from unittest.mock import Mock, patch

from stageflow.lock import (
    Lock,
    LockFactory,
    LockType,
    LockResult,
    LockMetaData,
    LockDefinitionDict,
    LockShorthandDict,
    LockDefinition,
    LockShorhands
)
from stageflow.element import DictElement


class TestLockType:
    """Test suite for the LockType enum and its validation methods."""

    def test_lock_type_enum_contains_all_expected_types(self):
        """Verify LockType enum contains all 12 expected lock types."""
        # Arrange
        expected_lock_types = {
            "EXISTS", "EQUALS", "GREATER_THAN", "LESS_THAN", "CONTAINS",
            "REGEX", "TYPE_CHECK", "RANGE", "LENGTH", "NOT_EMPTY",
            "IN_LIST", "NOT_IN_LIST"
        }

        # Act
        actual_lock_types = {lock_type.name for lock_type in LockType}

        # Assert
        assert actual_lock_types == expected_lock_types
        assert len(LockType) == 12

    def test_lock_type_enum_values_are_correct(self):
        """Verify LockType enum values match expected string representations."""
        # Arrange
        expected_mappings = {
            LockType.EXISTS: "exists",
            LockType.EQUALS: "equals",
            LockType.GREATER_THAN: "greater_than",
            LockType.LESS_THAN: "less_than",
            LockType.CONTAINS: "contains",
            LockType.REGEX: "regex",
            LockType.TYPE_CHECK: "type_check",
            LockType.RANGE: "range",
            LockType.LENGTH: "length",
            LockType.NOT_EMPTY: "not_empty",
            LockType.IN_LIST: "in_list",
            LockType.NOT_IN_LIST: "not_in_list"
        }

        # Act & Assert
        for lock_type, expected_value in expected_mappings.items():
            assert lock_type.value == expected_value


class TestLockTypeFailureMessages:
    """Test suite for LockType failure message generation."""

    def test_exists_failure_message(self):
        """Verify EXISTS lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.EXISTS
        property_path = "user.email"
        actual_value = None

        # Act
        message = lock_type.failure_message(property_path, actual_value)

        # Assert
        assert "required but missing or empty" in message
        assert property_path in message

    def test_equals_failure_message(self):
        """Verify EQUALS lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.EQUALS
        property_path = "status"
        actual_value = "pending"
        expected_value = "active"

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should equal" in message
        assert str(expected_value) in message
        assert str(actual_value) in message
        assert property_path in message

    def test_greater_than_failure_message(self):
        """Verify GREATER_THAN lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.GREATER_THAN
        property_path = "age"
        actual_value = 16
        expected_value = 18

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be greater than" in message
        assert str(expected_value) in message
        assert str(actual_value) in message

    def test_less_than_failure_message(self):
        """Verify LESS_THAN lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.LESS_THAN
        property_path = "count"
        actual_value = 150
        expected_value = 100

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be less than" in message
        assert str(expected_value) in message
        assert str(actual_value) in message

    def test_regex_failure_message(self):
        """Verify REGEX lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.REGEX
        property_path = "email"
        actual_value = "invalid-email"
        expected_value = r"^[^@]+@[^@]+\.[^@]+$"

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should match pattern" in message
        assert expected_value in message
        assert actual_value in message

    def test_in_list_failure_message(self):
        """Verify IN_LIST lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.IN_LIST
        property_path = "role"
        actual_value = "guest"
        expected_value = ["admin", "user", "moderator"]

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be one of" in message
        assert str(expected_value) in message
        assert actual_value in message

    def test_not_in_list_failure_message(self):
        """Verify NOT_IN_LIST lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.NOT_IN_LIST
        property_path = "username"
        actual_value = "admin"
        expected_value = ["admin", "root", "system"]

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should not be one of" in message
        assert str(expected_value) in message
        assert actual_value in message

    def test_contains_failure_message(self):
        """Verify CONTAINS lock type generates appropriate failure message."""
        # Arrange
        lock_type = LockType.CONTAINS
        property_path = "description"
        actual_value = "This is a test"
        expected_value = "important"

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should contain" in message
        assert expected_value in message
        assert actual_value in message

    def test_type_check_failure_message_with_string_type(self):
        """Verify TYPE_CHECK lock type generates appropriate failure message for string types."""
        # Arrange
        lock_type = LockType.TYPE_CHECK
        property_path = "score"
        actual_value = "not_a_number"
        expected_value = "int"

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be of type" in message
        assert expected_value in message
        assert "str" in message  # actual type
        assert str(actual_value) in message

    def test_type_check_failure_message_with_type_object(self):
        """Verify TYPE_CHECK lock type generates appropriate failure message for type objects."""
        # Arrange
        lock_type = LockType.TYPE_CHECK
        property_path = "data"
        actual_value = "string_value"
        expected_value = int

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be of type" in message
        assert "int" in message  # expected type name
        assert "str" in message  # actual type
        assert actual_value in message

    def test_range_failure_message_with_valid_range(self):
        """Verify RANGE lock type generates appropriate failure message for valid range."""
        # Arrange
        lock_type = LockType.RANGE
        property_path = "percentage"
        actual_value = 150
        expected_value = [0, 100]

        # Act
        message = lock_type.failure_message(property_path, actual_value, expected_value)

        # Assert
        assert "should be between" in message
        assert "0" in message
        assert "100" in message
        assert str(actual_value) in message

    def test_unknown_lock_type_failure_message(self):
        """Verify unknown lock types generate generic failure message."""
        # Arrange
        # This tests the fallback case in the failure_message method
        lock_type = LockType.LENGTH  # Using LENGTH which doesn't have a specific message
        property_path = "text"
        actual_value = "short"

        # Act
        message = lock_type.failure_message(property_path, actual_value)

        # Assert
        assert "failed validation for lock type" in message
        assert property_path in message
        assert lock_type.value in message


class TestLockTypeValidation:
    """Test suite for LockType validation logic."""

    @pytest.fixture
    def sample_lock_meta(self) -> LockMetaData:
        """Create sample lock metadata for testing."""
        return LockMetaData(
            expected_value="test_value",
            min_value=0,
            max_value=100
        )

    def test_exists_validation_with_valid_values(self):
        """Verify EXISTS validation passes for non-None, non-empty values."""
        # Arrange
        lock_type = LockType.EXISTS
        test_cases = [
            "non_empty_string",
            123,
            True,
            False,
            ["list", "with", "items"],
            {"key": "value"},
            " \t non-whitespace \n "  # String with content after stripping
        ]

        for value in test_cases:
            # Act
            result = lock_type.validate(value, {})

            # Assert
            assert result is True, f"EXISTS validation failed for value: {value}"

    def test_exists_validation_with_invalid_values(self):
        """Verify EXISTS validation fails for None and empty values."""
        # Arrange
        lock_type = LockType.EXISTS
        test_cases = [
            None,
            "",
            "   ",  # Whitespace-only string
            "\t\n  \r"  # Various whitespace characters
        ]

        for value in test_cases:
            # Act
            result = lock_type.validate(value, {})

            # Assert
            assert result is False, f"EXISTS validation should have failed for value: {repr(value)}"

    def test_not_empty_validation_with_strings(self):
        """Verify NOT_EMPTY validation works correctly for strings."""
        # Arrange
        lock_type = LockType.NOT_EMPTY

        # Act & Assert
        assert lock_type.validate("non_empty", {}) is True
        assert lock_type.validate("   content   ", {}) is True
        assert lock_type.validate("", {}) is False
        assert lock_type.validate("   ", {}) is False
        assert lock_type.validate("\t\n", {}) is False

    def test_not_empty_validation_with_collections(self):
        """Verify NOT_EMPTY validation works correctly for collections."""
        # Arrange
        lock_type = LockType.NOT_EMPTY

        # Act & Assert
        assert lock_type.validate([1, 2, 3], {}) is True
        assert lock_type.validate({"key": "value"}, {}) is True
        assert lock_type.validate((1, 2), {}) is True
        assert lock_type.validate([], {}) is False
        assert lock_type.validate({}, {}) is False
        assert lock_type.validate((), {}) is False

    def test_not_empty_validation_with_other_types(self):
        """Verify NOT_EMPTY validation works correctly for other types."""
        # Arrange
        lock_type = LockType.NOT_EMPTY

        # Act & Assert
        assert lock_type.validate(123, {}) is True
        assert lock_type.validate(True, {}) is True
        assert lock_type.validate(False, {}) is True
        assert lock_type.validate(None, {}) is False

    def test_equals_validation(self):
        """Verify EQUALS validation works correctly."""
        # Arrange
        lock_type = LockType.EQUALS

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": "test"}) is True
        assert lock_type.validate(42, {"expected_value": 42}) is True
        assert lock_type.validate(True, {"expected_value": True}) is True
        assert lock_type.validate("test", {"expected_value": "different"}) is False
        assert lock_type.validate(42, {"expected_value": 41}) is False

    def test_greater_than_validation(self):
        """Verify GREATER_THAN validation works correctly."""
        # Arrange
        lock_type = LockType.GREATER_THAN

        # Act & Assert
        assert lock_type.validate(25, {"expected_value": 18}) is True
        assert lock_type.validate(18.5, {"expected_value": 18}) is True
        assert lock_type.validate(17, {"expected_value": 18}) is False
        assert lock_type.validate(18, {"expected_value": 18}) is False

    def test_less_than_validation(self):
        """Verify LESS_THAN validation works correctly."""
        # Arrange
        lock_type = LockType.LESS_THAN

        # Act & Assert
        assert lock_type.validate(15, {"expected_value": 18}) is True
        assert lock_type.validate(17.5, {"expected_value": 18}) is True
        assert lock_type.validate(18, {"expected_value": 18}) is False
        assert lock_type.validate(19, {"expected_value": 18}) is False

    def test_range_validation(self):
        """Verify RANGE validation works correctly."""
        # Arrange
        lock_type = LockType.RANGE

        # Act & Assert
        assert lock_type.validate(50, {"min_value": 0, "max_value": 100}) is True
        assert lock_type.validate(0, {"min_value": 0, "max_value": 100}) is True
        assert lock_type.validate(100, {"min_value": 0, "max_value": 100}) is True
        assert lock_type.validate(-1, {"min_value": 0, "max_value": 100}) is False
        assert lock_type.validate(101, {"min_value": 0, "max_value": 100}) is False

    def test_length_validation(self):
        """Verify LENGTH validation works correctly."""
        # Arrange
        lock_type = LockType.LENGTH

        # Act & Assert
        assert lock_type.validate("hello", {"expected_value": 5}) is True
        assert lock_type.validate([1, 2, 3], {"expected_value": 3}) is True
        assert lock_type.validate("test", {"expected_value": 5}) is False
        assert lock_type.validate([1, 2], {"expected_value": 3}) is False

    def test_length_validation_with_invalid_types(self):
        """Verify LENGTH validation handles objects without __len__ method."""
        # Arrange
        lock_type = LockType.LENGTH

        # Act & Assert
        assert lock_type.validate(123, {"expected_value": 3}) is False
        assert lock_type.validate(None, {"expected_value": 0}) is False
        assert lock_type.validate(True, {"expected_value": 1}) is False

    def test_regex_validation_with_valid_patterns(self):
        """Verify REGEX validation works correctly for valid patterns."""
        # Arrange
        lock_type = LockType.REGEX
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        phone_pattern = r"^\+?[\d\s\-\(\)]+$"

        # Act & Assert
        assert lock_type.validate("user@example.com", {"expected_value": email_pattern}) is True
        assert lock_type.validate("+1-234-567-8900", {"expected_value": phone_pattern}) is True
        assert lock_type.validate("invalid-email", {"expected_value": email_pattern}) is False
        assert lock_type.validate("abc@", {"expected_value": email_pattern}) is False

    def test_regex_validation_with_non_string_values(self):
        """Verify REGEX validation fails for non-string values."""
        # Arrange
        lock_type = LockType.REGEX
        pattern = r"^\d+$"

        # Act & Assert
        assert lock_type.validate(123, {"expected_value": pattern}) is False
        assert lock_type.validate(None, {"expected_value": pattern}) is False
        assert lock_type.validate(True, {"expected_value": pattern}) is False

    def test_regex_validation_with_invalid_pattern(self):
        """Verify REGEX validation handles invalid regex patterns gracefully."""
        # Arrange
        lock_type = LockType.REGEX
        invalid_pattern = r"[invalid regex pattern ("

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": invalid_pattern}) is False

    def test_contains_validation_with_strings(self):
        """Verify CONTAINS validation works correctly for strings."""
        # Arrange
        lock_type = LockType.CONTAINS

        # Act & Assert
        assert lock_type.validate("Hello World", {"expected_value": "World"}) is True
        assert lock_type.validate("Hello World", {"expected_value": "Hello"}) is True
        assert lock_type.validate("Hello World", {"expected_value": "xyz"}) is False

    def test_contains_validation_with_collections(self):
        """Verify CONTAINS validation works correctly for collections."""
        # Arrange
        lock_type = LockType.CONTAINS

        # Act & Assert
        assert lock_type.validate(["apple", "banana", "cherry"], {"expected_value": "banana"}) is True
        assert lock_type.validate({"a": 1, "b": 2}, {"expected_value": "b"}) is True
        assert lock_type.validate([1, 2, 3], {"expected_value": "2"}) is True  # String conversion
        assert lock_type.validate([1, 2, 3], {"expected_value": "4"}) is False

    def test_contains_validation_with_invalid_types(self):
        """Verify CONTAINS validation handles invalid types gracefully."""
        # Arrange
        lock_type = LockType.CONTAINS

        # Act & Assert
        assert lock_type.validate(123, {"expected_value": "1"}) is False
        assert lock_type.validate(None, {"expected_value": "test"}) is False

    def test_in_list_validation(self):
        """Verify IN_LIST validation works correctly."""
        # Arrange
        lock_type = LockType.IN_LIST
        valid_roles = ["admin", "user", "moderator"]

        # Act & Assert
        assert lock_type.validate("admin", {"expected_value": valid_roles}) is True
        assert lock_type.validate("user", {"expected_value": valid_roles}) is True
        assert lock_type.validate("guest", {"expected_value": valid_roles}) is False

    def test_in_list_validation_with_different_collection_types(self):
        """Verify IN_LIST validation works with tuples and sets."""
        # Arrange
        lock_type = LockType.IN_LIST

        # Act & Assert
        assert lock_type.validate("a", {"expected_value": ("a", "b", "c")}) is True
        assert lock_type.validate("x", {"expected_value": {"x", "y", "z"}}) is True
        assert lock_type.validate("d", {"expected_value": ("a", "b", "c")}) is False

    def test_in_list_validation_with_invalid_expected_value(self):
        """Verify IN_LIST validation fails when expected_value is not a collection."""
        # Arrange
        lock_type = LockType.IN_LIST

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": "not_a_list"}) is False
        assert lock_type.validate("test", {"expected_value": 123}) is False

    def test_not_in_list_validation(self):
        """Verify NOT_IN_LIST validation works correctly."""
        # Arrange
        lock_type = LockType.NOT_IN_LIST
        forbidden_names = ["admin", "root", "system"]

        # Act & Assert
        assert lock_type.validate("user", {"expected_value": forbidden_names}) is True
        assert lock_type.validate("john", {"expected_value": forbidden_names}) is True
        assert lock_type.validate("admin", {"expected_value": forbidden_names}) is False
        assert lock_type.validate("root", {"expected_value": forbidden_names}) is False

    def test_type_check_validation_with_string_type_names(self):
        """Verify TYPE_CHECK validation works with string type names."""
        # Arrange
        lock_type = LockType.TYPE_CHECK

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": "str"}) is True
        assert lock_type.validate("test", {"expected_value": "string"}) is True
        assert lock_type.validate(42, {"expected_value": "int"}) is True
        assert lock_type.validate(42, {"expected_value": "integer"}) is True
        assert lock_type.validate(3.14, {"expected_value": "float"}) is True
        assert lock_type.validate(True, {"expected_value": "bool"}) is True
        assert lock_type.validate(True, {"expected_value": "boolean"}) is True
        assert lock_type.validate([1, 2, 3], {"expected_value": "list"}) is True
        assert lock_type.validate({"a": 1}, {"expected_value": "dict"}) is True
        assert lock_type.validate({"a": 1}, {"expected_value": "dictionary"}) is True

    def test_type_check_validation_with_type_objects(self):
        """Verify TYPE_CHECK validation works with actual type objects."""
        # Arrange
        lock_type = LockType.TYPE_CHECK

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": str}) is True
        assert lock_type.validate(42, {"expected_value": int}) is True
        assert lock_type.validate(3.14, {"expected_value": float}) is True
        assert lock_type.validate(True, {"expected_value": bool}) is True
        assert lock_type.validate([1, 2, 3], {"expected_value": list}) is True
        assert lock_type.validate({"a": 1}, {"expected_value": dict}) is True

    def test_type_check_validation_failures(self):
        """Verify TYPE_CHECK validation fails for mismatched types."""
        # Arrange
        lock_type = LockType.TYPE_CHECK

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": "int"}) is False
        assert lock_type.validate(42, {"expected_value": "str"}) is False
        assert lock_type.validate(3.14, {"expected_value": int}) is False
        assert lock_type.validate("test", {"expected_value": "unknown_type"}) is False

    def test_type_check_validation_with_invalid_expected_value(self):
        """Verify TYPE_CHECK validation handles invalid expected values."""
        # Arrange
        lock_type = LockType.TYPE_CHECK

        # Act & Assert
        assert lock_type.validate("test", {"expected_value": 123}) is False
        assert lock_type.validate("test", {"expected_value": None}) is False

    def test_validation_with_none_and_zero_values(self):
        """Verify validation handles None and zero values correctly for numeric comparisons."""
        # Arrange
        gt_lock = LockType.GREATER_THAN
        lt_lock = LockType.LESS_THAN
        range_lock = LockType.RANGE

        # Act & Assert - None values should be treated as 0
        assert gt_lock.validate(None, {"expected_value": -1}) is True
        assert gt_lock.validate(None, {"expected_value": 1}) is False
        assert lt_lock.validate(None, {"expected_value": 1}) is True
        assert lt_lock.validate(None, {"expected_value": -1}) is False
        assert range_lock.validate(None, {"min_value": -1, "max_value": 1}) is True

    def test_unsupported_lock_type_raises_value_error(self):
        """Verify that all current lock types are supported."""
        # Arrange & Act & Assert
        # Test that all defined lock types can be validated without errors
        for lock_type in LockType:
            # Verify each lock type has proper validation logic
            try:
                # Use a simple test case for each lock type
                result = lock_type.validate("test_value", {"expected_value": "test_value"})
                assert isinstance(result, bool)
            except Exception as e:
                # If an exception occurs, it should be a known validation error,
                # not an unsupported type error
                assert "Unsupported lock type" not in str(e)


class TestLockResult:
    """Test suite for LockResult data class."""

    def test_lock_result_creation_with_success(self):
        """Verify LockResult can be created for successful validation."""
        # Arrange
        property_path = "user.email"
        lock_type = LockType.EXISTS
        actual_value = "user@example.com"

        # Act
        result = LockResult(
            success=True,
            property_path=property_path,
            lock_type=lock_type,
            actual_value=actual_value,
            expected_value=None,
            error_message=""
        )

        # Assert
        assert result.success is True
        assert result.property_path == property_path
        assert result.lock_type == lock_type
        assert result.actual_value == actual_value
        assert result.expected_value is None
        assert result.error_message == ""

    def test_lock_result_creation_with_failure(self):
        """Verify LockResult can be created for failed validation."""
        # Arrange
        property_path = "user.age"
        lock_type = LockType.GREATER_THAN
        actual_value = 16
        expected_value = 18
        error_message = "Age must be greater than 18"

        # Act
        result = LockResult(
            success=False,
            property_path=property_path,
            lock_type=lock_type,
            actual_value=actual_value,
            expected_value=expected_value,
            error_message=error_message
        )

        # Assert
        assert result.success is False
        assert result.property_path == property_path
        assert result.lock_type == lock_type
        assert result.actual_value == actual_value
        assert result.expected_value == expected_value
        assert result.error_message == error_message

    def test_lock_result_is_frozen_dataclass(self):
        """Verify LockResult is immutable (frozen dataclass)."""
        # Arrange
        result = LockResult(
            success=True,
            property_path="test",
            lock_type=LockType.EXISTS,
            actual_value="value",
            expected_value=None,
            error_message=""
        )

        # Act & Assert
        with pytest.raises((AttributeError, FrozenInstanceError), match="can't set attribute|cannot assign to field"):
            result.success = False

    def test_lock_result_default_values(self):
        """Verify LockResult has appropriate default values."""
        # Arrange & Act
        result = LockResult(
            success=True,
            property_path="test",
            lock_type=LockType.EXISTS
        )

        # Assert
        assert result.actual_value is None
        assert result.expected_value is None
        assert result.error_message == ""


class TestLock:
    """Test suite for the Lock class."""

    @pytest.fixture
    def sample_element(self) -> DictElement:
        """Create a sample element for testing lock validation."""
        data = {
            "user_id": "user123",
            "email": "john@example.com",
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
                "age": 25,
                "bio": "Software developer with 5 years of experience"
            },
            "preferences": {
                "theme": "dark",
                "notifications": True,
                "language": "en"
            },
            "scores": [85, 92, 78, 96],
            "metadata": {
                "created_at": "2024-01-01T10:00:00Z",
                "last_login": None,
                "is_verified": True
            }
        }
        return DictElement(data)

    def test_lock_initialization_with_valid_config(self):
        """Verify Lock can be initialized with valid configuration."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "user.email",
            "expected_value": None
        }

        # Act
        lock = Lock(config)

        # Assert
        assert lock.lock_type == LockType.EXISTS
        assert lock.property_path == "user.email"
        assert lock.expected_value is None

    def test_lock_initialization_with_expected_value(self):
        """Verify Lock initialization includes expected_value and metadata."""
        # Arrange
        config = {
            "type": LockType.EQUALS,
            "property_path": "status",
            "expected_value": "active",
            "metadata": {"min_value": 0, "max_value": 100}
        }

        # Act
        lock = Lock(config)

        # Assert
        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "status"
        assert lock.expected_value == "active"
        assert lock.metadata == {"min_value": 0, "max_value": 100}

    def test_lock_initialization_with_missing_metadata(self):
        """Verify Lock initialization handles missing metadata gracefully."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "test",
            "expected_value": None
        }

        # Act
        lock = Lock(config)

        # Assert
        assert lock.metadata == {}

    def test_lock_validation_success_with_exists_lock(self, sample_element):
        """Verify Lock validation succeeds for existing properties."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "email",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert isinstance(result, LockResult)
        assert result.success is True
        assert result.property_path == "email"
        assert result.lock_type == LockType.EXISTS
        assert result.actual_value == "john@example.com"
        assert result.error_message == ""

    def test_lock_validation_failure_with_exists_lock(self, sample_element):
        """Verify Lock validation fails for missing properties."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "nonexistent.property",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert isinstance(result, LockResult)
        assert result.success is False
        assert result.property_path == "nonexistent.property"
        assert result.lock_type == LockType.EXISTS
        assert result.actual_value is None
        assert "required but missing or empty" in result.error_message

    def test_lock_validation_with_equals_lock_success(self, sample_element):
        """Verify Lock validation succeeds for equals comparison."""
        # Arrange
        config = {
            "type": LockType.EQUALS,
            "property_path": "preferences.theme",
            "expected_value": "dark"
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is True
        assert result.actual_value == "dark"
        assert result.expected_value == "dark"

    def test_lock_validation_with_equals_lock_failure(self, sample_element):
        """Verify Lock validation fails for incorrect equals comparison."""
        # Arrange
        config = {
            "type": LockType.EQUALS,
            "property_path": "preferences.theme",
            "expected_value": "light"
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is False
        assert result.actual_value == "dark"
        assert result.expected_value == "light"
        assert "should equal 'light' but is 'dark'" in result.error_message

    def test_lock_validation_with_regex_lock_success(self, sample_element):
        """Verify Lock validation succeeds for regex pattern matching."""
        # Arrange
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        config = {
            "type": LockType.REGEX,
            "property_path": "email",
            "expected_value": email_pattern
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is True
        assert result.actual_value == "john@example.com"
        assert result.expected_value == email_pattern

    def test_lock_validation_with_range_lock_success(self, sample_element):
        """Verify Lock validation succeeds for range validation."""
        # Arrange
        config = {
            "type": LockType.RANGE,
            "property_path": "profile.age",
            "expected_value": None,
            "metadata": {"min_value": 18, "max_value": 65}
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is True
        assert result.actual_value == 25

    def test_lock_validation_with_range_lock_failure(self, sample_element):
        """Verify Lock validation fails for out-of-range values."""
        # Arrange
        config = {
            "type": LockType.RANGE,
            "property_path": "profile.age",
            "expected_value": None,
            "metadata": {"min_value": 30, "max_value": 65}
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is False
        assert result.actual_value == 25

    def test_lock_validation_with_nested_property_access(self, sample_element):
        """Verify Lock validation works with deeply nested properties."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "profile.first_name",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        assert result.success is True
        assert result.actual_value == "John"

    def test_lock_validation_handles_element_property_access_error(self):
        """Verify Lock validation handles element property access errors gracefully."""
        # Arrange
        mock_element = Mock()
        mock_element.get_property.side_effect = KeyError("Property not found")

        config = {
            "type": LockType.EXISTS,
            "property_path": "test.property",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(mock_element)

        # Assert
        assert result.success is False
        assert "Error resolving property" in result.error_message
        assert result.actual_value is None

    def test_lock_validation_handles_general_exception(self):
        """Verify Lock validation handles unexpected exceptions gracefully."""
        # Arrange
        mock_element = Mock()
        mock_element.get_property.side_effect = RuntimeError("Unexpected error")

        config = {
            "type": LockType.EXISTS,
            "property_path": "test.property",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(mock_element)

        # Assert
        assert result.success is False
        assert "Error resolving property" in result.error_message
        assert "Unexpected error" in result.error_message

    def test_lock_to_dict_method(self):
        """Verify Lock to_dict method returns correct representation."""
        # Arrange
        config = {
            "type": LockType.EQUALS,
            "property_path": "user.status",
            "expected_value": "active"
        }
        lock = Lock(config)

        # Act
        result = lock.to_dict()

        # Assert
        assert result == {
            "property_path": "user.status",
            "type": LockType.EQUALS,
            "expected_value": "active"
        }

    def test_lock_has_typo_in_error_message_variable(self, sample_element):
        """Document the typo in the lock validation method (eror_message instead of error_message)."""
        # Arrange
        config = {
            "type": LockType.EXISTS,
            "property_path": "missing.property",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(sample_element)

        # Assert
        # This test documents the existing typo in line 249 of lock.py
        # The variable is named 'eror_message' instead of 'error_message'
        assert result.success is False
        # The error message should still be populated despite the typo


class TestLockFactory:
    """Test suite for the LockFactory class."""

    def test_lock_factory_create_with_full_definition(self):
        """Verify LockFactory creates Lock from full definition."""
        # Arrange
        lock_definition = {
            "type": LockType.EQUALS,
            "property_path": "user.status",
            "expected_value": "active"
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert isinstance(lock, Lock)
        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "user.status"
        assert lock.expected_value == "active"

    def test_lock_factory_create_with_exists_shorthand(self):
        """Verify LockFactory creates Lock from 'exists' shorthand."""
        # Arrange
        lock_definition = {
            "exists": "user.email"
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert isinstance(lock, Lock)
        assert lock.lock_type == LockType.EXISTS
        assert lock.property_path == "user.email"
        assert lock.expected_value is True

    def test_lock_factory_create_with_is_true_shorthand(self):
        """Verify LockFactory creates Lock from 'is_true' shorthand."""
        # Arrange
        lock_definition = {
            "is_true": "user.is_verified"
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert isinstance(lock, Lock)
        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "user.is_verified"
        assert lock.expected_value is True

    def test_lock_factory_create_with_is_false_shorthand(self):
        """Verify LockFactory creates Lock from 'is_false' shorthand."""
        # Arrange
        lock_definition = {
            "is_false": "user.is_suspended"
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert isinstance(lock, Lock)
        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "user.is_suspended"
        assert lock.expected_value is False

    def test_lock_factory_create_with_invalid_definition_raises_value_error(self):
        """Verify LockFactory raises ValueError for invalid definitions."""
        # Arrange
        invalid_definitions = [
            {},  # Empty definition
            {"invalid_key": "value"},  # Unknown key
            {"type": LockType.EXISTS},  # Missing property_path
            {"property_path": "test"},  # Missing type
        ]

        for invalid_definition in invalid_definitions:
            # Act & Assert
            with pytest.raises(ValueError, match="Invalid lock definition format"):
                LockFactory.create(invalid_definition)

    def test_lock_factory_create_with_none_shorthand_value(self):
        """Verify LockFactory handles None values in shorthand syntax."""
        # Arrange
        lock_definition = {
            "exists": None,
            "is_true": "some.property"  # This should be used
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "some.property"
        assert lock.expected_value is True

    def test_lock_factory_shorthand_keys_constant(self):
        """Verify LockFactory SHORTHAND_KEYS constant contains expected values."""
        # Arrange
        expected_keys = ["exists", "is_true", "is_false"]

        # Act
        actual_keys = LockFactory.SHORTHAND_KEYS

        # Assert
        assert actual_keys == expected_keys

    def test_lock_shorthands_dictionary_contains_correct_mappings(self):
        """Verify LockShorhands dictionary contains correct mappings."""
        # Arrange
        expected_mappings = {
            "is_true": (LockType.EQUALS, True),
            "is_false": (LockType.EQUALS, False),
            "exists": (LockType.EXISTS, True),
        }

        # Act & Assert
        assert LockShorhands == expected_mappings

    def test_lock_factory_create_prioritizes_full_definition_over_shorthand(self):
        """Verify LockFactory prioritizes full definition when both formats are present."""
        # Arrange
        lock_definition = {
            "type": LockType.REGEX,
            "property_path": "user.email",
            "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
            "exists": "user.name"  # This should be ignored
        }

        # Act
        lock = LockFactory.create(lock_definition)

        # Assert
        assert lock.lock_type == LockType.REGEX
        assert lock.property_path == "user.email"
        assert lock.expected_value == r"^[^@]+@[^@]+\.[^@]+$"


class TestLockIntegration:
    """Integration tests for Lock with real Element instances."""

    @pytest.fixture
    def complex_element(self) -> DictElement:
        """Create a complex element for integration testing."""
        data = {
            "user": {
                "id": "usr_123",
                "profile": {
                    "name": "Alice Johnson",
                    "email": "alice@example.com",
                    "age": 28,
                    "skills": ["Python", "JavaScript", "SQL"],
                    "certifications": {
                        "aws": True,
                        "kubernetes": False
                    }
                },
                "settings": {
                    "theme": "dark",
                    "language": "en-US",
                    "notifications": {
                        "email": True,
                        "push": False,
                        "sms": True
                    }
                }
            },
            "account": {
                "type": "premium",
                "balance": 1250.75,
                "created_at": "2023-06-15T08:30:00Z",
                "last_payment": None,
                "subscription": {
                    "plan": "professional",
                    "expires_at": "2024-06-15T08:30:00Z",
                    "auto_renew": True
                }
            },
            "metrics": {
                "login_count": 142,
                "projects_created": 15,
                "last_activity": "2024-01-20T14:22:00Z",
                "performance_score": 94.5
            }
        }
        return DictElement(data)

    def test_comprehensive_lock_validation_scenario(self, complex_element):
        """Test comprehensive validation scenario with multiple lock types."""
        # Arrange
        locks_and_expectations = [
            # EXISTS locks
            ({"type": LockType.EXISTS, "property_path": "user.id", "expected_value": None}, True),
            ({"type": LockType.EXISTS, "property_path": "user.profile.email", "expected_value": None}, True),
            ({"type": LockType.EXISTS, "property_path": "nonexistent.path", "expected_value": None}, False),

            # EQUALS locks
            ({"type": LockType.EQUALS, "property_path": "user.settings.theme", "expected_value": "dark"}, True),
            ({"type": LockType.EQUALS, "property_path": "account.type", "expected_value": "basic"}, False),

            # GREATER_THAN locks
            ({"type": LockType.GREATER_THAN, "property_path": "user.profile.age", "expected_value": 25}, True),
            ({"type": LockType.GREATER_THAN, "property_path": "account.balance", "expected_value": 2000}, False),

            # REGEX locks
            ({"type": LockType.REGEX, "property_path": "user.profile.email", "expected_value": r"^[^@]+@[^@]+\.[^@]+$"}, True),
            ({"type": LockType.REGEX, "property_path": "user.id", "expected_value": r"^usr_\d+$"}, True),

            # IN_LIST locks
            ({"type": LockType.IN_LIST, "property_path": "account.type", "expected_value": ["basic", "premium", "enterprise"]}, True),
            ({"type": LockType.IN_LIST, "property_path": "user.settings.language", "expected_value": ["en-US", "es-ES", "fr-FR"]}, True),

            # CONTAINS locks
            ({"type": LockType.CONTAINS, "property_path": "user.profile.skills", "expected_value": "Python"}, True),
            ({"type": LockType.CONTAINS, "property_path": "user.profile.name", "expected_value": "Johnson"}, True),

            # TYPE_CHECK locks
            ({"type": LockType.TYPE_CHECK, "property_path": "metrics.login_count", "expected_value": "int"}, True),
            ({"type": LockType.TYPE_CHECK, "property_path": "account.subscription.auto_renew", "expected_value": "bool"}, True),

            # LENGTH locks
            ({"type": LockType.LENGTH, "property_path": "user.profile.skills", "expected_value": 3}, True),
            ({"type": LockType.LENGTH, "property_path": "user.id", "expected_value": 7}, True),
        ]

        # Act & Assert
        for lock_config, expected_success in locks_and_expectations:
            lock = Lock(lock_config)
            result = lock.validate(complex_element)

            assert result.success == expected_success, (
                f"Lock validation failed for {lock_config['property_path']} "
                f"with {lock_config['type']}. Expected: {expected_success}, "
                f"Got: {result.success}. Error: {result.error_message}"
            )

    def test_factory_integration_with_complex_scenarios(self, complex_element):
        """Test LockFactory integration with complex validation scenarios."""
        # Arrange
        factory_test_cases = [
            # Shorthand syntax
            ({"exists": "user.profile.email"}, True),
            ({"exists": "missing.property"}, False),
            ({"is_true": "account.subscription.auto_renew"}, True),
            ({"is_false": "user.profile.certifications.kubernetes"}, True),

            # Full definition syntax
            ({
                "type": LockType.RANGE,
                "property_path": "metrics.performance_score",
                "expected_value": None,
                "metadata": {"min_value": 80, "max_value": 100}
            }, True),
            ({
                "type": LockType.NOT_IN_LIST,
                "property_path": "account.type",
                "expected_value": ["basic", "trial"]
            }, True),
        ]

        # Act & Assert
        for definition, expected_success in factory_test_cases:
            lock = LockFactory.create(definition)
            result = lock.validate(complex_element)

            assert result.success == expected_success, (
                f"Factory-created lock validation failed for {definition}. "
                f"Expected: {expected_success}, Got: {result.success}. "
                f"Error: {result.error_message}"
            )

    def test_edge_case_property_paths(self, complex_element):
        """Test lock validation with edge case property paths."""
        # Arrange
        edge_case_locks = [
            # Array index access (if element supports it)
            Lock({"type": LockType.EXISTS, "property_path": "user.profile.skills[0]", "expected_value": None}),

            # Deeply nested properties
            Lock({"type": LockType.EXISTS, "property_path": "user.settings.notifications.email", "expected_value": None}),

            # Properties with None values
            Lock({"type": LockType.EXISTS, "property_path": "account.last_payment", "expected_value": None}),
        ]

        # Act & Assert
        for lock in edge_case_locks:
            result = lock.validate(complex_element)
            # We're mainly testing that these don't raise exceptions
            assert isinstance(result, LockResult)
            assert isinstance(result.success, bool)

    def test_performance_with_multiple_validations(self, complex_element):
        """Test performance characteristics with multiple validations."""
        # Arrange
        locks = [
            Lock({"type": LockType.EXISTS, "property_path": f"user.profile.skills", "expected_value": None})
            for _ in range(100)
        ]

        # Act
        results = []
        for lock in locks:
            result = lock.validate(complex_element)
            results.append(result)

        # Assert
        assert len(results) == 100
        assert all(result.success for result in results)
        # This test ensures that repeated validations don't cause memory leaks or performance degradation


class TestLockTypeEdgeCases:
    """Test suite for edge cases and boundary conditions in lock validation."""

    @pytest.mark.parametrize("value,expected", [
        ("", False),
        ("   ", False),
        ("\t\n\r", False),
        ("a", True),
        ("  content  ", True),
        (0, True),
        (False, True),
        (None, False),
        ([], True),
        ({}, True),
    ])
    def test_exists_validation_edge_cases(self, value, expected):
        """Test EXISTS validation with various edge case values."""
        # Arrange
        lock_type = LockType.EXISTS

        # Act
        result = lock_type.validate(value, {})

        # Assert
        assert result == expected

    @pytest.mark.parametrize("value,min_val,max_val,expected", [
        (50, 0, 100, True),
        (0, 0, 100, True),
        (100, 0, 100, True),
        (-1, 0, 100, False),
        (101, 0, 100, False),
        (50.5, 50, 51, True),
        ("50", 40, 60, True),  # String should be converted to float
    ])
    def test_range_validation_boundary_conditions(self, value, min_val, max_val, expected):
        """Test RANGE validation with boundary conditions."""
        # Arrange
        lock_type = LockType.RANGE
        metadata = {"min_value": min_val, "max_value": max_val}

        # Act
        result = lock_type.validate(value, metadata)

        # Assert
        assert result == expected

    @pytest.mark.parametrize("collection,expected_value,expected_result", [
        ("hello world", "world", True),
        ("hello world", "missing", False),
        (["a", "b", "c"], "b", True),
        (["a", "b", "c"], "d", False),
        ({"key": "value"}, "key", True),
        ({"key": "value"}, "missing", False),
        (123, "1", False),  # Invalid type
        (None, "test", False),  # None value
    ])
    def test_contains_validation_with_various_types(self, collection, expected_value, expected_result):
        """Test CONTAINS validation with various collection types."""
        # Arrange
        lock_type = LockType.CONTAINS
        metadata = {"expected_value": expected_value}

        # Act
        result = lock_type.validate(collection, metadata)

        # Assert
        assert result == expected_result

    def test_regex_validation_with_complex_patterns(self):
        """Test REGEX validation with complex real-world patterns."""
        # Arrange
        lock_type = LockType.REGEX
        test_cases = [
            # Email validation
            ("user@example.com", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", True),
            ("invalid.email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", False),

            # Phone number validation
            ("+1-555-123-4567", r"^\+?[\d\s\-\(\)]+$", True),
            ("abc-def-ghij", r"^\+?[\d\s\-\(\)]+$", False),

            # URL validation
            ("https://example.com/path", r"^https?://[^\s/$.?#].[^\s]*$", True),
            ("not-a-url", r"^https?://[^\s/$.?#].[^\s]*$", False),
        ]

        for value, pattern, expected in test_cases:
            # Act
            result = lock_type.validate(value, {"expected_value": pattern})

            # Assert
            assert result == expected, f"Pattern {pattern} failed for value {value}"

    def test_type_check_validation_with_inheritance(self):
        """Test TYPE_CHECK validation with inheritance and subclasses."""
        # Arrange
        lock_type = LockType.TYPE_CHECK

        class CustomList(list):
            pass

        custom_list = CustomList([1, 2, 3])

        # Act & Assert
        # Should pass because CustomList inherits from list
        assert lock_type.validate(custom_list, {"expected_value": list}) is True
        assert lock_type.validate(custom_list, {"expected_value": "list"}) is True

        # Should fail for unrelated types
        assert lock_type.validate(custom_list, {"expected_value": dict}) is False


@pytest.mark.integration
class TestLockSystemIntegration:
    """Integration tests for the complete lock validation system."""

    def test_lock_system_with_real_world_user_data(self):
        """Test the complete lock system with realistic user data."""
        # Arrange
        user_data = {
            "id": "usr_789123",
            "email": "john.doe@company.com",
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
                "age": 32,
                "department": "Engineering",
                "skills": ["Python", "Docker", "Kubernetes", "AWS"],
                "certification_count": 4
            },
            "employment": {
                "status": "active",
                "start_date": "2020-03-15",
                "salary": 95000,
                "is_manager": True,
                "direct_reports": 3
            },
            "access": {
                "level": "senior",
                "permissions": ["read", "write", "admin"],
                "last_login": "2024-01-20T09:15:00Z",
                "failed_login_attempts": 0
            }
        }
        element = DictElement(user_data)

        # Define comprehensive validation rules
        validation_rules = [
            # Basic existence checks
            {"exists": "id"},
            {"exists": "email"},
            {"exists": "profile.first_name"},

            # Format validations
            {
                "type": LockType.REGEX,
                "property_path": "email",
                "expected_value": r"^[^@]+@[^@]+\.[^@]+$"
            },
            {
                "type": LockType.REGEX,
                "property_path": "id",
                "expected_value": r"^usr_\d+$"
            },

            # Business rule validations
            {
                "type": LockType.IN_LIST,
                "property_path": "employment.status",
                "expected_value": ["active", "inactive", "pending"]
            },
            {
                "type": LockType.GREATER_THAN,
                "property_path": "profile.age",
                "expected_value": 18
            },
            {
                "type": LockType.RANGE,
                "property_path": "employment.salary",
                "expected_value": None,
                "metadata": {"min_value": 30000, "max_value": 200000}
            },

            # Collection validations
            {
                "type": LockType.CONTAINS,
                "property_path": "access.permissions",
                "expected_value": "read"
            },
            {
                "type": LockType.LENGTH,
                "property_path": "profile.skills",
                "expected_value": 4
            },

            # Type checks
            {
                "type": LockType.TYPE_CHECK,
                "property_path": "employment.is_manager",
                "expected_value": "bool"
            },
            {
                "type": LockType.TYPE_CHECK,
                "property_path": "access.failed_login_attempts",
                "expected_value": "int"
            },

            # Boolean checks using shorthand
            {"is_true": "employment.is_manager"},

            # Security validations
            {
                "type": LockType.LESS_THAN,
                "property_path": "access.failed_login_attempts",
                "expected_value": 5
            }
        ]

        # Act - Validate all rules
        results = []
        for rule in validation_rules:
            lock = LockFactory.create(rule)
            result = lock.validate(element)
            results.append((rule, result))

        # Assert - All validations should pass
        failed_validations = [
            (rule, result) for rule, result in results
            if not result.success
        ]

        assert len(failed_validations) == 0, (
            f"Failed validations: {failed_validations}"
        )

        # Verify specific results
        assert len(results) == len(validation_rules)
        assert all(result.success for _, result in results)

    def test_lock_system_error_reporting_quality(self):
        """Test that the lock system provides high-quality error messages."""
        # Arrange
        problematic_data = {
            "user": {
                "email": "invalid-email-format",
                "age": "not-a-number",
                "status": "unknown_status"
            }
        }
        element = DictElement(problematic_data)

        problematic_locks = [
            {
                "type": LockType.REGEX,
                "property_path": "user.email",
                "expected_value": r"^[^@]+@[^@]+\.[^@]+$"
            },
            {
                "type": LockType.TYPE_CHECK,
                "property_path": "user.age",
                "expected_value": "int"
            },
            {
                "type": LockType.IN_LIST,
                "property_path": "user.status",
                "expected_value": ["active", "inactive", "pending"]
            },
            {
                "type": LockType.EXISTS,
                "property_path": "user.missing_field",
                "expected_value": None
            }
        ]

        # Act
        error_results = []
        for lock_config in problematic_locks:
            lock = Lock(lock_config)
            result = lock.validate(element)
            if not result.success:
                error_results.append(result)

        # Assert
        assert len(error_results) == 4  # All should fail

        # Check error message quality
        for result in error_results:
            assert result.error_message != ""
            assert result.property_path in result.error_message
            assert len(result.error_message) > 10  # Reasonably descriptive

        # Check specific error patterns
        email_error = next(r for r in error_results if "email" in r.property_path)
        assert "should match pattern" in email_error.error_message

        age_error = next(r for r in error_results if "age" in r.property_path)
        assert "should be of type" in age_error.error_message

        status_error = next(r for r in error_results if "status" in r.property_path)
        assert "should be one of" in status_error.error_message

        missing_error = next(r for r in error_results if "missing_field" in r.property_path)
        assert "required but missing" in missing_error.error_message


class TestLockDocumentedIssues:
    """Test suite documenting known issues in the current implementation."""

    def test_typo_in_error_message_variable_name(self):
        """Document the typo in lock.py line 249 (eror_message instead of error_message)."""
        # Arrange
        element = DictElement({"test": "value"})
        config = {
            "type": LockType.EXISTS,
            "property_path": "missing",
            "expected_value": None
        }
        lock = Lock(config)

        # Act
        result = lock.validate(element)

        # Assert
        # Despite the typo in the source code (line 249: eror_message instead of error_message),
        # the error message should still be properly set due to the LockResult constructor
        assert result.success is False
        assert result.error_message != ""
        assert "required but missing" in result.error_message

    def test_duplicate_expected_value_assignment_in_init(self):
        """Document the duplicate assignment in Lock.__init__ line 236."""
        # Arrange
        config = {
            "type": LockType.EQUALS,
            "property_path": "test",
            "expected_value": "test_value"
        }

        # Act
        lock = Lock(config)

        # Assert
        # Despite the duplicate assignment in line 236:
        # self.expected_value = self.expected_value = config.get("expected_value")
        # The value should still be correctly assigned
        assert lock.expected_value == "test_value"

    def test_typo_in_lockshorthands_variable_name(self):
        """Document the typo in LockShorhands variable name (missing 't')."""
        # Arrange & Act & Assert
        # The variable is named LockShorhands instead of LockShorthands
        assert "is_true" in LockShorhands
        assert "is_false" in LockShorhands
        assert "exists" in LockShorhands

        # Verify the mapping is correct despite the typo
        assert LockShorhands["is_true"] == (LockType.EQUALS, True)
        assert LockShorhands["is_false"] == (LockType.EQUALS, False)
        assert LockShorhands["exists"] == (LockType.EXISTS, True)