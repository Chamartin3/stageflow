"""Unit tests for StageFlow lock validation system."""

from typing import Any

import pytest

from stageflow.core.element import DictElement
from stageflow.gates import (
    Lock,
    LockType,
    get_lock_validator as get_validator,
    list_lock_validators as list_validators,
    register_lock_validator as register_validator,
    clear_lock_validators,
)
from stageflow.gates.lock import LockFactory


class TestLockType:
    """Test LockType enumeration and basic functionality."""

    def test_lock_type_values(self):
        """Test that all required lock types are defined."""
        required_types = {
            "exists", "equals", "greater_than", "less_than", "contains",
            "regex", "type_check", "range", "length", "not_empty",
            "in_list", "not_in_list", "custom"
        }
        actual_types = {lock_type.value for lock_type in LockType}
        assert required_types == actual_types


class TestCustomValidatorRegistry:
    """Test custom validator registration and retrieval."""

    def setup_method(self):
        """Clear validators before each test."""
        clear_lock_validators()

    def test_register_validator(self):
        """Test registering a custom validator."""
        def email_validator(value, expected):
            return isinstance(value, str) and "@" in value

        register_validator("email", email_validator)
        assert "email" in list_validators()
        assert get_validator("email") is email_validator

    def test_get_nonexistent_validator(self):
        """Test getting a validator that doesn't exist."""
        assert get_validator("nonexistent") is None

    def test_overwrite_validator(self):
        """Test overwriting an existing validator."""
        def validator1(value, expected):
            return True

        def validator2(value, expected):
            return False

        register_validator("test", validator1)
        register_validator("test", validator2)

        assert get_validator("test") is validator2

    def test_list_validators_empty(self):
        """Test listing validators when none are registered."""
        assert list_validators() == []


class TestLockValidation:
    """Test lock validation logic for all lock types."""

    def create_element(self, data: dict[str, Any]) -> DictElement:
        """Helper to create test elements."""
        return DictElement(data)

    def test_exists_validation(self):
        """Test EXISTS lock type validation."""
        element = self.create_element({"name": "John", "empty": "", "null": None})

        # Property exists and has value
        lock = Lock(LockType.EXISTS, "name", True)
        result = lock.validate(element)
        assert result.success is True

        # Property is empty string
        lock = Lock(LockType.EXISTS, "empty", True)
        result = lock.validate(element)
        assert result.success is False

        # Property is None
        lock = Lock(LockType.EXISTS, "null", True)
        result = lock.validate(element)
        assert result.success is False

        # Property doesn't exist
        lock = Lock(LockType.EXISTS, "missing", True)
        result = lock.validate(element)
        assert result.success is False

        # Check for non-existence
        lock = Lock(LockType.EXISTS, "missing", False)
        result = lock.validate(element)
        assert result.success is True

    def test_equals_validation(self):
        """Test EQUALS lock type validation."""
        element = self.create_element({"age": 25, "name": "John"})

        # Successful equality
        lock = Lock(LockType.EQUALS, "age", 25)
        result = lock.validate(element)
        assert result.success is True

        # Failed equality
        lock = Lock(LockType.EQUALS, "age", 30)
        result = lock.validate(element)
        assert result.success is False

        # String equality
        lock = Lock(LockType.EQUALS, "name", "John")
        result = lock.validate(element)
        assert result.success is True

        # Missing property
        lock = Lock(LockType.EQUALS, "missing", "value")
        result = lock.validate(element)
        assert result.success is False

    def test_greater_than_validation(self):
        """Test GREATER_THAN lock type validation."""
        element = self.create_element({"age": 25, "price": 19.99, "invalid": "text"})

        # Successful comparison
        lock = Lock(LockType.GREATER_THAN, "age", 20)
        result = lock.validate(element)
        assert result.success is True

        # Failed comparison
        lock = Lock(LockType.GREATER_THAN, "age", 30)
        result = lock.validate(element)
        assert result.success is False

        # Float comparison
        lock = Lock(LockType.GREATER_THAN, "price", 15.0)
        result = lock.validate(element)
        assert result.success is True

        # Invalid type
        lock = Lock(LockType.GREATER_THAN, "invalid", 10)
        result = lock.validate(element)
        assert result.success is False

        # Missing property
        lock = Lock(LockType.GREATER_THAN, "missing", 10)
        result = lock.validate(element)
        assert result.success is False

    def test_less_than_validation(self):
        """Test LESS_THAN lock type validation."""
        element = self.create_element({"age": 25, "price": 19.99})

        # Successful comparison
        lock = Lock(LockType.LESS_THAN, "age", 30)
        result = lock.validate(element)
        assert result.success is True

        # Failed comparison
        lock = Lock(LockType.LESS_THAN, "age", 20)
        result = lock.validate(element)
        assert result.success is False

        # Float comparison
        lock = Lock(LockType.LESS_THAN, "price", 25.0)
        result = lock.validate(element)
        assert result.success is True

    def test_contains_validation(self):
        """Test CONTAINS lock type validation."""
        element = self.create_element({
            "email": "user@example.com",
            "tags": ["python", "testing", "stageflow"],
            "numbers": [1, 2, 3],
            "invalid": 123
        })

        # String contains substring
        lock = Lock(LockType.CONTAINS, "email", "@")
        result = lock.validate(element)
        assert result.success is True

        # String doesn't contain substring
        lock = Lock(LockType.CONTAINS, "email", "xyz")
        result = lock.validate(element)
        assert result.success is False

        # List contains element
        lock = Lock(LockType.CONTAINS, "tags", "python")
        result = lock.validate(element)
        assert result.success is True

        # List doesn't contain element
        lock = Lock(LockType.CONTAINS, "tags", "java")
        result = lock.validate(element)
        assert result.success is False

        # Numbers list
        lock = Lock(LockType.CONTAINS, "numbers", 2)
        result = lock.validate(element)
        assert result.success is True

        # Invalid type for contains
        lock = Lock(LockType.CONTAINS, "invalid", "test")
        result = lock.validate(element)
        assert result.success is False

    def test_regex_validation(self):
        """Test REGEX lock type validation."""
        element = self.create_element({
            "email": "user@example.com",
            "phone": "123-456-7890",
            "invalid": 123
        })

        # Valid email regex
        lock = Lock(LockType.REGEX, "email", r".+@.+\..+")
        result = lock.validate(element)
        assert result.success is True

        # Invalid email regex
        lock = Lock(LockType.REGEX, "email", r"^\d+$")
        result = lock.validate(element)
        assert result.success is False

        # Phone number regex
        lock = Lock(LockType.REGEX, "phone", r"\d{3}-\d{3}-\d{4}")
        result = lock.validate(element)
        assert result.success is True

        # Invalid regex pattern
        lock = Lock(LockType.REGEX, "email", "[")
        result = lock.validate(element)
        assert result.success is False

        # Non-string value
        lock = Lock(LockType.REGEX, "invalid", r"\d+")
        result = lock.validate(element)
        assert result.success is False

    def test_type_check_validation(self):
        """Test TYPE_CHECK lock type validation."""
        element = self.create_element({
            "name": "John",
            "age": 25,
            "score": 98.5,
            "active": True,
            "tags": ["python", "testing"],
            "profile": {"bio": "Developer"}
        })

        # String type check
        lock = Lock(LockType.TYPE_CHECK, "name", str)
        result = lock.validate(element)
        assert result.success is True

        lock = Lock(LockType.TYPE_CHECK, "name", "str")
        result = lock.validate(element)
        assert result.success is True

        # Integer type check
        lock = Lock(LockType.TYPE_CHECK, "age", int)
        result = lock.validate(element)
        assert result.success is True

        lock = Lock(LockType.TYPE_CHECK, "age", "integer")
        result = lock.validate(element)
        assert result.success is True

        # Float type check
        lock = Lock(LockType.TYPE_CHECK, "score", float)
        result = lock.validate(element)
        assert result.success is True

        # Boolean type check
        lock = Lock(LockType.TYPE_CHECK, "active", bool)
        result = lock.validate(element)
        assert result.success is True

        # List type check
        lock = Lock(LockType.TYPE_CHECK, "tags", list)
        result = lock.validate(element)
        assert result.success is True

        # Dict type check
        lock = Lock(LockType.TYPE_CHECK, "profile", dict)
        result = lock.validate(element)
        assert result.success is True

        # Failed type check
        lock = Lock(LockType.TYPE_CHECK, "name", int)
        result = lock.validate(element)
        assert result.success is False

        # Unknown string type
        lock = Lock(LockType.TYPE_CHECK, "name", "unknown")
        result = lock.validate(element)
        assert result.success is False

        # Invalid expected value
        lock = Lock(LockType.TYPE_CHECK, "name", 123)
        result = lock.validate(element)
        assert result.success is False

    def test_range_validation(self):
        """Test RANGE lock type validation."""
        element = self.create_element({
            "age": 25,
            "score": 85.5,
            "invalid": "text"
        })

        # Successful range check
        lock = Lock(LockType.RANGE, "age", [18, 65])
        result = lock.validate(element)
        assert result.success is True

        # Failed range check (too low)
        lock = Lock(LockType.RANGE, "age", [30, 65])
        result = lock.validate(element)
        assert result.success is False

        # Failed range check (too high)
        lock = Lock(LockType.RANGE, "age", [10, 20])
        result = lock.validate(element)
        assert result.success is False

        # Float range check
        lock = Lock(LockType.RANGE, "score", [80.0, 90.0])
        result = lock.validate(element)
        assert result.success is True

        # Boundary values
        lock = Lock(LockType.RANGE, "age", [25, 25])
        result = lock.validate(element)
        assert result.success is True

        # Invalid range format
        lock = Lock(LockType.RANGE, "age", [10])
        result = lock.validate(element)
        assert result.success is False

        # Invalid value type
        lock = Lock(LockType.RANGE, "invalid", [10, 20])
        result = lock.validate(element)
        assert result.success is False

    def test_length_validation(self):
        """Test LENGTH lock type validation."""
        element = self.create_element({
            "name": "John",
            "tags": ["a", "b", "c"],
            "empty": "",
            "invalid": 123
        })

        # Exact length
        lock = Lock(LockType.LENGTH, "name", 4)
        result = lock.validate(element)
        assert result.success is True

        # Wrong length
        lock = Lock(LockType.LENGTH, "name", 5)
        result = lock.validate(element)
        assert result.success is False

        # List length
        lock = Lock(LockType.LENGTH, "tags", 3)
        result = lock.validate(element)
        assert result.success is True

        # Min/max dict format
        lock = Lock(LockType.LENGTH, "name", {"min": 3, "max": 5})
        result = lock.validate(element)
        assert result.success is True

        lock = Lock(LockType.LENGTH, "name", {"min": 5, "max": 10})
        result = lock.validate(element)
        assert result.success is False

        # Only min constraint
        lock = Lock(LockType.LENGTH, "name", {"min": 3})
        result = lock.validate(element)
        assert result.success is True

        # Only max constraint
        lock = Lock(LockType.LENGTH, "name", {"max": 5})
        result = lock.validate(element)
        assert result.success is True

        # Range format [min, max]
        lock = Lock(LockType.LENGTH, "name", [3, 5])
        result = lock.validate(element)
        assert result.success is True

        # Empty string
        lock = Lock(LockType.LENGTH, "empty", 0)
        result = lock.validate(element)
        assert result.success is True

        # Invalid type for length
        lock = Lock(LockType.LENGTH, "invalid", 3)
        result = lock.validate(element)
        assert result.success is False

    def test_not_empty_validation(self):
        """Test NOT_EMPTY lock type validation."""
        element = self.create_element({
            "name": "John",
            "empty_str": "",
            "whitespace": "   ",
            "empty_list": [],
            "list_with_items": ["item"],
            "null": None
        })

        # Non-empty string
        lock = Lock(LockType.NOT_EMPTY, "name")
        result = lock.validate(element)
        assert result.success is True

        # Empty string
        lock = Lock(LockType.NOT_EMPTY, "empty_str")
        result = lock.validate(element)
        assert result.success is False

        # Whitespace-only string
        lock = Lock(LockType.NOT_EMPTY, "whitespace")
        result = lock.validate(element)
        assert result.success is False

        # Empty list
        lock = Lock(LockType.NOT_EMPTY, "empty_list")
        result = lock.validate(element)
        assert result.success is False

        # Non-empty list
        lock = Lock(LockType.NOT_EMPTY, "list_with_items")
        result = lock.validate(element)
        assert result.success is True

        # Null value
        lock = Lock(LockType.NOT_EMPTY, "null")
        result = lock.validate(element)
        assert result.success is False

    def test_in_list_validation(self):
        """Test IN_LIST lock type validation."""
        element = self.create_element({
            "status": "active",
            "priority": 1,
            "category": "unknown"
        })

        # Value in list
        lock = Lock(LockType.IN_LIST, "status", ["active", "inactive", "pending"])
        result = lock.validate(element)
        assert result.success is True

        # Value not in list
        lock = Lock(LockType.IN_LIST, "category", ["high", "medium", "low"])
        result = lock.validate(element)
        assert result.success is False

        # Number in list
        lock = Lock(LockType.IN_LIST, "priority", [1, 2, 3])
        result = lock.validate(element)
        assert result.success is True

    def test_not_in_list_validation(self):
        """Test NOT_IN_LIST lock type validation."""
        element = self.create_element({
            "username": "admin",
            "role": "user"
        })

        # Value not in blocked list
        lock = Lock(LockType.NOT_IN_LIST, "role", ["admin", "superuser"])
        result = lock.validate(element)
        assert result.success is True

        # Value in blocked list
        lock = Lock(LockType.NOT_IN_LIST, "username", ["admin", "root"])
        result = lock.validate(element)
        assert result.success is False

    def test_custom_validation(self):
        """Test CUSTOM lock type validation."""
        def email_validator(value, expected):
            return isinstance(value, str) and "@" in value

        def length_validator(value, expected):
            return len(str(value)) >= expected

        register_validator("email", email_validator)
        register_validator("min_length", length_validator)

        element = self.create_element({
            "email": "user@example.com",
            "name": "John",
            "invalid_email": "notanemail"
        })

        # Valid custom validation
        lock = Lock(LockType.CUSTOM, "email", validator_name="email")
        result = lock.validate(element)
        assert result.success is True

        # Invalid custom validation
        lock = Lock(LockType.CUSTOM, "invalid_email", validator_name="email")
        result = lock.validate(element)
        assert result.success is False

        # Custom validation with expected value
        lock = Lock(LockType.CUSTOM, "name", 3, validator_name="min_length")
        result = lock.validate(element)
        assert result.success is True

        # Nonexistent validator
        lock = Lock(LockType.CUSTOM, "name", validator_name="nonexistent")
        result = lock.validate(element)
        assert result.success is False

    def test_lock_initialization_validation(self):
        """Test lock initialization validation."""
        # Valid lock
        lock = Lock(LockType.EXISTS, "name")
        assert lock.metadata == {}

        # Lock requiring expected_value
        with pytest.raises(ValueError, match="requires expected_value"):
            Lock(LockType.EQUALS, "name")

        # Custom lock requiring validator_name
        with pytest.raises(ValueError, match="requires validator_name"):
            Lock(LockType.CUSTOM, "name")

        # Lock with metadata
        lock = Lock(LockType.EXISTS, "name", metadata={"description": "test"})
        assert lock.metadata["description"] == "test"


class TestLockErrorMessages:
    """Test lock error message generation."""

    def create_element(self, data: dict[str, Any]) -> DictElement:
        """Helper to create test elements."""
        return DictElement(data)

    def test_failure_messages(self):
        """Test various failure message generation."""
        element = self.create_element({
            "name": "John",
            "age": 15,
            "email": "invalid",
            "tags": ["python"]
        })

        # EXISTS failure
        lock = Lock(LockType.EXISTS, "missing", True)
        msg = lock.get_failure_message(element)
        assert "required but missing" in msg

        # EQUALS failure
        lock = Lock(LockType.EQUALS, "name", "Jane")
        msg = lock.get_failure_message(element)
        assert "should equal 'Jane'" in msg

        # GREATER_THAN failure
        lock = Lock(LockType.GREATER_THAN, "age", 18)
        msg = lock.get_failure_message(element)
        assert "should be greater than 18" in msg

        # CONTAINS failure
        lock = Lock(LockType.CONTAINS, "email", "@")
        msg = lock.get_failure_message(element)
        assert "should contain '@'" in msg

        # TYPE_CHECK failure
        lock = Lock(LockType.TYPE_CHECK, "age", str)
        msg = lock.get_failure_message(element)
        assert "should be of type 'str'" in msg

    def test_action_messages(self):
        """Test action message generation."""
        element = self.create_element({"name": "John", "age": 15})

        # EXISTS action
        lock = Lock(LockType.EXISTS, "missing", True)
        msg = lock.get_action_message(element)
        assert "Set missing field" in msg

        # EQUALS action
        lock = Lock(LockType.EQUALS, "name", "Jane")
        msg = lock.get_action_message(element)
        assert "Set name to 'Jane'" in msg

        # RANGE action
        lock = Lock(LockType.RANGE, "age", [18, 65])
        msg = lock.get_action_message(element)
        assert "between 18 and 65" in msg


class TestLockFactory:
    """Test LockFactory for simplified lock syntax support."""

    def test_shorthand_exists_syntax(self):
        """Test shorthand exists syntax parsing."""
        lock_def = {"exists": "email"}
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.EXISTS
        assert lock.property_path == "email"
        assert lock.expected_value is None

    def test_shorthand_is_true_syntax(self):
        """Test shorthand is_true syntax parsing."""
        lock_def = {"is_true": "verified"}
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "verified"
        assert lock.expected_value is True

    def test_shorthand_is_false_syntax(self):
        """Test shorthand is_false syntax parsing."""
        lock_def = {"is_false": "banned"}
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.EQUALS
        assert lock.property_path == "banned"
        assert lock.expected_value is False

    def test_complex_regex_syntax(self):
        """Test complex regex syntax parsing."""
        lock_def = {
            "regex": {
                "property_path": "email",
                "value": r"^[^@]+@[^@]+\.[^@]+$"
            }
        }
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.REGEX
        assert lock.property_path == "email"
        assert lock.expected_value == r"^[^@]+@[^@]+\.[^@]+$"

    def test_complex_range_syntax(self):
        """Test complex range syntax parsing."""
        lock_def = {
            "range": {
                "property_path": "age",
                "min": 18,
                "max": 120
            }
        }
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.RANGE
        assert lock.property_path == "age"
        assert lock.expected_value == [18, 120]

    def test_legacy_syntax_backward_compatibility(self):
        """Test that legacy verbose syntax still works."""
        lock_def = {
            "property_path": "name",
            "lock_type": "exists"
        }
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.EXISTS
        assert lock.property_path == "name"

    def test_legacy_syntax_with_type_field(self):
        """Test legacy syntax with 'type' field."""
        lock_def = {
            "property": "email",
            "type": "regex",
            "value": r"^[^@]+@[^@]+\.[^@]+$"
        }
        lock = LockFactory.create_lock(lock_def)

        assert lock.lock_type == LockType.REGEX
        assert lock.property_path == "email"
        assert lock.expected_value == r"^[^@]+@[^@]+\.[^@]+$"

    def test_invalid_shorthand_syntax(self):
        """Test error handling for invalid shorthand syntax."""
        # Multiple keys
        with pytest.raises(ValueError, match="Unsupported lock definition format"):
            LockFactory.create_lock({"exists": "email", "is_true": "verified"})

        # Invalid shorthand key
        with pytest.raises(ValueError, match="Unknown shorthand key"):
            LockFactory.create_lock({"invalid": "property"})

    def test_invalid_complex_syntax(self):
        """Test error handling for invalid complex syntax."""
        # Missing required fields
        with pytest.raises(ValueError, match="requires 'property_path' and 'value'"):
            LockFactory.create_lock({"regex": {"value": "pattern"}})

        # Invalid complex key
        with pytest.raises(ValueError, match="Unknown complex key"):
            LockFactory.create_lock({"invalid": {"property_path": "test"}})

    def test_string_shorthand_not_implemented(self):
        """Test that string shorthand raises error (not implemented)."""
        with pytest.raises(ValueError, match="String shorthand syntax not yet supported"):
            LockFactory.create_lock("exists:email")

    def test_mixed_syntax_validation(self):
        """Test that different syntax formats produce equivalent locks."""
        # Shorthand
        shorthand_lock = LockFactory.create_lock({"exists": "email"})

        # Legacy
        legacy_lock = LockFactory.create_lock({
            "property_path": "email",
            "lock_type": "exists"
        })

        # Complex (not applicable for exists)
        # But they should be equivalent
        assert shorthand_lock.lock_type == legacy_lock.lock_type
        assert shorthand_lock.property_path == legacy_lock.property_path
        assert shorthand_lock.expected_value == legacy_lock.expected_value

    def test_complex_syntax_with_min_max_range(self):
        """Test range syntax with only min or only max."""
        # Only min
        lock_def = {
            "range": {
                "property_path": "age",
                "min": 18
            }
        }
        lock = LockFactory.create_lock(lock_def)
        assert lock.expected_value == [18, None]

        # Only max
        lock_def = {
            "range": {
                "property_path": "age",
                "max": 120
            }
        }
        lock = LockFactory.create_lock(lock_def)
        assert lock.expected_value == [None, 120]


if __name__ == "__main__":
    pytest.main([__file__])
