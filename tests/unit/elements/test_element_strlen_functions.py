"""Unit tests for string length functions (strlen, minlen, maxlen) in Element."""

import pytest

from stageflow.elements import DictElement


class TestStrlenFunction:
    """Test strlen() function for sum of string lengths."""

    @pytest.fixture
    def element(self):
        """Create test element with various data types."""
        return DictElement(
            {
                "tags": ["hello", "world"],
                "short_tags": ["a", "bb", "ccc"],
                "numbers": [1, 22, 333],
                "mixed": ["hello", 123, True],
                "empty_list": [],
                "with_objects": ["hello", {"key": "val"}],
                "with_nested_lists": ["hello", ["nested"]],
                "single_item": ["test"],
                "nested": {"tags": ["foo", "bar", "baz"]},
            }
        )

    def test_strlen_basic_strings(self, element):
        """Test strlen with basic string arrays."""
        assert element.get_property("strlen(tags)") == 10  # "hello" + "world"
        assert element.get_property("strlen(short_tags)") == 6  # "a" + "bb" + "ccc"

    def test_strlen_with_numbers(self, element):
        """Test strlen with numeric values (should stringify)."""
        assert element.get_property("strlen(numbers)") == 6  # "1" + "22" + "333"

    def test_strlen_with_mixed_types(self, element):
        """Test strlen with mixed primitive types."""
        assert element.get_property("strlen(mixed)") == 12  # "hello" + "123" + "True"

    def test_strlen_empty_list(self, element):
        """Test strlen with empty array."""
        assert element.get_property("strlen(empty_list)") == 0

    def test_strlen_single_item(self, element):
        """Test strlen with single item."""
        assert element.get_property("strlen(single_item)") == 4  # "test"

    def test_strlen_nested_property(self, element):
        """Test strlen with nested property path."""
        assert element.get_property("strlen(nested.tags)") == 9  # "foo" + "bar" + "baz"

    def test_strlen_rejects_objects(self, element):
        """Test strlen rejects arrays containing objects."""
        assert element.get_property("strlen(with_objects)") is None

    def test_strlen_rejects_nested_lists(self, element):
        """Test strlen rejects arrays containing nested lists."""
        assert element.get_property("strlen(with_nested_lists)") is None

    def test_strlen_missing_property(self, element):
        """Test strlen with non-existent property."""
        assert element.get_property("strlen(missing)") is None

    def test_strlen_non_array_property(self, element):
        """Test strlen with non-array property."""
        element_with_string = DictElement({"name": "hello"})
        assert element_with_string.get_property("strlen(name)") is None

    def test_strlen_case_insensitive(self, element):
        """Test that STRLEN works case-insensitively."""
        assert element.get_property("STRLEN(tags)") == 10
        assert element.get_property("StrLen(tags)") == 10


class TestMinlenFunction:
    """Test minlen() function for minimum string length."""

    @pytest.fixture
    def element(self):
        """Create test element with various data types."""
        return DictElement(
            {
                "tags": ["hello", "world", "hi"],
                "short_tags": ["a", "bb", "ccc"],
                "numbers": [1, 22, 333],
                "mixed": ["hello", 1, True],
                "empty_list": [],
                "with_objects": ["hello", {"key": "val"}],
                "single_item": ["test"],
                "nested": {"tags": ["foo", "barbaz", "b"]},
            }
        )

    def test_minlen_basic_strings(self, element):
        """Test minlen with basic string arrays."""
        assert element.get_property("minlen(tags)") == 2  # "hi"
        assert element.get_property("minlen(short_tags)") == 1  # "a"

    def test_minlen_with_numbers(self, element):
        """Test minlen with numeric values (should stringify)."""
        assert element.get_property("minlen(numbers)") == 1  # "1"

    def test_minlen_with_mixed_types(self, element):
        """Test minlen with mixed primitive types."""
        assert element.get_property("minlen(mixed)") == 1  # "1"

    def test_minlen_empty_list(self, element):
        """Test minlen with empty array returns None."""
        assert element.get_property("minlen(empty_list)") is None

    def test_minlen_single_item(self, element):
        """Test minlen with single item."""
        assert element.get_property("minlen(single_item)") == 4  # "test"

    def test_minlen_nested_property(self, element):
        """Test minlen with nested property path."""
        assert element.get_property("minlen(nested.tags)") == 1  # "b"

    def test_minlen_rejects_objects(self, element):
        """Test minlen rejects arrays containing objects."""
        assert element.get_property("minlen(with_objects)") is None

    def test_minlen_missing_property(self, element):
        """Test minlen with non-existent property."""
        assert element.get_property("minlen(missing)") is None

    def test_minlen_case_insensitive(self, element):
        """Test that MINLEN works case-insensitively."""
        assert element.get_property("MINLEN(tags)") == 2
        assert element.get_property("MinLen(tags)") == 2


class TestMaxlenFunction:
    """Test maxlen() function for maximum string length."""

    @pytest.fixture
    def element(self):
        """Create test element with various data types."""
        return DictElement(
            {
                "tags": ["hello", "world", "hi"],
                "short_tags": ["a", "bb", "ccc"],
                "numbers": [1, 22, 333],
                "mixed": ["hello", 1, True],
                "empty_list": [],
                "with_objects": ["hello", {"key": "val"}],
                "single_item": ["test"],
                "nested": {"tags": ["foo", "barbaz", "b"]},
            }
        )

    def test_maxlen_basic_strings(self, element):
        """Test maxlen with basic string arrays."""
        assert element.get_property("maxlen(tags)") == 5  # "hello" or "world"
        assert element.get_property("maxlen(short_tags)") == 3  # "ccc"

    def test_maxlen_with_numbers(self, element):
        """Test maxlen with numeric values (should stringify)."""
        assert element.get_property("maxlen(numbers)") == 3  # "333"

    def test_maxlen_with_mixed_types(self, element):
        """Test maxlen with mixed primitive types."""
        assert element.get_property("maxlen(mixed)") == 5  # "hello"

    def test_maxlen_empty_list(self, element):
        """Test maxlen with empty array returns None."""
        assert element.get_property("maxlen(empty_list)") is None

    def test_maxlen_single_item(self, element):
        """Test maxlen with single item."""
        assert element.get_property("maxlen(single_item)") == 4  # "test"

    def test_maxlen_nested_property(self, element):
        """Test maxlen with nested property path."""
        assert element.get_property("maxlen(nested.tags)") == 6  # "barbaz"

    def test_maxlen_rejects_objects(self, element):
        """Test maxlen rejects arrays containing objects."""
        assert element.get_property("maxlen(with_objects)") is None

    def test_maxlen_missing_property(self, element):
        """Test maxlen with non-existent property."""
        assert element.get_property("maxlen(missing)") is None

    def test_maxlen_case_insensitive(self, element):
        """Test that MAXLEN works case-insensitively."""
        assert element.get_property("MAXLEN(tags)") == 5
        assert element.get_property("MaxLen(tags)") == 5


class TestStrlenWithLocks:
    """Test string length functions used with validation locks."""

    def test_strlen_with_greater_than_lock(self):
        """Test strlen used with GREATER_THAN lock."""
        from stageflow.lock import SimpleLock

        element = DictElement({"tags": ["hello", "world"]})

        # Total length is 10, should pass > 5
        lock = SimpleLock(
            {
                "type": "greater_than",
                "property_path": "strlen(tags)",
                "expected_value": 5,
            }
        )
        result = lock.validate(element)
        assert result.success is True

        # Should fail > 15
        lock_fail = SimpleLock(
            {
                "type": "greater_than",
                "property_path": "strlen(tags)",
                "expected_value": 15,
            }
        )
        result_fail = lock_fail.validate(element)
        assert result_fail.success is False

    def test_minlen_with_greater_than_lock(self):
        """Test minlen used with GREATER_THAN lock."""
        from stageflow.lock import SimpleLock

        element = DictElement({"tags": ["hello", "world", "hi"]})

        # Minimum length is 2 ("hi"), should pass >= 2
        lock = SimpleLock(
            {
                "type": "greater_than",
                "property_path": "minlen(tags)",
                "expected_value": 1,
            }
        )
        result = lock.validate(element)
        assert result.success is True

        # Should fail > 2
        lock_fail = SimpleLock(
            {
                "type": "greater_than",
                "property_path": "minlen(tags)",
                "expected_value": 2,
            }
        )
        result_fail = lock_fail.validate(element)
        assert result_fail.success is False

    def test_maxlen_with_less_than_lock(self):
        """Test maxlen used with LESS_THAN lock."""
        from stageflow.lock import SimpleLock

        element = DictElement({"tags": ["hello", "world", "hi"]})

        # Maximum length is 5, should pass < 10
        lock = SimpleLock(
            {
                "type": "less_than",
                "property_path": "maxlen(tags)",
                "expected_value": 10,
            }
        )
        result = lock.validate(element)
        assert result.success is True

        # Should fail < 3
        lock_fail = SimpleLock(
            {
                "type": "less_than",
                "property_path": "maxlen(tags)",
                "expected_value": 3,
            }
        )
        result_fail = lock_fail.validate(element)
        assert result_fail.success is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_function_argument(self):
        """Test functions with empty argument."""
        element = DictElement({"tags": ["hello"]})
        assert element.get_property("strlen()") is None
        assert element.get_property("minlen()") is None
        assert element.get_property("maxlen()") is None

    def test_whitespace_only_strings(self):
        """Test with whitespace-only strings."""
        element = DictElement({"tags": ["  ", "   ", "    "]})
        assert element.get_property("strlen(tags)") == 9  # 2 + 3 + 4 spaces
        assert element.get_property("minlen(tags)") == 2
        assert element.get_property("maxlen(tags)") == 4

    def test_empty_strings_in_array(self):
        """Test with empty strings in array."""
        element = DictElement({"tags": ["hello", "", "world"]})
        assert element.get_property("strlen(tags)") == 10  # 5 + 0 + 5
        assert element.get_property("minlen(tags)") == 0
        assert element.get_property("maxlen(tags)") == 5

    def test_boolean_values(self):
        """Test with boolean values."""
        element = DictElement({"flags": [True, False, True]})
        assert element.get_property("strlen(flags)") == 13  # "True"(4) + "False"(5) + "True"(4)
        assert element.get_property("minlen(flags)") == 4  # "True"
        assert element.get_property("maxlen(flags)") == 5  # "False"

    def test_float_values(self):
        """Test with float values."""
        element = DictElement({"values": [1.5, 2.75, 3.0]})
        # "1.5" (3) + "2.75" (4) + "3.0" (3) = 10
        assert element.get_property("strlen(values)") == 10
        assert element.get_property("minlen(values)") == 3
        assert element.get_property("maxlen(values)") == 4
