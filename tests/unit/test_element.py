"""Unit tests for Element classes."""

import pytest

from stageflow.element import DictElement, create_element


class TestDictElement:
    """Test DictElement implementation."""

    def test_get_property_simple(self, sample_element):
        """Test getting simple properties."""
        assert sample_element.get_property("user_id") == "user123"
        assert sample_element.get_property("email") == "test@example.com"

    def test_get_property_nested(self, sample_element):
        """Test getting nested properties."""
        assert sample_element.get_property("profile.first_name") == "John"
        assert sample_element.get_property("profile.last_name") == "Doe"
        assert sample_element.get_property("verification.email_verified") is True

    def test_get_property_missing(self, sample_element):
        """Test getting missing properties raises KeyError."""
        with pytest.raises(KeyError):
            sample_element.get_property("nonexistent")

        with pytest.raises(KeyError):
            sample_element.get_property("profile.nonexistent")

    def test_has_property_exists(self, sample_element):
        """Test has_property for existing properties."""
        assert sample_element.has_property("user_id") is True
        assert sample_element.has_property("profile.first_name") is True
        assert sample_element.has_property("verification.email_verified") is True

    def test_has_property_missing(self, sample_element):
        """Test has_property for missing properties."""
        assert sample_element.has_property("nonexistent") is False
        assert sample_element.has_property("profile.nonexistent") is False

    def test_to_dict(self, sample_element, sample_element_data):
        """Test to_dict returns copy of data."""
        result = sample_element.to_dict()
        assert result == sample_element_data

        # Verify it's a copy, not the same object
        result["user_id"] = "modified"
        assert sample_element.get_property("user_id") == "user123"

    def test_bracket_notation(self, complex_element):
        """Test bracket notation for array access."""
        assert complex_element.get_property("items[0].name") == "Widget A"
        assert complex_element.get_property("items[1].price") == 39.99

    def test_bracket_notation_missing_index(self, complex_element):
        """Test bracket notation with missing index."""
        with pytest.raises((KeyError, IndexError)):
            complex_element.get_property("items[5].name")

    def test_dot_notation_access(self, sample_element):
        """Test dot notation property access via __getattr__."""
        assert sample_element.user_id == "user123"
        assert sample_element.email == "test@example.com"

    def test_dot_notation_nested_access(self, sample_element):
        """Test dot notation access to nested properties."""
        profile = sample_element.profile
        assert isinstance(profile, DictElement)
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"

    def test_dot_notation_missing_property(self, sample_element):
        """Test dot notation access to missing property raises AttributeError."""
        with pytest.raises(AttributeError):
            sample_element.nonexistent

    def test_bracket_notation_access(self, sample_element):
        """Test bracket notation property access via __getitem__."""
        assert sample_element["user_id"] == "user123"
        assert sample_element["email"] == "test@example.com"

    def test_bracket_notation_nested_access(self, sample_element):
        """Test bracket notation access to nested properties."""
        profile = sample_element["profile"]
        assert isinstance(profile, DictElement)
        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Doe"

    def test_bracket_notation_missing_property(self, sample_element):
        """Test bracket notation access to missing property raises KeyError."""
        with pytest.raises(KeyError):
            sample_element["nonexistent"]

    def test_element_iteration(self, sample_element):
        """Test iteration over element keys."""
        keys = list(sample_element)
        expected_keys = ["user_id", "email", "profile", "preferences", "verification", "metadata"]
        assert set(keys) == set(expected_keys)

    def test_element_contains(self, sample_element):
        """Test 'in' operator for checking property existence."""
        assert "user_id" in sample_element
        assert "profile" in sample_element
        assert "nonexistent" not in sample_element

    def test_element_keys(self, sample_element):
        """Test keys() method."""
        keys = list(sample_element.keys())
        expected_keys = ["user_id", "email", "profile", "preferences", "verification", "metadata"]
        assert set(keys) == set(expected_keys)

    def test_element_values(self, sample_element):
        """Test values() method."""
        values = list(sample_element.values())
        assert len(values) == 6
        # Check that nested dictionaries are returned as DictElement instances
        profile_value = None
        for value in values:
            if isinstance(value, DictElement):
                profile_value = value
                break
        assert profile_value is not None
        assert profile_value.first_name == "John"

    def test_element_items(self, sample_element):
        """Test items() method."""
        items = dict(sample_element.items())
        assert "user_id" in items
        assert items["user_id"] == "user123"
        # Check that nested dictionaries are returned as DictElement instances
        assert isinstance(items["profile"], DictElement)
        assert items["profile"].first_name == "John"

    def test_immutability_through_dot_notation(self, sample_element_data):
        """Test that dot notation access preserves immutability."""
        element = DictElement(sample_element_data)
        profile = element.profile
        # Modifying the original data shouldn't affect the element
        sample_element_data["profile"]["first_name"] = "Modified"
        assert profile.first_name == "John"  # Should still be original value

    def test_immutability_through_bracket_notation(self, sample_element_data):
        """Test that bracket notation access preserves immutability."""
        element = DictElement(sample_element_data)
        profile = element["profile"]
        # Modifying the original data shouldn't affect the element
        sample_element_data["profile"]["first_name"] = "Modified"
        assert profile["first_name"] == "John"  # Should still be original value

    def test_mixed_notation_complex_paths(self, complex_element):
        """Test mixed dot and bracket notation for complex paths."""
        # Test mixed notation: dot.notation[index]['key'].property
        assert complex_element.get_property("items[0].name") == "Widget A"
        assert complex_element.get_property("items[1]['price']") == 39.99
        assert complex_element.get_property("customer['address'].city") == "Anytown"
        assert complex_element.get_property("customer.address['zip']") == "12345"

    def test_quoted_keys_with_spaces(self):
        """Test bracket notation with quoted keys containing spaces."""
        data = {
            "user data": {"full name": "John Doe"},
            "api response": {"status code": 200}
        }
        element = DictElement(data)

        assert element.get_property("['user data']['full name']") == "John Doe"
        assert element.get_property("['api response']['status code']") == 200

    def test_quoted_keys_with_special_characters(self):
        """Test bracket notation with quoted keys containing special characters."""
        data = {
            "key.with.dots": {"nested": "value1"},
            "key'with'quotes": {"nested": "value2"},
            "key\"with\"double\"quotes": {"nested": "value3"}
        }
        element = DictElement(data)

        assert element.get_property("['key.with.dots']['nested']") == "value1"
        assert element.get_property("[\"key'with'quotes\"]['nested']") == "value2"
        assert element.get_property("['key\"with\"double\"quotes']['nested']") == "value3"

    def test_escaped_quotes_in_keys(self):
        """Test bracket notation with escaped quotes in keys."""
        data = {
            "key'with'escaped": {"value": "test"},
            "key\"with\"escaped": {"value": "test2"}
        }
        element = DictElement(data)

        assert element.get_property("['key\\'with\\'escaped']['value']") == "test"
        assert element.get_property("[\"key\\\"with\\\"escaped\"]['value']") == "test2"

    def test_nested_array_access(self):
        """Test nested array access with multiple indices."""
        data = {
            "matrix": [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ],
            "complex": [
                {"items": [{"id": 1}, {"id": 2}]},
                {"items": [{"id": 3}, {"id": 4}]}
            ]
        }
        element = DictElement(data)

        assert element.get_property("matrix[0][1]") == 2
        assert element.get_property("matrix[2][0]") == 7
        assert element.get_property("complex[0]['items'][1]['id']") == 2
        assert element.get_property("complex[1].items[0].id") == 3

    def test_complex_mixed_notation_scenarios(self):
        """Test complex scenarios mixing all notation types."""
        data = {
            "settings": {
                "themes": [
                    {
                        "name": "dark",
                        "colors": {
                            "primary": "#000000",
                            "secondary": "#333333"
                        },
                        "font sizes": [12, 14, 16, 18]
                    },
                    {
                        "name": "light",
                        "colors": {
                            "primary": "#ffffff",
                            "secondary": "#cccccc"
                        },
                        "font sizes": [10, 12, 14, 16]
                    }
                ]
            }
        }
        element = DictElement(data)

        # Test complex mixed paths
        assert element.get_property("settings.themes[0]['colors'].primary") == "#000000"
        assert element.get_property("settings['themes'][1].colors['secondary']") == "#cccccc"
        assert element.get_property("settings.themes[0]['font sizes'][2]") == 16
        assert element.get_property("settings['themes'][1]['font sizes'][0]") == 10

    def test_error_handling_with_context(self, sample_element):
        """Test enhanced error handling with path context."""
        # Test KeyError with context
        with pytest.raises(KeyError, match=r"Property 'nonexistent' not found at path 'nonexistent'"):
            sample_element.get_property("nonexistent")

        with pytest.raises(KeyError, match=r"Property 'missing' not found at path 'profile\.missing'"):
            sample_element.get_property("profile.missing")

    def test_error_handling_index_out_of_bounds(self, complex_element):
        """Test IndexError handling with context."""
        with pytest.raises(IndexError, match=r"Index 10 out of bounds at path 'items\[10\]'"):
            complex_element.get_property("items[10]")

    def test_error_handling_type_mismatch(self, sample_element):
        """Test TypeError handling when accessing wrong data types."""
        with pytest.raises(TypeError, match=r"Cannot access 'nonexistent' on str at path 'email\.nonexistent'"):
            sample_element.get_property("email.nonexistent")

    def test_error_handling_invalid_syntax(self):
        """Test ValueError for invalid path syntax."""
        data = {"test": "value"}
        element = DictElement(data)

        # Test unclosed bracket
        with pytest.raises(ValueError, match=r"Unclosed bracket"):
            element.get_property("test[unclosed")

        # Test various syntax errors that should raise ValueError
        with pytest.raises(ValueError):
            element.get_property("test['unclosed")  # Unclosed quote or bracket

        with pytest.raises(ValueError):
            element.get_property("test[\"unclosed")  # Unclosed double quote or bracket

    def test_whitespace_handling_in_brackets(self):
        """Test whitespace handling in bracket notation."""
        data = {"test": [1, 2, 3], "key": "value"}
        element = DictElement(data)

        # Whitespace should be ignored outside quotes
        assert element.get_property("test[ 0 ]") == 1
        assert element.get_property("[ 'key' ]") == "value"

    def test_empty_path_edge_cases(self, sample_element):
        """Test edge cases with empty paths."""
        # Empty path should return the data itself
        assert sample_element.get_property("") == sample_element.to_dict()

    def test_has_property_enhanced_patterns(self, complex_element):
        """Test has_property with enhanced path patterns."""
        # Test existing complex paths
        assert complex_element.has_property("items[0].name") is True
        assert complex_element.has_property("customer['address'].city") is True
        assert complex_element.has_property("customer.address['zip']") is True

        # Test non-existing complex paths
        assert complex_element.has_property("items[10].name") is False
        assert complex_element.has_property("customer.address.country") is False
        assert complex_element.has_property("nonexistent[0]['key']") is False

    def test_path_reconstruction_for_errors(self):
        """Test path reconstruction in error messages maintains readability."""
        data = {
            "normal": "value",
            "key with spaces": {"nested": "value"},
            "key.with.dots": [1, 2, 3]
        }
        element = DictElement(data)

        # Test that complex keys are properly reconstructed in error messages
        with pytest.raises(KeyError) as exc_info:
            element.get_property("['key with spaces'].missing")
        # The path reconstruction shows the key name and property
        assert "key with spaces" in str(exc_info.value)
        assert "missing" in str(exc_info.value)

        with pytest.raises(IndexError) as exc_info:
            element.get_property("['key.with.dots'][5]")
        # The path reconstruction shows the array access
        assert "key.with.dots" in str(exc_info.value)
        assert "5" in str(exc_info.value)


class TestCreateElement:
    """Test create_element factory function."""

    def test_create_from_dict(self, sample_element_data):
        """Test creating element from dictionary."""
        element = create_element(sample_element_data)
        assert isinstance(element, DictElement)
        assert element.get_property("user_id") == "user123"

    def test_create_from_element(self, sample_element):
        """Test creating element from existing element."""
        element = create_element(sample_element)
        assert element is sample_element

    def test_create_from_invalid_type(self):
        """Test creating element from invalid type raises TypeError."""
        with pytest.raises(TypeError):
            create_element("invalid")

        with pytest.raises(TypeError):
            create_element(123)
