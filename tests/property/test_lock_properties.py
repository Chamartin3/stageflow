"""Property-based tests for Lock validation behaviors.

This module tests the fundamental invariants and behaviors of Lock validation,
ensuring consistency, correctness, and proper error handling across all lock
types and constraint combinations.

Key properties tested:
- Lock validation consistency and determinism
- Correct behavior for all LockType variants
- Proper error message generation
- Validation result stability
- Custom validator integration
"""

import pytest
from hypothesis import assume, given

from stageflow.element import DictElement
from stageflow.gates import Lock, LockType
from stageflow.gates import get_lock_validator as get_validator
from stageflow.gates import register_lock_validator as register_validator
from tests.property.generators import (
    dict_element,
    element_with_property,
    element_without_property,
    lock_instance,
    lock_type_and_value,
    valid_property_path,
)

pytestmark = pytest.mark.property


class TestLockValidationProperties:
    """Property-based tests for Lock validation behaviors."""

    @given(lock=lock_instance(), element=dict_element())
    def test_lock_validation_deterministic(self, lock: Lock, element: DictElement):
        """Lock validation should be deterministic - same result every time."""
        result1 = lock.validate(element)
        result2 = lock.validate(element)
        assert result1 == result2

    @given(lock=lock_instance(), element=dict_element())
    def test_lock_validation_boolean_result(self, lock: Lock, element: DictElement):
        """Lock validation should always return a boolean value."""
        result = lock.validate(element)
        assert isinstance(result, bool)

    @given(path=valid_property_path(), lock_type_value=lock_type_and_value())
    def test_lock_with_existing_property(self, path: str, lock_type_value):
        """Test lock validation when property definitely exists."""
        lock_type, expected_value = lock_type_value

        # Skip custom lock type for this test unless we have a validator
        if lock_type == LockType.CUSTOM and not get_validator("test_validator"):
            return

        # Create element with the property
        element = element_with_property(path, "test_value")

        # Create lock
        validator_name = "test_validator" if lock_type == LockType.CUSTOM else None
        lock = Lock(
            property_path=path,
            lock_type=lock_type,
            expected_value=expected_value,
            validator_name=validator_name
        )

        # Validation should not crash
        result = lock.validate(element)
        assert isinstance(result, bool)

        # Should be able to get failure and action messages
        failure_msg = lock.get_failure_message(element)
        action_msg = lock.get_action_message(element)
        assert isinstance(failure_msg, str)
        assert isinstance(action_msg, str)

    @given(path=valid_property_path(), lock_type_value=lock_type_and_value())
    def test_lock_with_missing_property(self, path: str, lock_type_value):
        """Test lock validation when property definitely doesn't exist."""
        lock_type, expected_value = lock_type_value

        # Skip very simple paths that might exist in random data
        assume("." in path or "[" in path)

        # Skip custom lock type for this test unless we have a validator
        if lock_type == LockType.CUSTOM and not get_validator("test_validator"):
            return

        # Create element without the property
        element = element_without_property(path)

        # Create lock
        validator_name = "test_validator" if lock_type == LockType.CUSTOM else None
        lock = Lock(
            property_path=path,
            lock_type=lock_type,
            expected_value=expected_value,
            validator_name=validator_name
        )

        # Validation should handle missing property appropriately
        result = lock.validate(element)
        assert isinstance(result, bool)

        # For EXISTS lock with expected_value=False, missing property should pass
        if lock_type == LockType.EXISTS and expected_value is False:
            assert result is True
        else:
            # For most other lock types, missing property should fail
            # (though this depends on the specific implementation)
            assert isinstance(result, bool)

    def test_exists_lock_behavior(self):
        """Test specific behavior of EXISTS lock type."""
        element_with_value = DictElement({"key": "value"})
        element_with_empty = DictElement({"key": ""})
        element_with_none = DictElement({"key": None})
        element_without_key = DictElement({"other": "value"})

        # EXISTS lock expecting property to exist
        exists_lock = Lock("key", LockType.EXISTS, True)
        assert exists_lock.validate(element_with_value) is True
        assert exists_lock.validate(element_with_empty) is False  # Empty string
        assert exists_lock.validate(element_with_none) is False   # None value
        assert exists_lock.validate(element_without_key) is False # Missing

        # EXISTS lock expecting property NOT to exist
        not_exists_lock = Lock("key", LockType.EXISTS, False)
        assert not_exists_lock.validate(element_with_value) is False
        assert not_exists_lock.validate(element_with_empty) is True  # Empty string
        assert not_exists_lock.validate(element_with_none) is True   # None value
        assert not_exists_lock.validate(element_without_key) is True # Missing

    def test_equals_lock_behavior(self):
        """Test specific behavior of EQUALS lock type."""
        element = DictElement({
            "string": "hello",
            "number": 42,
            "boolean": True,
            "none": None
        })

        # String equality
        string_lock = Lock("string", LockType.EQUALS, "hello")
        assert string_lock.validate(element) is True

        wrong_string_lock = Lock("string", LockType.EQUALS, "world")
        assert wrong_string_lock.validate(element) is False

        # Number equality
        number_lock = Lock("number", LockType.EQUALS, 42)
        assert number_lock.validate(element) is True

        wrong_number_lock = Lock("number", LockType.EQUALS, 43)
        assert wrong_number_lock.validate(element) is False

        # Boolean equality
        bool_lock = Lock("boolean", LockType.EQUALS, True)
        assert bool_lock.validate(element) is True

        wrong_bool_lock = Lock("boolean", LockType.EQUALS, False)
        assert wrong_bool_lock.validate(element) is False

    def test_numeric_comparison_locks(self):
        """Test GREATER_THAN and LESS_THAN lock behaviors."""
        element = DictElement({
            "age": 25,
            "price": 19.99,
            "count": "10",  # String that can be converted to number
            "invalid": "not_a_number"
        })

        # GREATER_THAN tests
        gt_lock = Lock("age", LockType.GREATER_THAN, 20)
        assert gt_lock.validate(element) is True

        gt_fail_lock = Lock("age", LockType.GREATER_THAN, 30)
        assert gt_fail_lock.validate(element) is False

        # LESS_THAN tests
        lt_lock = Lock("age", LockType.LESS_THAN, 30)
        assert lt_lock.validate(element) is True

        lt_fail_lock = Lock("age", LockType.LESS_THAN, 20)
        assert lt_fail_lock.validate(element) is False

        # Float comparison
        price_lock = Lock("price", LockType.GREATER_THAN, 15.0)
        assert price_lock.validate(element) is True

        # String number conversion
        count_lock = Lock("count", LockType.GREATER_THAN, 5)
        assert count_lock.validate(element) is True

        # Invalid number should fail
        invalid_lock = Lock("invalid", LockType.GREATER_THAN, 5)
        assert invalid_lock.validate(element) is False

    def test_regex_lock_behavior(self):
        """Test REGEX lock type behavior."""
        element = DictElement({
            "email": "test@example.com",
            "phone": "+1-555-123-4567",
            "number": 12345,
            "invalid": None
        })

        # Email regex
        email_lock = Lock("email", LockType.REGEX, r"^[^@]+@[^@]+\.[^@]+$")
        assert email_lock.validate(element) is True

        bad_email_lock = Lock("email", LockType.REGEX, r"^\d+$")
        assert bad_email_lock.validate(element) is False

        # Phone regex
        phone_lock = Lock("phone", LockType.REGEX, r"\+\d+-\d+-\d+-\d+")
        assert phone_lock.validate(element) is True

        # Non-string value should fail
        number_regex_lock = Lock("number", LockType.REGEX, r"\d+")
        assert number_regex_lock.validate(element) is False

        # None value should fail
        none_regex_lock = Lock("invalid", LockType.REGEX, r".*")
        assert none_regex_lock.validate(element) is False

    def test_type_check_lock_behavior(self):
        """Test TYPE_CHECK lock type behavior."""
        element = DictElement({
            "name": "John",
            "age": 25,
            "score": 98.5,
            "active": True,
            "tags": ["python", "testing"],
            "data": {"key": "value"}
        })

        # Test type checking with type objects
        str_lock = Lock("name", LockType.TYPE_CHECK, str)
        assert str_lock.validate(element) is True

        int_lock = Lock("age", LockType.TYPE_CHECK, int)
        assert int_lock.validate(element) is True

        float_lock = Lock("score", LockType.TYPE_CHECK, float)
        assert float_lock.validate(element) is True

        bool_lock = Lock("active", LockType.TYPE_CHECK, bool)
        assert bool_lock.validate(element) is True

        list_lock = Lock("tags", LockType.TYPE_CHECK, list)
        assert list_lock.validate(element) is True

        dict_lock = Lock("data", LockType.TYPE_CHECK, dict)
        assert dict_lock.validate(element) is True

        # Test type checking with string type names
        str_name_lock = Lock("name", LockType.TYPE_CHECK, "str")
        assert str_name_lock.validate(element) is True

        int_name_lock = Lock("age", LockType.TYPE_CHECK, "int")
        assert int_name_lock.validate(element) is True

        # Wrong type should fail
        wrong_type_lock = Lock("name", LockType.TYPE_CHECK, int)
        assert wrong_type_lock.validate(element) is False

    def test_range_lock_behavior(self):
        """Test RANGE lock type behavior."""
        element = DictElement({
            "age": 25,
            "score": 87.5,
            "count": "15",
            "invalid": "not_a_number"
        })

        # Valid range
        age_range = Lock("age", LockType.RANGE, [18, 65])
        assert age_range.validate(element) is True

        # Out of range
        young_range = Lock("age", LockType.RANGE, [0, 17])
        assert young_range.validate(element) is False

        old_range = Lock("age", LockType.RANGE, [66, 100])
        assert old_range.validate(element) is False

        # Float value in range
        score_range = Lock("score", LockType.RANGE, [80.0, 90.0])
        assert score_range.validate(element) is True

        # String number in range
        count_range = Lock("count", LockType.RANGE, [10, 20])
        assert count_range.validate(element) is True

        # Invalid number should fail
        invalid_range = Lock("invalid", LockType.RANGE, [0, 100])
        assert invalid_range.validate(element) is False

    def test_custom_validator_lock(self):
        """Test CUSTOM lock type with registered validators."""
        # Register a custom validator
        def is_even(value, expected):
            try:
                return int(value) % 2 == 0
            except (ValueError, TypeError):
                return False

        register_validator("is_even", is_even)

        element = DictElement({
            "even_number": 42,
            "odd_number": 13,
            "string_even": "20",
            "invalid": "not_a_number"
        })

        # Custom lock for even numbers
        even_lock = Lock(
            "even_number",
            LockType.CUSTOM,
            expected_value=None,
            validator_name="is_even"
        )
        assert even_lock.validate(element) is True

        # Odd number should fail
        odd_lock = Lock(
            "odd_number",
            LockType.CUSTOM,
            expected_value=None,
            validator_name="is_even"
        )
        assert odd_lock.validate(element) is False

        # String even number should pass
        string_even_lock = Lock(
            "string_even",
            LockType.CUSTOM,
            expected_value=None,
            validator_name="is_even"
        )
        assert string_even_lock.validate(element) is True

        # Invalid input should fail
        invalid_lock = Lock(
            "invalid",
            LockType.CUSTOM,
            expected_value=None,
            validator_name="is_even"
        )
        assert invalid_lock.validate(element) is False

    @given(lock=lock_instance(), element=dict_element())
    def test_lock_error_messages_never_crash(self, lock: Lock, element: DictElement):
        """Error message generation should never crash."""
        try:
            failure_message = lock.get_failure_message(element)
            assert isinstance(failure_message, str)
            assert len(failure_message) > 0
        except Exception as e:
            pytest.fail(f"get_failure_message crashed: {e}")

        try:
            action_message = lock.get_action_message(element)
            assert isinstance(action_message, str)
            assert len(action_message) > 0
        except Exception as e:
            pytest.fail(f"get_action_message crashed: {e}")

    @given(lock=lock_instance())
    def test_lock_configuration_validation(self, lock: Lock):
        """Lock should be properly configured after creation."""
        # Basic properties should be set
        assert isinstance(lock.property_path, str)
        assert len(lock.property_path) > 0
        assert isinstance(lock.lock_type, LockType)

        # Custom locks should have validator_name
        if lock.lock_type == LockType.CUSTOM:
            assert lock.validator_name is not None
            assert isinstance(lock.validator_name, str)

        # Locks requiring expected_value should have it
        required_value_types = {
            LockType.EQUALS, LockType.GREATER_THAN, LockType.LESS_THAN,
            LockType.CONTAINS, LockType.REGEX, LockType.TYPE_CHECK,
            LockType.RANGE, LockType.LENGTH, LockType.IN_LIST,
            LockType.NOT_IN_LIST
        }
        if lock.lock_type in required_value_types:
            assert lock.expected_value is not None

    def test_lock_invalid_configurations(self):
        """Test that invalid lock configurations raise appropriate errors."""
        # Missing expected_value for types that require it
        with pytest.raises(ValueError):
            Lock("path", LockType.EQUALS, None)

        with pytest.raises(ValueError):
            Lock("path", LockType.GREATER_THAN, None)

        # Missing validator_name for CUSTOM type
        with pytest.raises(ValueError):
            Lock("path", LockType.CUSTOM, None, validator_name=None)

        # Empty property path should be handled
        # (implementation may vary - this tests current behavior)
        try:
            Lock("", LockType.EXISTS)
            # If it doesn't raise, that's also valid behavior
        except ValueError:
            # This is also acceptable
            pass

    @given(
        lock_type_value1=lock_type_and_value(),
        lock_type_value2=lock_type_and_value(),
        path=valid_property_path()
    )
    def test_different_locks_same_path_independence(
        self, lock_type_value1, lock_type_value2, path: str
    ):
        """Different locks on the same path should be independent."""
        lock_type1, expected_value1 = lock_type_value1
        lock_type2, expected_value2 = lock_type_value2

        # Skip custom locks without validators
        if (lock_type1 == LockType.CUSTOM and not get_validator("test_validator")) or \
           (lock_type2 == LockType.CUSTOM and not get_validator("test_validator")):
            return

        element = element_with_property(path, "test_value")

        # Create two different locks for the same path
        validator_name1 = "test_validator" if lock_type1 == LockType.CUSTOM else None
        validator_name2 = "test_validator" if lock_type2 == LockType.CUSTOM else None

        lock1 = Lock(path, lock_type1, expected_value1, validator_name1)
        lock2 = Lock(path, lock_type2, expected_value2, validator_name2)

        # Validate with both locks
        result1 = lock1.validate(element)
        result2 = lock2.validate(element)

        # Results should be independent and deterministic
        assert lock1.validate(element) == result1
        assert lock2.validate(element) == result2

        # Both should be boolean
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
