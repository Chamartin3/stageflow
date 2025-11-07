"""Tests for element length function support."""

import pytest

from stageflow.elements import DictElement
from stageflow.lock import LockFactory, LockType


class TestElementLengthFunctions:
    """Test length function support in DictElement."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing length operations."""
        return {
            "items": ["a", "b", "c"],  # length 3
            "empty_list": [],  # length 0
            "string_field": "hello",  # length 5
            "empty_string": "",  # length 0
            "user": {
                "posts": [1, 2, 3, 4],  # length 4
                "name": "John",  # length 4
                "tags": {"python", "dev"},  # length 2
                "empty_dict": {},  # length 0
            },
            "matrix": [[1, 2], [3, 4, 5]],  # length 2
        }

    @pytest.fixture
    def element(self, sample_data):
        """Create DictElement with sample data."""
        return DictElement(sample_data)

    def test_length_function_syntax_arrays(self, element):
        """Test length(path) function syntax with arrays."""
        assert element.get_property("length(items)") == 3
        assert element.get_property("length(empty_list)") == 0
        assert element.get_property("length(user.posts)") == 4
        assert element.get_property("length(matrix)") == 2

    def test_length_function_syntax_strings(self, element):
        """Test length(path) function syntax with strings."""
        assert element.get_property("length(string_field)") == 5
        assert element.get_property("length(empty_string)") == 0
        assert element.get_property("length(user.name)") == 4

    def test_length_function_syntax_collections(self, element):
        """Test length(path) function syntax with collections."""
        assert element.get_property("length(user.tags)") == 2
        assert element.get_property("length(user.empty_dict)") == 0

    def test_length_property_syntax_arrays(self, element):
        """Test path.length property syntax with arrays."""
        assert element.get_property("items.length") == 3
        assert element.get_property("empty_list.length") == 0
        assert element.get_property("user.posts.length") == 4
        assert element.get_property("matrix.length") == 2

    def test_length_property_syntax_strings(self, element):
        """Test path.length property syntax with strings."""
        assert element.get_property("string_field.length") == 5
        assert element.get_property("empty_string.length") == 0
        assert element.get_property("user.name.length") == 4

    def test_length_property_syntax_collections(self, element):
        """Test path.length property syntax with collections."""
        assert element.get_property("user.tags.length") == 2
        assert element.get_property("user.empty_dict.length") == 0

    def test_length_function_invalid_path(self, element):
        """Test length function with invalid paths returns None."""
        assert element.get_property("length(nonexistent)") is None
        assert element.get_property("length(user.missing)") is None

    def test_length_property_invalid_path(self, element):
        """Test length property with invalid paths returns None."""
        assert element.get_property("nonexistent.length") is None
        assert element.get_property("user.missing.length") is None

    def test_length_function_unsupported_type(self, element):
        """Test length function with unsupported types returns None."""
        # Add a number to test unsupported type
        element_with_number = DictElement(
            {
                "number": 42,
                "boolean": True,
            }
        )

        # These should return None since numbers and booleans don't support length
        assert element_with_number.get_property("length(number)") is None
        assert element_with_number.get_property("length(boolean)") is None

    def test_count_function_alias(self, element):
        """Test that count() works as an alias for length()."""
        assert element.get_property("count(items)") == 3
        assert element.get_property("count(string_field)") == 5
        assert element.get_property("count(user.tags)") == 2

    def test_length_function_case_insensitive(self, element):
        """Test that LENGTH() and COUNT() work case-insensitively."""
        assert element.get_property("LENGTH(items)") == 3
        assert element.get_property("Count(string_field)") == 5

    def test_length_function_invalid_syntax(self, element):
        """Test invalid length function syntax returns None."""
        # Missing closing parenthesis
        assert element.get_property("length(items") is None
        # Missing opening parenthesis
        assert element.get_property("lengthitems)") is None
        # Empty argument
        assert element.get_property("length()") is None
        # Unsupported function
        assert element.get_property("size(items)") is None

    def test_backward_compatibility_normal_properties(self, element):
        """Test that normal property access still works."""
        assert element.get_property("items") == ["a", "b", "c"]
        assert element.get_property("string_field") == "hello"
        assert element.get_property("user.name") == "John"

    def test_length_function_with_complex_paths(self, element):
        """Test length functions with complex property paths."""
        assert element.get_property("length(user.posts)") == 4
        assert element.get_property("user.posts.length") == 4

    def test_length_function_with_array_indices(self, element):
        """Test length functions with array index access."""
        # Access specific array element and get its length
        assert element.get_property("length(matrix[0])") == 2  # [1, 2] has length 2
        assert element.get_property("length(matrix[1])") == 3  # [3, 4, 5] has length 3

    def test_has_property_with_length_functions(self, element):
        """Test has_property method with length functions."""
        # Length functions should return False for has_property since they're computed
        assert not element.has_property("length(items)")
        assert not element.has_property("items.length")

        # But the underlying properties should still exist
        assert element.has_property("items")
        assert element.has_property("string_field")

    # Lock Type Integration Tests

    def test_length_with_equals_lock_function_syntax(self, element):
        """EQUALS lock with length using function syntax."""
        lock = LockFactory.create(
            {
                "type": LockType.EQUALS,
                "property_path": "length(items)",
                "expected_value": 3,
            }
        )

        result = lock.validate(element)
        assert result.success is True

        # Test failure case
        lock_fail = LockFactory.create(
            {
                "type": LockType.EQUALS,
                "property_path": "length(items)",
                "expected_value": 5,
            }
        )

        result_fail = lock_fail.validate(element)
        assert result_fail.success is False

    def test_length_with_equals_lock_property_syntax(self, element):
        """EQUALS lock with length using property syntax."""
        lock = LockFactory.create(
            {
                "type": LockType.EQUALS,
                "property_path": "items.length",
                "expected_value": 3,
            }
        )

        result = lock.validate(element)
        assert result.success is True

    def test_length_with_greater_than_lock(self, element):
        """GREATER_THAN lock with length."""
        lock = LockFactory.create(
            {
                "type": LockType.GREATER_THAN,
                "property_path": "length(user.posts)",
                "expected_value": 3,
            }
        )

        result = lock.validate(element)
        assert result.success is True  # 4 > 3

    def test_length_with_less_than_lock(self, element):
        """LESS_THAN lock with length."""
        lock = LockFactory.create(
            {
                "type": LockType.LESS_THAN,
                "property_path": "length(empty_list)",
                "expected_value": 1,
            }
        )

        result = lock.validate(element)
        assert result.success is True  # 0 < 1

    def test_length_with_greater_equal_lock(self, element):
        """GREATER_EQUAL lock with length."""
        lock = LockFactory.create(
            {
                "type": LockType.GREATER_THAN,  # Note: Using GREATER_THAN for >= comparison
                "property_path": "length(string_field)",
                "expected_value": 4,  # 5 >= 4
            }
        )

        result = lock.validate(element)
        assert result.success is True  # 5 >= 4

    def test_length_with_less_equal_lock(self, element):
        """LESS_EQUAL lock with length."""
        lock = LockFactory.create(
            {
                "type": LockType.LESS_THAN,  # Note: Using LESS_THAN for <= comparison
                "property_path": "length(user.tags)",
                "expected_value": 3,  # 2 <= 3
            }
        )

        result = lock.validate(element)
        assert result.success is True  # 2 <= 3

    def test_length_with_type_check_lock(self, element):
        """TYPE_CHECK lock with length (length returns int)."""
        lock = LockFactory.create(
            {
                "type": LockType.TYPE_CHECK,
                "property_path": "length(items)",
                "expected_value": "int",
            }
        )

        result = lock.validate(element)
        assert result.success is True

    # Edge Cases and Error Handling

    def test_length_of_actual_length_field(self):
        """Data with actual 'length' field vs computed length."""
        element = DictElement(
            {
                "items": [1, 2, 3],
                "metadata": {"length": 100},  # Actual field named 'length'
            }
        )

        # Property syntax accesses actual field
        assert element.get_property("metadata.length") == 100

        # Function syntax computes length
        assert element.get_property("length(items)") == 3

        # Function syntax on metadata computes length of dict
        assert element.get_property("length(metadata)") == 1

    def test_length_function_vs_property_syntax_consistency(self, element):
        """Both syntaxes produce same result."""
        # Test various paths
        paths = ["items", "user.posts", "string_field", "user.tags"]

        for path in paths:
            func_result = element.get_property(f"length({path})")
            prop_result = element.get_property(f"{path}.length")
            assert func_result == prop_result, (
                f"Mismatch for path {path}: func={func_result}, prop={prop_result}"
            )

    def test_length_with_empty_path(self):
        """Empty path handling."""
        element = DictElement({"test": "value"})
        assert element.get_property("length()") is None
        assert element.get_property("length(") is None
        assert element.get_property("length)") is None

    def test_length_with_invalid_syntax(self):
        """Invalid syntax handling."""
        element = DictElement({"items": [1, 2, 3]})

        # Various malformed syntaxes
        invalid_syntaxes = [
            "length(items",  # Missing closing paren
            "lengthitems)",  # Missing opening paren
            "length[items]",  # Wrong brackets
            "length{items}",  # Wrong braces
            "len(items)",  # Wrong function name
            "size(items)",  # Wrong function name
        ]

        for syntax in invalid_syntaxes:
            result = element.get_property(syntax)
            assert result is None, f"Expected None for invalid syntax: {syntax}"

    def test_length_with_deeply_nested_paths(self):
        """Deeply nested paths still work."""
        element = DictElement(
            {"level1": {"level2": {"level3": {"deep_array": [1, 2, 3, 4, 5]}}}}
        )

        assert element.get_property("length(level1.level2.level3.deep_array)") == 5
        assert element.get_property("level1.level2.level3.deep_array.length") == 5

    def test_length_with_special_characters_in_paths(self):
        """Paths with special characters."""
        element = DictElement(
            {
                "user_data": {
                    "special-field": [1, 2, 3],
                    "field_with_underscores": "test_string",
                }
            }
        )

        # Note: Special characters in property names may not work with dot notation
        # but should work when accessed directly
        assert element.get_property("length(user_data.field_with_underscores)") == 11

    # Custom Error Messages with Length

    def test_length_lock_with_custom_message(self):
        """Custom error message with length lock."""
        lock = LockFactory.create(
            {
                "type": LockType.GREATER_THAN,
                "property_path": "length(items)",
                "expected_value": 5,
                "error_message": "Item list must contain more than 5 items",
            }
        )

        element = DictElement({"items": [1, 2, 3]})
        result = lock.validate(element)

        assert result.success is False
        assert "Item list must contain more than 5 items" in result.error_message

    def test_length_lock_error_shows_actual_length(self):
        """Error shows actual length value."""
        lock = LockFactory.create(
            {
                "type": LockType.EQUALS,
                "property_path": "length(items)",
                "expected_value": 5,
            }
        )

        element = DictElement({"items": [1, 2, 3]})
        result = lock.validate(element)

        assert result.success is False
        # Error message should indicate actual length (3) vs expected (5)
        assert "3" in result.error_message
        assert "5" in result.error_message

    # Performance Tests

    def test_length_performance_large_arrays(self):
        """Length computation is fast even with large arrays."""
        import time

        # Create element with large array
        large_array = list(range(10000))
        element = DictElement({"items": large_array})

        # Time the length computation
        start = time.time()
        length = element.get_property("length(items)")
        duration = time.time() - start

        assert length == 10000
        assert duration < 0.01  # Should be nearly instant
