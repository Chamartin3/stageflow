"""Lock types and validation logic for StageFlow."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class LockType(Enum):
    """
    Built-in lock types for common validation scenarios.

    Each lock type provides a specific validation behavior:
    - EXISTS: Property must exist and not be None/empty
    - EQUALS: Property must equal specific value
    - GREATER_THAN: Numeric property must be greater than value
    - LESS_THAN: Numeric property must be less than value
    - REGEX: String property must match regex pattern
    - IN_LIST: Property value must be in allowed list
    - NOT_IN_LIST: Property value must not be in blocked list
    - CUSTOM: Custom validation function
    """

    EXISTS = "exists"
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX = "regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Lock:
    """
    Individual validation constraint within a gate.

    Locks represent atomic validation rules that check specific properties
    of an element against defined criteria.
    """

    property_path: str
    lock_type: LockType
    expected_value: Any = None
    validator_name: str | None = None  # For custom validators
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Validate lock configuration after initialization."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate that required fields are present for specific lock types
        if self.lock_type in [
            LockType.EQUALS,
            LockType.GREATER_THAN,
            LockType.LESS_THAN,
            LockType.REGEX,
            LockType.IN_LIST,
            LockType.NOT_IN_LIST,
        ] and self.expected_value is None:
            raise ValueError(f"Lock type {self.lock_type.value} requires expected_value")

        if self.lock_type == LockType.CUSTOM and not self.validator_name:
            raise ValueError("Custom lock type requires validator_name")

    def validate(self, element: "Element") -> bool:
        """
        Validate element against this lock's criteria.

        Args:
            element: Element to validate

        Returns:
            True if validation passes, False otherwise
        """
        try:
            value = element.get_property(self.property_path)
        except (KeyError, AttributeError, TypeError):
            # Property doesn't exist or cannot be accessed
            return self.lock_type == LockType.EXISTS and self.expected_value is False

        return self._validate_value(value)

    def _validate_value(self, value: Any) -> bool:
        """
        Validate a specific value against this lock's criteria.

        Args:
            value: Value to validate

        Returns:
            True if validation passes, False otherwise
        """
        if self.lock_type == LockType.EXISTS:
            if self.expected_value is False:
                return value is None or value == "" or value == []
            else:
                return value is not None and value != "" and value != []

        if value is None:
            return False

        if self.lock_type == LockType.EQUALS:
            return value == self.expected_value

        if self.lock_type == LockType.GREATER_THAN:
            try:
                return float(value) > float(self.expected_value)
            except (ValueError, TypeError):
                return False

        if self.lock_type == LockType.LESS_THAN:
            try:
                return float(value) < float(self.expected_value)
            except (ValueError, TypeError):
                return False

        if self.lock_type == LockType.REGEX:
            try:
                return bool(re.match(str(self.expected_value), str(value)))
            except re.error:
                return False

        if self.lock_type == LockType.IN_LIST:
            return value in self.expected_value

        if self.lock_type == LockType.NOT_IN_LIST:
            return value not in self.expected_value

        if self.lock_type == LockType.CUSTOM:
            # Custom validation would be handled by extension system
            return False

        return False

    def get_failure_message(self, element: "Element") -> str:
        """
        Generate human-readable failure message.

        Args:
            element: Element that failed validation

        Returns:
            Descriptive error message
        """
        try:
            value = element.get_property(self.property_path)
        except (KeyError, AttributeError, TypeError):
            value = "<missing>"

        if self.lock_type == LockType.EXISTS:
            if self.expected_value is False:
                return f"Property '{self.property_path}' should not exist but has value: {value}"
            else:
                return f"Property '{self.property_path}' is required but missing or empty"

        if self.lock_type == LockType.EQUALS:
            return f"Property '{self.property_path}' should equal '{self.expected_value}' but is '{value}'"

        if self.lock_type == LockType.GREATER_THAN:
            return f"Property '{self.property_path}' should be greater than {self.expected_value} but is {value}"

        if self.lock_type == LockType.LESS_THAN:
            return f"Property '{self.property_path}' should be less than {self.expected_value} but is {value}"

        if self.lock_type == LockType.REGEX:
            return f"Property '{self.property_path}' should match pattern '{self.expected_value}' but is '{value}'"

        if self.lock_type == LockType.IN_LIST:
            return f"Property '{self.property_path}' should be one of {self.expected_value} but is '{value}'"

        if self.lock_type == LockType.NOT_IN_LIST:
            return f"Property '{self.property_path}' should not be one of {self.expected_value} but is '{value}'"

        if self.lock_type == LockType.CUSTOM:
            return f"Custom validation '{self.validator_name}' failed for property '{self.property_path}'"

        return f"Validation failed for property '{self.property_path}'"

    def get_action_message(self, element: "Element") -> str:
        """
        Generate actionable message for fixing validation failure.

        Args:
            element: Element that failed validation

        Returns:
            Actionable instruction for fixing the issue
        """
        if self.lock_type == LockType.EXISTS:
            if self.expected_value is False:
                return f"Remove property: {self.property_path}"
            else:
                return f"Set missing field: {self.property_path}"

        if self.lock_type == LockType.EQUALS:
            return f"Set {self.property_path} to '{self.expected_value}'"

        if self.lock_type == LockType.GREATER_THAN:
            return f"Increase {self.property_path} to be greater than {self.expected_value}"

        if self.lock_type == LockType.LESS_THAN:
            return f"Decrease {self.property_path} to be less than {self.expected_value}"

        if self.lock_type == LockType.REGEX:
            return f"Update {self.property_path} to match pattern: {self.expected_value}"

        if self.lock_type == LockType.IN_LIST:
            return f"Set {self.property_path} to one of: {', '.join(map(str, self.expected_value))}"

        if self.lock_type == LockType.NOT_IN_LIST:
            return f"Change {self.property_path} from restricted value"

        if self.lock_type == LockType.CUSTOM:
            return f"Fix custom validation for {self.property_path}"

        return f"Fix validation for {self.property_path}"


# Import here to avoid circular imports
from stageflow.core.element import Element
