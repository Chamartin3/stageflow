"""Unit tests for Element classes."""

import pytest

from stageflow.core.element import DictElement, create_element


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
