"""Property-based tests for Element property resolution.

This module tests the fundamental invariants and behaviors of Element property
resolution, ensuring consistency, determinism, and correctness across a wide
range of data structures and property paths.

Key properties tested:
- Property resolution consistency and determinism
- Roundtrip properties for element conversion
- Property existence checks match actual resolution
- Error handling for invalid paths and missing properties
"""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from stageflow.element import DictElement, create_element
from tests.property.generators import (
    dict_element,
    element_with_property,
    element_without_property,
    nested_dict_data,
    valid_property_path,
)

pytestmark = pytest.mark.property


class TestElementPropertyResolution:
    """Property-based tests for Element property resolution behaviors."""

    @given(element=dict_element(), path=valid_property_path())
    def test_property_resolution_deterministic(self, element: DictElement, path: str):
        """Property resolution should be deterministic - same result every time."""
        # Property resolution should always return the same result
        try:
            result1 = element.get_property(path)
            result2 = element.get_property(path)
            assert result1 == result2
        except (KeyError, IndexError, TypeError):
            # If it fails once, it should fail consistently
            with pytest.raises((KeyError, IndexError, TypeError)):
                element.get_property(path)

    @given(element=dict_element(), path=valid_property_path())
    def test_has_property_consistency(self, element: DictElement, path: str):
        """has_property should be consistent with actual property resolution."""
        has_prop = element.has_property(path)

        if has_prop:
            # If has_property returns True, get_property should not raise an exception
            try:
                element.get_property(path)
                # The property should exist and not be None for most lock types
                # (though None values are technically valid)
            except (KeyError, IndexError, TypeError):
                pytest.fail(f"has_property returned True but get_property failed for path: {path}")
        else:
            # If has_property returns False, get_property should raise an exception
            with pytest.raises((KeyError, IndexError, TypeError)):
                element.get_property(path)

    @given(data=nested_dict_data())
    def test_element_immutability(self, data: dict):
        """Element creation should not modify the original data."""
        original_data = data.copy()
        element = DictElement(data)

        # Original data should not be modified
        assert data == original_data

        # Element should have its own copy
        element_data = element.to_dict()
        assert element_data == original_data

        # Modifying returned dict should not affect element
        if element_data:
            key = next(iter(element_data.keys()))
            original_value = element_data[key]
            element_data[key] = "modified"

            # Element should still return original value
            fresh_data = element.to_dict()
            assert fresh_data[key] == original_value

    @given(data=nested_dict_data())
    def test_to_dict_roundtrip(self, data: dict):
        """Converting to dict and back should preserve data."""
        element = DictElement(data)
        recovered_data = element.to_dict()
        recovered_element = DictElement(recovered_data)

        assert recovered_element.to_dict() == data

    @given(element=dict_element())
    def test_create_element_factory(self, element: DictElement):
        """create_element factory should handle various input types correctly."""
        # Test with Element input
        result1 = create_element(element)
        assert isinstance(result1, DictElement)
        assert result1.to_dict() == element.to_dict()

        # Test with dict input
        data = element.to_dict()
        result2 = create_element(data)
        assert isinstance(result2, DictElement)
        assert result2.to_dict() == data

    def test_create_element_invalid_type(self):
        """create_element should raise TypeError for invalid input types."""
        with pytest.raises(TypeError):
            create_element("invalid")

        with pytest.raises(TypeError):
            create_element(123)

        with pytest.raises(TypeError):
            create_element([1, 2, 3])

    @given(path=valid_property_path(), value=st.one_of(st.text(), st.integers(), st.booleans()))
    def test_property_access_with_guaranteed_property(self, path: str, value):
        """Test property access when property is guaranteed to exist."""
        element = element_with_property(path, value)

        # Property should exist
        assert element.has_property(path)

        # Should be able to retrieve the value
        retrieved_value = element.get_property(path)
        assert retrieved_value == value

    @given(path=valid_property_path())
    def test_property_access_with_missing_property(self, path: str):
        """Test property access when property is guaranteed to be missing."""
        # Skip very simple paths that are likely to exist in random data
        assume("." in path or "[" in path)

        element = element_without_property(path)

        # Property should not exist
        assert not element.has_property(path)

        # Should raise appropriate exception
        with pytest.raises((KeyError, IndexError, TypeError)):
            element.get_property(path)

    @given(element=dict_element())
    def test_element_iteration_and_access(self, element: DictElement):
        """Test that element iteration and access methods work correctly."""
        data = element.to_dict()

        # Test key iteration
        element_keys = set(element.keys())
        data_keys = set(data.keys())
        assert element_keys == data_keys

        # Test containment checks
        for key in data.keys():
            assert key in element

        # Test items and values iteration
        element_items = dict(element.items())
        for key, value in data.items():
            assert key in element_items
            if isinstance(value, dict):
                # Nested dicts become DictElements
                assert isinstance(element_items[key], DictElement)
                assert element_items[key].to_dict() == value
            else:
                assert element_items[key] == value

    @given(element=dict_element())
    def test_dot_notation_access(self, element: DictElement):
        """Test dot notation property access via __getattr__."""
        data = element.to_dict()

        for key in data.keys():
            if isinstance(key, str) and key.isidentifier():
                # Should be able to access via dot notation
                attr_value = getattr(element, key)
                direct_value = element.get_property(key)

                if isinstance(direct_value, dict):
                    assert isinstance(attr_value, DictElement)
                    assert attr_value.to_dict() == direct_value
                else:
                    assert attr_value == direct_value

    @given(element=dict_element())
    def test_bracket_notation_access(self, element: DictElement):
        """Test bracket notation property access via __getitem__."""
        data = element.to_dict()

        for key in data.keys():
            # Should be able to access via bracket notation
            bracket_value = element[key]
            direct_value = element.get_property(key)

            if isinstance(direct_value, dict):
                assert isinstance(bracket_value, DictElement)
                assert bracket_value.to_dict() == direct_value
            else:
                assert bracket_value == direct_value

    @given(element=dict_element())
    def test_element_attribute_errors(self, element: DictElement):
        """Test that accessing non-existent attributes raises AttributeError."""
        # Use a property name very unlikely to exist
        nonexistent_prop = "__very_unlikely_to_exist_property_name__"

        with pytest.raises(AttributeError):
            getattr(element, nonexistent_prop)

    @given(element=dict_element())
    def test_element_key_errors(self, element: DictElement):
        """Test that accessing non-existent keys raises appropriate errors."""
        # Use a property name very unlikely to exist
        nonexistent_key = "__very_unlikely_to_exist_key_name__"

        if not element.has_property(nonexistent_key):
            with pytest.raises((KeyError, AttributeError, TypeError)):
                element[nonexistent_key]

    # Specific test cases for edge conditions
    @given(element=dict_element(), path=st.text())
    def test_empty_and_invalid_paths(self, element: DictElement, path: str):
        """Test behavior with empty and potentially invalid property paths."""
        if not path:
            # Empty path should return the element data itself
            result = element.get_property(path)
            assert result == element.to_dict()
        # Other invalid paths should be handled gracefully
        # (either succeed or fail consistently)

    @given(
        element=dict_element(),
        path1=valid_property_path(),
        path2=valid_property_path()
    )
    def test_independent_property_access(self, element: DictElement, path1: str, path2: str):
        """Accessing one property should not affect accessing another."""
        assume(path1 != path2)

        # Access path1
        try:
            value1_first = element.get_property(path1)
            has_path1 = True
        except (KeyError, IndexError, TypeError):
            has_path1 = False

        # Access path2
        try:
            element.get_property(path2)
            has_path2 = True
        except (KeyError, IndexError, TypeError):
            has_path2 = False

        # Access path1 again - should be the same
        if has_path1:
            value1_second = element.get_property(path1)
            assert value1_first == value1_second

        # has_property calls should also be consistent
        assert element.has_property(path1) == has_path1
        assert element.has_property(path2) == has_path2
