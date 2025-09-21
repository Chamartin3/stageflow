"""Lock types and validation logic for StageFlow.

This module provides the core validation framework through LockType enumeration
and Lock classes. It supports both built-in validation patterns and custom
validator registration for extensible validation logic.

Example Usage:
    Basic lock creation:
        >>> from stageflow.gates.lock import Lock, LockType
        >>> lock = Lock("user.age", LockType.GREATER_THAN, 18)

    Custom validator registration:
        >>> register_validator("email", lambda v, _: "@" in str(v))
        >>> email_lock = Lock("email", LockType.CUSTOM, validator_name="email")

    Range validation:
        >>> price_lock = Lock("price", LockType.RANGE, [10.0, 100.0])

    Type checking:
        >>> name_lock = Lock("name", LockType.TYPE_CHECK, str)
"""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Custom validator registry
_custom_validators: dict[str, Callable[[Any, Any], bool]] = {}


def register_validator(name: str, validator: Callable[[Any, Any], bool]) -> None:
    """Register a custom validator function.

    Custom validators enable extending the validation system with domain-specific
    validation logic. Validators should be thread-safe and handle edge cases gracefully.

    Args:
        name: Unique name for the validator. Will overwrite existing validators
              with the same name.
        validator: Function that takes (value, expected_value) and returns bool.
                  Should return True if validation passes, False otherwise.
                  Must not raise exceptions under normal circumstances.

    Example:
        >>> def validate_email(value, expected):
        ...     return isinstance(value, str) and "@" in value
        >>> register_validator("email", validate_email)
        >>> lock = Lock("user.email", LockType.CUSTOM, validator_name="email")

    Note:
        Custom validators are stored in a global registry and persist for the
        lifetime of the application. Consider using descriptive names to avoid
        naming conflicts.
    """
    _custom_validators[name] = validator


def get_validator(name: str) -> Callable[[Any, Any], bool] | None:
    """Get a registered custom validator by name.

    Args:
        name: Name of the validator

    Returns:
        Validator function or None if not found
    """
    return _custom_validators.get(name)


def list_validators() -> list[str]:
    """List all registered custom validator names.

    Returns:
        List of validator names
    """
    return list(_custom_validators.keys())


def clear_validators() -> None:
    """Clear all registered custom validators.

    Note: This is primarily intended for testing purposes.
    """
    _custom_validators.clear()


class LockType(Enum):
    """
    Built-in lock types for common validation scenarios.

    Each lock type provides a specific validation behavior:
    - EXISTS: Property must exist and not be None/empty
        expected_value: bool (default True for existence check)
    - EQUALS: Property must equal specific value
        expected_value: Any value to compare against
    - GREATER_THAN: Numeric property must be greater than value
        expected_value: numeric value for comparison
    - LESS_THAN: Numeric property must be less than value
        expected_value: numeric value for comparison
    - CONTAINS: String/collection must contain specified substring/element
        expected_value: substring or element to search for
    - REGEX: String property must match regex pattern
        expected_value: regex pattern string
    - TYPE_CHECK: Property must be of specified type
        expected_value: type object or string type name
    - RANGE: Numeric property must be within specified range (inclusive)
        expected_value: [min, max] list/tuple
    - LENGTH: String/collection length must match criteria
        expected_value: int for exact length, dict with 'min'/'max' keys,
                       or [min, max] list/tuple
    - NOT_EMPTY: Property must not be empty (string/collection)
        expected_value: not used (can be None)
    - IN_LIST: Property value must be in allowed list
        expected_value: list/tuple of allowed values
    - NOT_IN_LIST: Property value must not be in blocked list
        expected_value: list/tuple of blocked values
    - CUSTOM: Custom validation function
        expected_value: passed to custom validator
        validator_name: required, name of registered validator
    """

    EXISTS = "exists"
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    REGEX = "regex"
    TYPE_CHECK = "type_check"
    RANGE = "range"
    LENGTH = "length"
    NOT_EMPTY = "not_empty"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of validation operation with detailed reporting.

    Contains success/failure status, detailed error messages,
    and actionable suggestions for fixing issues.
    """

    success: bool
    property_path: str
    lock_type: LockType
    actual_value: Any = None
    expected_value: Any = None
    error_message: str = ""
    action_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Custom exceptions for lock operations
class PropertyNotFoundError(Exception):
    """Raised when a property path cannot be resolved."""


class ValidationError(Exception):
    """Raised when validation fails."""


class InvalidPathError(Exception):
    """Raised when a property path is malformed."""


class AccessDeniedError(Exception):
    """Raised when access to a property is denied."""


class Lock:
    """
    Lock class for property resolution and validation on Elements.

    Combines property path resolution with LockType validation to ensure
    data integrity and proper access control.
    """

    def __init__(self, lock_type_or_path: LockType | str, property_path_or_type: str | LockType = None, expected_value: Any = None, validator_name: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        """
        Initialize Lock with LockType and property path.

        Supports both new and legacy constructor signatures:
        - New: Lock(lock_type, property_path, expected_value, ...)
        - Legacy: Lock(property_path, lock_type, expected_value, ...)

        Args:
            lock_type_or_path: LockType for new signature, or property_path for legacy
            property_path_or_type: property_path for new signature, or LockType for legacy
            expected_value: Expected value for validation (if required)
            validator_name: Name of custom validator (for CUSTOM lock type)
            metadata: Additional metadata for the lock
        """
        # Detect which signature is being used
        if isinstance(lock_type_or_path, LockType):
            # New signature: Lock(lock_type, property_path, ...)
            self.lock_type = lock_type_or_path
            self.property_path = property_path_or_type
        elif isinstance(lock_type_or_path, str) and isinstance(property_path_or_type, LockType):
            # Legacy signature: Lock(property_path, lock_type, ...)
            self.property_path = lock_type_or_path
            self.lock_type = property_path_or_type
        else:
            raise TypeError(f"Invalid Lock constructor arguments. Expected (LockType, str) or (str, LockType), got ({type(lock_type_or_path)}, {type(property_path_or_type)})")

        self.expected_value = expected_value
        self.validator_name = validator_name
        self.metadata = metadata or {}

        # Validate lock configuration
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate lock configuration after initialization."""
        if not self.property_path:
            raise InvalidPathError("Property path cannot be empty")

        # Validate that required fields are present for specific lock types
        if self.lock_type in [
            LockType.EQUALS,
            LockType.GREATER_THAN,
            LockType.LESS_THAN,
            LockType.CONTAINS,
            LockType.REGEX,
            LockType.TYPE_CHECK,
            LockType.RANGE,
            LockType.LENGTH,
            LockType.IN_LIST,
            LockType.NOT_IN_LIST,
        ] and self.expected_value is None:
            raise ValueError(f"Lock type {self.lock_type.value} requires expected_value")

        if self.lock_type == LockType.CUSTOM and not self.validator_name:
            raise ValueError("Custom lock type requires validator_name")

    def resolve_property(self, element: "Element") -> Any:
        """
        Resolve property path on the given Element.

        Args:
            element: Element to resolve property on

        Returns:
            The resolved property value

        Raises:
            PropertyNotFoundError: If property path doesn't exist
            InvalidPathError: If property path is malformed
        """
        try:
            return element.get_property(self.property_path)
        except (KeyError, AttributeError, TypeError, IndexError) as e:
            raise PropertyNotFoundError(f"Property '{self.property_path}' not found: {e}")
        except Exception as e:
            raise InvalidPathError(f"Invalid property path '{self.property_path}': {e}")

    def validate(self, element: "Element") -> ValidationResult:
        """
        Validate the resolved property according to LockType rules.

        Args:
            element: Element to validate

        Returns:
            ValidationResult with success status and detailed information
        """
        return self._validate_detailed(element)

    def _validate_detailed(self, element: "Element") -> ValidationResult:
        """
        Internal method for detailed validation returning ValidationResult.

        Args:
            element: Element to validate

        Returns:
            ValidationResult with success status and detailed information
        """
        try:
            value = self.resolve_property(element)
        except PropertyNotFoundError:
            # Property doesn't exist - handle based on lock type
            if self.lock_type == LockType.EXISTS and self.expected_value is False:
                return ValidationResult(
                    success=True,
                    property_path=self.property_path,
                    lock_type=self.lock_type,
                    actual_value=None,
                    expected_value=self.expected_value,
                    metadata=self.metadata.copy()
                )
            else:
                return ValidationResult(
                    success=False,
                    property_path=self.property_path,
                    lock_type=self.lock_type,
                    actual_value=None,
                    expected_value=self.expected_value,
                    error_message=self._get_failure_message(None),
                    action_message=self._get_action_message(None),
                    metadata=self.metadata.copy()
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                property_path=self.property_path,
                lock_type=self.lock_type,
                actual_value=None,
                expected_value=self.expected_value,
                error_message=f"Error resolving property: {e}",
                action_message="Fix property path or element structure",
                metadata=self.metadata.copy()
            )

        # Validate the resolved value
        is_valid = self._validate_value(value)

        return ValidationResult(
            success=is_valid,
            property_path=self.property_path,
            lock_type=self.lock_type,
            actual_value=value,
            expected_value=self.expected_value,
            error_message="" if is_valid else self._get_failure_message(value),
            action_message="" if is_valid else self._get_action_message(value),
            metadata=self.metadata.copy()
        )

    async def validate_async(self, element: "Element") -> ValidationResult:
        """
        Asynchronously validate the resolved property.

        Args:
            element: Element to validate

        Returns:
            ValidationResult with success status and detailed information
        """
        # For now, just run the synchronous validation in an async context
        # This allows for future extension to truly async validation
        return await asyncio.get_event_loop().run_in_executor(None, self.validate, element)

    def can_access(self, element: "Element", access_type: str) -> bool:
        """
        Check if the specified access type is allowed.

        Args:
            element: Element to check access for
            access_type: Type of access ("read", "write", "execute")

        Returns:
            True if access is allowed, False otherwise
        """
        # Basic access control - can be extended for more sophisticated logic
        try:
            # If we can resolve the property, read access is allowed
            self.resolve_property(element)

            if access_type.lower() == "read":
                return True
            elif access_type.lower() == "write":
                # Write access depends on lock type - some locks prevent writes
                readonly_locks = {LockType.EXISTS, LockType.TYPE_CHECK}
                return self.lock_type not in readonly_locks
            elif access_type.lower() == "execute":
                # Execute access only for callable properties
                value = self.resolve_property(element)
                return callable(value)
            else:
                return False
        except (PropertyNotFoundError, InvalidPathError):
            return False

    def validate_legacy(self, element: "Element") -> bool:
        """
        Legacy validate method that returns bool for backward compatibility.

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

    def __call__(self, element: "Element") -> bool:
        """
        Allow Lock to be called directly for backward compatibility.

        Args:
            element: Element to validate

        Returns:
            True if validation passes, False otherwise
        """
        return self.validate_legacy(element)

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
            # Only validate strings with regex
            if not isinstance(value, str):
                return False
            try:
                return bool(re.match(str(self.expected_value), value))
            except re.error:
                return False

        if self.lock_type == LockType.IN_LIST:
            return value in self.expected_value

        if self.lock_type == LockType.NOT_IN_LIST:
            return value not in self.expected_value

        if self.lock_type == LockType.CONTAINS:
            try:
                if isinstance(value, str) and isinstance(self.expected_value, str):
                    return self.expected_value in value
                elif hasattr(value, '__contains__'):
                    return self.expected_value in value
                else:
                    return False
            except (TypeError, AttributeError):
                return False

        if self.lock_type == LockType.TYPE_CHECK:
            if isinstance(self.expected_value, str):
                # Handle string type names
                type_map = {
                    'str': str, 'string': str,
                    'int': int, 'integer': int,
                    'float': float,
                    'bool': bool, 'boolean': bool,
                    'list': list,
                    'dict': dict, 'dictionary': dict,
                    'tuple': tuple,
                    'set': set
                }
                expected_type = type_map.get(self.expected_value.lower())
                if expected_type:
                    return isinstance(value, expected_type)
                else:
                    return False
            elif isinstance(self.expected_value, type):
                return isinstance(value, self.expected_value)
            else:
                return False

        if self.lock_type == LockType.RANGE:
            try:
                num_value = float(value)
                if isinstance(self.expected_value, (list, tuple)) and len(self.expected_value) == 2:
                    min_val, max_val = self.expected_value
                    return float(min_val) <= num_value <= float(max_val)
                else:
                    return False
            except (ValueError, TypeError):
                return False

        if self.lock_type == LockType.LENGTH:
            try:
                length = len(value)
                if isinstance(self.expected_value, int):
                    return length == self.expected_value
                elif isinstance(self.expected_value, dict):
                    # Support min/max length constraints
                    min_len = self.expected_value.get('min')
                    max_len = self.expected_value.get('max')
                    if min_len is not None and length < min_len:
                        return False
                    if max_len is not None and length > max_len:
                        return False
                    return True
                elif isinstance(self.expected_value, (list, tuple)) and len(self.expected_value) == 2:
                    min_len, max_len = self.expected_value
                    return min_len <= length <= max_len
                else:
                    return False
            except TypeError:
                return False

        if self.lock_type == LockType.NOT_EMPTY:
            if isinstance(value, str):
                return len(value.strip()) > 0
            elif hasattr(value, '__len__'):
                return len(value) > 0
            else:
                return value is not None

        if self.lock_type == LockType.CUSTOM:
            if self.validator_name:
                validator = get_validator(self.validator_name)
                if validator:
                    try:
                        return validator(value, self.expected_value)
                    except (ValueError, TypeError, AttributeError):
                        return False
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

        return self._get_failure_message(value)

    def get_action_message(self, element: "Element") -> str:
        """
        Generate actionable message for fixing validation failure.

        Args:
            element: Element that failed validation

        Returns:
            Actionable instruction for fixing the issue
        """
        try:
            value = element.get_property(self.property_path)
        except (KeyError, AttributeError, TypeError):
            value = None

        return self._get_action_message(value)

    def _get_failure_message(self, value: Any) -> str:
        """
        Generate human-readable failure message.

        Args:
            value: The actual value that failed validation

        Returns:
            Descriptive error message
        """
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

        if self.lock_type == LockType.CONTAINS:
            return f"Property '{self.property_path}' should contain '{self.expected_value}' but is '{value}'"

        if self.lock_type == LockType.TYPE_CHECK:
            expected_type = self.expected_value if isinstance(self.expected_value, str) else getattr(self.expected_value, '__name__', str(self.expected_value))
            actual_type = type(value).__name__
            return f"Property '{self.property_path}' should be of type '{expected_type}' but is '{actual_type}' with value '{value}'"

        if self.lock_type == LockType.RANGE:
            if isinstance(self.expected_value, (list, tuple)) and len(self.expected_value) == 2:
                min_val, max_val = self.expected_value
                return f"Property '{self.property_path}' should be between {min_val} and {max_val} but is {value}"
            else:
                return f"Property '{self.property_path}' should be within range {self.expected_value} but is {value}"

        if self.lock_type == LockType.LENGTH:
            try:
                actual_length = len(value)
            except TypeError:
                actual_length = "<non-measurable>"

            if isinstance(self.expected_value, int):
                return f"Property '{self.property_path}' should have length {self.expected_value} but has length {actual_length}"
            elif isinstance(self.expected_value, dict):
                constraints = []
                if 'min' in self.expected_value:
                    constraints.append(f"at least {self.expected_value['min']}")
                if 'max' in self.expected_value:
                    constraints.append(f"at most {self.expected_value['max']}")
                constraint_str = " and ".join(constraints)
                return f"Property '{self.property_path}' should have length {constraint_str} but has length {actual_length}"
            else:
                return f"Property '{self.property_path}' should have length {self.expected_value} but has length {actual_length}"

        if self.lock_type == LockType.NOT_EMPTY:
            return f"Property '{self.property_path}' should not be empty but is '{value}'"

        if self.lock_type == LockType.CUSTOM:
            return f"Custom validation '{self.validator_name}' failed for property '{self.property_path}'"

        return f"Validation failed for property '{self.property_path}'"

    def _get_action_message(self, value: Any) -> str:
        """
        Generate actionable message for fixing validation failure.

        Args:
            value: The actual value that failed validation

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

        if self.lock_type == LockType.CONTAINS:
            return f"Ensure {self.property_path} contains '{self.expected_value}'"

        if self.lock_type == LockType.TYPE_CHECK:
            expected_type = self.expected_value if isinstance(self.expected_value, str) else getattr(self.expected_value, '__name__', str(self.expected_value))
            return f"Change {self.property_path} to be of type {expected_type}"

        if self.lock_type == LockType.RANGE:
            if isinstance(self.expected_value, (list, tuple)) and len(self.expected_value) == 2:
                min_val, max_val = self.expected_value
                return f"Set {self.property_path} to a value between {min_val} and {max_val}"
            else:
                return f"Set {self.property_path} to a value within range {self.expected_value}"

        if self.lock_type == LockType.LENGTH:
            if isinstance(self.expected_value, int):
                return f"Adjust {self.property_path} to have exactly {self.expected_value} elements/characters"
            elif isinstance(self.expected_value, dict):
                constraints = []
                if 'min' in self.expected_value:
                    constraints.append(f"at least {self.expected_value['min']}")
                if 'max' in self.expected_value:
                    constraints.append(f"at most {self.expected_value['max']}")
                constraint_str = " and ".join(constraints)
                return f"Adjust {self.property_path} to have {constraint_str} elements/characters"
            else:
                return f"Adjust {self.property_path} length to match {self.expected_value}"

        if self.lock_type == LockType.NOT_EMPTY:
            return f"Provide a non-empty value for {self.property_path}"

        if self.lock_type == LockType.CUSTOM:
            return f"Fix custom validation for {self.property_path}"

        return f"Fix validation for {self.property_path}"




# Import here to avoid circular imports
from stageflow.core.element import Element