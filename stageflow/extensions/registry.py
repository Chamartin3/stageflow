"""Custom lock registry for StageFlow extensions."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from stageflow.core.element import Element


@dataclass
class CustomValidator:
    """Custom validation function wrapper."""

    name: str
    validator: Callable[[Element, str, Any], bool]
    description: str = ""
    expected_params: dict[str, str] = None

    def __post_init__(self):
        if self.expected_params is None:
            self.expected_params = {}


class CustomLockRegistry:
    """
    Registry for custom lock validators in StageFlow.

    Allows registration and management of custom validation functions
    that can be used in lock definitions.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._validators: dict[str, CustomValidator] = {}

    def register(
        self,
        name: str,
        validator: Callable[[Element, str, Any], bool],
        description: str = "",
        expected_params: dict[str, str] = None,
    ):
        """
        Register a custom validator.

        Args:
            name: Unique name for the validator
            validator: Function that takes (element, property_path, expected_value) and returns bool
            description: Human-readable description of the validator
            expected_params: Dictionary describing expected parameters

        Raises:
            ValueError: If validator name already exists
        """
        if name in self._validators:
            raise ValueError(f"Validator '{name}' is already registered")

        custom_validator = CustomValidator(
            name=name,
            validator=validator,
            description=description,
            expected_params=expected_params or {},
        )

        self._validators[name] = custom_validator

    def unregister(self, name: str):
        """
        Unregister a custom validator.

        Args:
            name: Name of validator to remove

        Raises:
            KeyError: If validator doesn't exist
        """
        if name not in self._validators:
            raise KeyError(f"Validator '{name}' is not registered")

        del self._validators[name]

    def get_validator(self, name: str) -> CustomValidator:
        """
        Get a registered validator.

        Args:
            name: Name of validator to retrieve

        Returns:
            CustomValidator instance

        Raises:
            KeyError: If validator doesn't exist
        """
        if name not in self._validators:
            raise KeyError(f"Validator '{name}' is not registered")

        return self._validators[name]

    def validate(self, name: str, element: Element, property_path: str, expected_value: Any) -> bool:
        """
        Execute a custom validator.

        Args:
            name: Name of validator to execute
            element: Element to validate
            property_path: Property path to validate
            expected_value: Expected value or parameters

        Returns:
            True if validation passes, False otherwise

        Raises:
            KeyError: If validator doesn't exist
        """
        validator = self.get_validator(name)
        try:
            return validator.validator(element, property_path, expected_value)
        except Exception:
            # Custom validators should handle their own exceptions
            # Return False for any validation errors
            return False

    def list_validators(self) -> dict[str, str]:
        """
        List all registered validators.

        Returns:
            Dictionary mapping validator names to descriptions
        """
        return {name: validator.description for name, validator in self._validators.items()}

    def clear(self):
        """Clear all registered validators."""
        self._validators.clear()


# Global registry instance
_global_registry = CustomLockRegistry()


def register_validator(
    name: str,
    validator: Callable[[Element, str, Any], bool],
    description: str = "",
    expected_params: dict[str, str] = None,
):
    """
    Register a validator in the global registry.

    Args:
        name: Unique name for the validator
        validator: Validation function
        description: Human-readable description
        expected_params: Dictionary describing expected parameters
    """
    _global_registry.register(name, validator, description, expected_params)


def get_global_registry() -> CustomLockRegistry:
    """Get the global custom lock registry."""
    return _global_registry


# Example custom validators
def _validate_email_domain(element: Element, property_path: str, expected_value: Any) -> bool:
    """Validate email has specific domain."""
    try:
        email = element.get_property(property_path)
        if not isinstance(email, str) or "@" not in email:
            return False
        domain = email.split("@")[1]
        if isinstance(expected_value, str):
            return domain == expected_value
        elif isinstance(expected_value, list):
            return domain in expected_value
        return False
    except (KeyError, IndexError, AttributeError):
        return False


def _validate_phone_format(element: Element, property_path: str, expected_value: Any) -> bool:
    """Validate phone number format."""
    try:
        import re

        phone = element.get_property(property_path)
        if not isinstance(phone, str):
            return False

        # Simple phone validation - can be customized
        pattern = r"^\+?[\d\s\-\(\)]+$"
        return bool(re.match(pattern, phone))
    except (KeyError, AttributeError):
        return False


def _validate_date_range(element: Element, property_path: str, expected_value: Any) -> bool:
    """Validate date is within specified range."""
    try:
        from datetime import datetime

        date_str = element.get_property(property_path)
        if not isinstance(date_str, str):
            return False

        date_obj = datetime.fromisoformat(date_str)

        if isinstance(expected_value, dict):
            min_date = expected_value.get("min")
            max_date = expected_value.get("max")

            if min_date:
                min_obj = datetime.fromisoformat(min_date)
                if date_obj < min_obj:
                    return False

            if max_date:
                max_obj = datetime.fromisoformat(max_date)
                if date_obj > max_obj:
                    return False

            return True

        return False
    except (KeyError, ValueError, AttributeError):
        return False


# Register example validators
register_validator(
    "email_domain",
    _validate_email_domain,
    "Validate email has specific domain(s)",
    {"expected_value": "string or list of allowed domains"},
)

register_validator(
    "phone_format",
    _validate_phone_format,
    "Validate phone number format",
    {"expected_value": "not used"},
)

register_validator(
    "date_range",
    _validate_date_range,
    "Validate date is within specified range",
    {"expected_value": "dict with 'min' and/or 'max' ISO date strings"},
)
