"""
Test suite for custom error messages functionality.

Tests cover basic custom error message support in Lock validation.
"""

from stageflow.elements import DictElement
from stageflow.lock import Lock, LockFactory, LockType


class TestCustomErrorMessagesBasic:
    """Basic custom error message functionality tests."""

    def test_lock_with_custom_message_on_failure(self):
        """Custom message appears when validation fails."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                "error_message": "Task must be active before review",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Task must be active before review"

    def test_lock_without_custom_message_uses_default(self):
        """Generated message used when no custom message."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                # No error_message field
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert "should equal" in result.error_message.lower()
        assert "active" in result.error_message

    def test_lock_with_custom_message_on_success_no_error(self):
        """No error message when validation succeeds."""
        element = DictElement({"status": "active"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                "error_message": "Task must be active",
            }
        )

        result = lock.validate(element)
        assert result.success is True
        assert result.error_message == ""

    def test_custom_message_with_empty_string(self):
        """Empty string custom message falls back to generated."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                "error_message": "",  # Empty string
            }
        )

        result = lock.validate(element)
        assert result.success is False
        # Should use generated message since empty string is falsy
        assert "should equal" in result.error_message.lower()

    def test_custom_message_with_special_characters(self):
        """Custom messages with quotes, newlines, etc. work."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                "error_message": "Task must be 'active'\nPlease check the status.\tContact support if needed.",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert "Task must be 'active'" in result.error_message
        assert "\n" in result.error_message
        assert "\t" in result.error_message


class TestCustomErrorMessagesShorthand:
    """Shorthand syntax custom message tests."""

    def test_exists_shorthand_with_custom_message(self):
        """Shorthand exists syntax supports custom message."""
        element = DictElement({})
        lock = LockFactory.create(
            {"exists": "work_done", "error_message": "Work Done section is required"}
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Work Done section is required"

    def test_is_true_shorthand_with_custom_message(self):
        """Shorthand is_true syntax supports custom message."""
        element = DictElement({"flag": False})
        lock = LockFactory.create(
            {"is_true": "flag", "error_message": "Flag must be enabled"}
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Flag must be enabled"

    def test_is_false_shorthand_with_custom_message(self):
        """Shorthand is_false syntax supports custom message."""
        element = DictElement({"flag": True})
        lock = LockFactory.create(
            {"is_false": "flag", "error_message": "Flag must be disabled"}
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Flag must be disabled"


class TestCustomErrorMessagesAllLockTypes:
    """Custom messages work with all lock types."""

    def test_custom_message_exists_lock(self):
        """EXISTS lock with custom message."""
        element = DictElement({})
        lock = Lock(
            {
                "type": LockType.EXISTS,
                "property_path": "field",
                "error_message": "Field is required",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Field is required"

    def test_custom_message_equals_lock(self):
        """EQUALS lock with custom message."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
                "error_message": "Status must be active",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Status must be active"

    def test_custom_message_greater_than_lock(self):
        """GREATER_THAN lock with custom message."""
        element = DictElement({"count": 1})
        lock = Lock(
            {
                "type": LockType.GREATER_THAN,
                "property_path": "count",
                "expected_value": 5,
                "error_message": "Count must exceed 5",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Count must exceed 5"

    def test_custom_message_regex_lock(self):
        """REGEX lock with custom message."""
        element = DictElement({"email": "invalid-email"})
        lock = Lock(
            {
                "type": LockType.REGEX,
                "property_path": "email",
                "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
                "error_message": "Email format is invalid",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Email format is invalid"

    def test_custom_message_length_lock(self):
        """LENGTH lock with custom message."""
        element = DictElement({"items": [1, 2, 3, 4, 5, 6]})
        lock = Lock(
            {
                "type": LockType.LENGTH,
                "property_path": "items",
                "expected_value": 3,
                "error_message": "List must have exactly 3 items",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "List must have exactly 3 items"


class TestCustomErrorMessagesExceptions:
    """Custom messages in exception scenarios."""

    def test_custom_message_on_property_resolution_error(self):
        """Custom message used when property path doesn't exist."""
        element = DictElement({})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "deeply.nested.missing.path",
                "expected_value": "value",
                "error_message": "Configuration is missing",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        assert result.error_message == "Configuration is missing"


class TestCustomErrorMessagesBackwardCompatibility:
    """Backward compatibility tests."""

    def test_existing_locks_without_custom_messages_work(self):
        """Regression: existing locks without messages still work."""
        element = DictElement({"status": "pending"})
        lock = Lock(
            {
                "type": LockType.EQUALS,
                "property_path": "status",
                "expected_value": "active",
            }
        )

        result = lock.validate(element)
        assert result.success is False
        # Should have generated message
        assert len(result.error_message) > 0
        assert "should equal" in result.error_message.lower()

    def test_lock_stores_custom_message(self):
        """Lock correctly stores custom error message."""
        lock = Lock(
            {
                "type": LockType.EXISTS,
                "property_path": "field",
                "error_message": "Custom message",
            }
        )

        assert lock.custom_error_message == "Custom message"

    def test_lock_without_custom_message_has_none(self):
        """Lock without custom message has None."""
        lock = Lock({"type": LockType.EXISTS, "property_path": "field"})

        assert lock.custom_error_message is None
