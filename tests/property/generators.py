"""Custom data generators for StageFlow property-based testing.

This module provides Hypothesis strategies for generating test data for StageFlow
domain objects. The generators produce valid instances of Elements, Locks, Gates,
and other core components to enable comprehensive property-based testing.

The generators are designed to:
- Create realistic test data that respects domain constraints
- Balance diversity with execution performance
- Support hierarchical generation (simple to complex objects)
- Enable focused testing of specific properties and behaviors
"""

from typing import Any

import hypothesis.strategies as st
from hypothesis import assume

from stageflow.core.element import DictElement
from stageflow.gates import Gate, GateOperation, Lock, LockType


# Basic data type generators
@st.composite
def valid_property_path(draw) -> str:
    """Generate valid property paths for element access.

    Creates paths using dot notation, bracket notation, and mixed notation
    that are valid for property resolution in DictElement.
    """
    # Simple paths
    simple_paths = st.sampled_from([
        "name", "email", "age", "active", "id", "status", "type", "value",
        "user_id", "profile", "settings", "data", "metadata", "config"
    ])

    # Nested paths
    nested_parts = st.lists(
        st.sampled_from([
            "profile", "settings", "address", "contact", "preferences",
            "account", "billing", "shipping", "details", "info"
        ]),
        min_size=1, max_size=3
    )

    # Array access paths
    array_indices = st.integers(min_value=0, max_value=10)

    path_type = draw(st.sampled_from(["simple", "nested", "array", "mixed"]))

    if path_type == "simple":
        return draw(simple_paths)
    elif path_type == "nested":
        parts = draw(nested_parts)
        return ".".join(parts)
    elif path_type == "array":
        base = draw(simple_paths)
        index = draw(array_indices)
        return f"{base}[{index}]"
    else:  # mixed
        parts = draw(nested_parts)
        if len(parts) > 1:
            # Add array access to one part
            index = draw(array_indices)
            insert_pos = draw(st.integers(min_value=0, max_value=len(parts)-1))
            parts[insert_pos] = f"{parts[insert_pos]}[{index}]"
        return ".".join(parts)


@st.composite
def nested_dict_data(draw, max_depth: int = 3, current_depth: int = 0) -> dict[str, Any]:
    """Generate nested dictionary data for DictElement testing.

    Creates realistic nested data structures with various data types
    and reasonable complexity for property resolution testing.
    """
    assume(current_depth < max_depth)

    # Base value generators
    strings = st.text(min_size=0, max_size=50)
    numbers = st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False))
    booleans = st.booleans()
    nulls = st.none()

    # List generators
    simple_lists = st.lists(
        st.one_of(strings, numbers, booleans, nulls),
        min_size=0, max_size=5
    )

    # Determine if we should add nested structures
    if current_depth < max_depth - 1:
        nested_dicts = st.deferred(lambda: nested_dict_data(max_depth, current_depth + 1))
        value_strategy = st.one_of(
            strings, numbers, booleans, nulls, simple_lists, nested_dicts
        )
    else:
        value_strategy = st.one_of(strings, numbers, booleans, nulls, simple_lists)

    # Generate reasonable number of keys
    num_keys = draw(st.integers(min_value=1, max_value=8))

    keys = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd"]),
                min_size=1, max_size=20),
        min_size=num_keys, max_size=num_keys, unique=True
    ))

    result = {}
    for key in keys:
        result[key] = draw(value_strategy)

    return result


@st.composite
def dict_element(draw) -> DictElement:
    """Generate DictElement instances with realistic data."""
    data = draw(nested_dict_data())
    return DictElement(data)


@st.composite
def lock_type_and_value(draw) -> tuple[LockType, Any]:
    """Generate valid LockType and corresponding expected_value pairs."""
    lock_type = draw(st.sampled_from(list(LockType)))

    if lock_type == LockType.EXISTS:
        expected_value = draw(st.one_of(st.booleans(), st.none()))
    elif lock_type == LockType.EQUALS:
        expected_value = draw(st.one_of(
            st.text(), st.integers(), st.floats(allow_nan=False), st.booleans()
        ))
    elif lock_type in [LockType.GREATER_THAN, LockType.LESS_THAN]:
        expected_value = draw(st.one_of(st.integers(), st.floats(allow_nan=False)))
    elif lock_type == LockType.CONTAINS:
        expected_value = draw(st.text(min_size=1, max_size=20))
    elif lock_type == LockType.REGEX:
        # Generate simple regex patterns that are likely to be valid
        patterns = [
            r".*", r".+", r"^[a-z]+$", r"^[A-Z]+$", r"^\d+$",
            r"^[a-zA-Z0-9]+$", r"@", r"\.", r"^test", r"end$"
        ]
        expected_value = draw(st.sampled_from(patterns))
    elif lock_type == LockType.TYPE_CHECK:
        expected_value = draw(st.sampled_from([str, int, float, bool, list, dict]))
    elif lock_type == LockType.RANGE:
        min_val = draw(st.integers(min_value=-100, max_value=100))
        max_val = draw(st.integers(min_value=min_val, max_value=min_val + 100))
        expected_value = [min_val, max_val]
    elif lock_type == LockType.LENGTH:
        length_type = draw(st.sampled_from(["exact", "min_max", "dict"]))
        if length_type == "exact":
            expected_value = draw(st.integers(min_value=0, max_value=20))
        elif length_type == "min_max":
            min_len = draw(st.integers(min_value=0, max_value=10))
            max_len = draw(st.integers(min_value=min_len, max_value=min_len + 10))
            expected_value = [min_len, max_len]
        else:  # dict
            min_len = draw(st.integers(min_value=0, max_value=10))
            max_len = draw(st.integers(min_value=min_len, max_value=min_len + 10))
            expected_value = {"min": min_len, "max": max_len}
    elif lock_type == LockType.NOT_EMPTY:
        expected_value = None
    elif lock_type in [LockType.IN_LIST, LockType.NOT_IN_LIST]:
        expected_value = draw(st.lists(
            st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1, max_size=5
        ))
    elif lock_type == LockType.CUSTOM:
        expected_value = draw(st.text())  # Custom validators can have any expected value
    else:
        expected_value = None

    return lock_type, expected_value


@st.composite
def lock_instance(draw) -> Lock:
    """Generate valid Lock instances."""
    property_path = draw(valid_property_path())
    lock_type, expected_value = draw(lock_type_and_value())

    # Handle custom validator case
    validator_name = None
    if lock_type == LockType.CUSTOM:
        validator_name = "test_validator"
        # Register a simple test validator if it doesn't exist
        from stageflow.gates import get_lock_validator as get_validator, register_lock_validator as register_validator
        if not get_validator("test_validator"):
            register_validator("test_validator", lambda v, e: str(v) == str(e))

    metadata = draw(st.one_of(
        st.none(),
        st.dictionaries(st.text(), st.text(), max_size=3)
    ))

    return Lock(
        property_path,
        lock_type,
        expected_value,
        validator_name,
        metadata
    )


def gate_operation() -> GateOperation:
    """Generate GateOperation values."""
    return st.just(GateOperation.AND)


@st.composite
def simple_gate(draw) -> Gate:
    """Generate simple Gate instances with locks only (no nested gates)."""
    name = draw(st.text(min_size=1, max_size=20))
    operation = draw(gate_operation())

    # Generate locks for AND operation
    num_locks = draw(st.integers(min_value=1, max_value=5))
    locks = [draw(lock_instance()) for _ in range(num_locks)]

    metadata = draw(st.dictionaries(st.text(), st.text(), max_size=3))

    return Gate.AND(*locks, name=name, **metadata)


@st.composite
def complex_gate(draw, max_depth: int = 2, current_depth: int = 0) -> Gate:
    """Generate complex Gate instances with potential nesting."""
    assume(current_depth < max_depth)

    name = draw(st.text(min_size=1, max_size=20))
    operation = draw(gate_operation())

    # Decide whether to include nested gates
    include_nested = current_depth < max_depth - 1 and draw(st.booleans())

    components = []

    # AND gate with multiple components
    num_components = draw(st.integers(min_value=1, max_value=4))
    for _ in range(num_components):
        if include_nested and draw(st.booleans()):
            component = draw(st.deferred(
                lambda: complex_gate(max_depth, current_depth + 1)
            ))
        else:
            component = draw(lock_instance())
        components.append(component)

    metadata = draw(st.dictionaries(st.text(), st.text(), max_size=3))

    return Gate.AND(*components, name=name, **metadata)


# Element data generators that guarantee certain properties exist
def element_with_property(property_path: str, value: Any = None) -> DictElement:
    """Generate DictElement that definitely has the specified property."""
    # Create a simple base structure
    base_data = {"test": "value", "number": 42, "flag": True}

    # Use the DictElement's own path parsing to understand the structure needed
    # For complex paths like 'profile[0].profile', we need to create nested structures

    try:
        # Try to parse the path by creating a mock structure
        parts = []
        i = 0
        current_part = ""

        while i < len(property_path):
            char = property_path[i]
            if char == '.':
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            elif char == '[':
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                # Find the closing bracket
                j = i + 1
                while j < len(property_path) and property_path[j] != ']':
                    j += 1
                if j < len(property_path):
                    index_str = property_path[i+1:j]
                    if index_str.isdigit():
                        parts.append(int(index_str))
                    else:
                        parts.append(index_str)
                    i = j
                else:
                    current_part += char
            else:
                current_part += char
            i += 1

        if current_part:
            parts.append(current_part)

        # Build the structure
        current = base_data
        for i, part in enumerate(parts[:-1]):
            if isinstance(part, int):
                # Array index - ensure current is a list
                if not isinstance(current, list):
                    # This shouldn't happen in our structure building
                    current = []
                while len(current) <= part:
                    current.append({})
                current = current[part]
            else:
                # Dictionary key
                if part not in current:
                    # Determine what type the next level should be
                    next_part = parts[i + 1] if i + 1 < len(parts) else None
                    if isinstance(next_part, int):
                        current[part] = []
                    else:
                        current[part] = {}
                current = current[part]

        # Set the final value
        final_part = parts[-1]
        if isinstance(final_part, int):
            while len(current) <= final_part:
                current.append(None)
            current[final_part] = value if value is not None else "test_value"
        else:
            current[final_part] = value if value is not None else "test_value"

    except Exception:
        # Fallback: create a simple structure
        if '.' in property_path:
            # Simple nested structure
            path_parts = property_path.split('.')
            current = base_data
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[path_parts[-1]] = value if value is not None else "test_value"
        else:
            # Simple key
            base_data[property_path] = value if value is not None else "test_value"

    return DictElement(base_data)


def element_without_property(property_path: str) -> DictElement:
    """Generate DictElement that definitely does NOT have the specified property."""
    # Create a simple base structure that's unlikely to have the specific property
    base_data = {"other_key": "other_value", "different": {"nested": "value"}}
    return DictElement(base_data)
