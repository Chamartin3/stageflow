#!/usr/bin/env python3
"""Quick test for the new Lock class interface."""

import asyncio

from stageflow.core.element import DictElement
from stageflow.gates import (
    LockType,
    Lock,
    PropertyNotFoundError,
    ValidationResult,
)


def test_new_lock_interface():
    """Test the new Lock class interface matches task requirements."""
    # Create test data
    element = DictElement({
        "user": {
            "name": "Alice",
            "age": 25,
            "email": "alice@example.com"
        },
        "items": ["apple", "banana", "cherry"]
    })

    # Test basic lock creation and configuration
    lock = NewLock(LockType.EQUALS, "user.name", "Alice")
    assert lock.lock_type == LockType.EQUALS
    assert lock.property_path == "user.name"
    assert lock.expected_value == "Alice"

    # Test property resolution
    resolved = lock.resolve_property(element)
    assert resolved == "Alice"

    # Test validation returns ValidationResult
    result = lock.validate(element)
    assert isinstance(result, ValidationResult)
    assert result.success == True
    assert result.property_path == "user.name"
    assert result.lock_type == LockType.EQUALS
    assert result.actual_value == "Alice"
    assert result.expected_value == "Alice"

    # Test failed validation
    fail_lock = NewLock(LockType.EQUALS, "user.name", "Bob")
    fail_result = fail_lock.validate(element)
    assert isinstance(fail_result, ValidationResult)
    assert fail_result.success == False
    assert fail_result.error_message != ""
    assert fail_result.action_message != ""

    # Test access control
    assert lock.can_access(element, "read") == True
    assert lock.can_access(element, "write") == True
    assert lock.can_access(element, "execute") == False

    # Test property not found error
    missing_lock = NewLock(LockType.EQUALS, "nonexistent.property", "value")
    try:
        missing_lock.resolve_property(element)
        assert False, "Should have raised PropertyNotFoundError"
    except PropertyNotFoundError:
        pass

    print("✓ All new Lock interface tests passed!")


async def test_async_validation():
    """Test async validation method."""
    element = DictElement({"score": 85})
    lock = NewLock(LockType.GREATER_THAN, "score", 80)

    result = await lock.validate_async(element)
    assert isinstance(result, ValidationResult)
    assert result.success == True
    print("✓ Async validation test passed!")


def test_complex_property_paths():
    """Test property path resolution with complex paths."""
    element = DictElement({
        "users": [
            {"name": "Alice", "settings": {"theme": "dark"}},
            {"name": "Bob", "settings": {"theme": "light"}}
        ]
    })

    # Test array access
    lock = NewLock(LockType.EQUALS, "users[0].name", "Alice")
    result = lock.validate(element)
    assert result.success == True

    # Test nested property access
    lock2 = NewLock(LockType.EQUALS, "users[0].settings.theme", "dark")
    result2 = lock2.validate(element)
    assert result2.success == True

    print("✓ Complex property path tests passed!")


if __name__ == "__main__":
    test_new_lock_interface()
    asyncio.run(test_async_validation())
    test_complex_property_paths()
    print("🎉 All tests passed! New Lock class implementation is working correctly.")
