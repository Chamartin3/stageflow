"""Lock types and validation logic for StageFlow.

"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict

from stageflow.element import Element

# Custom validator registry


class LockMetaData(TypedDict, total=False):
    expected_value: Any
    min_value: int | None
    max_value: int | None


class LockType(Enum):
    """
    Built-in lock types for common validation scenarios.
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


    def failure_message(self, property_path: str, actual_value: Any, expected_value: Any = None) -> str:
        """Generate human-readable failure message for this lock type.

        Args:
            property_path: Path of the property being validated
            actual_value: The actual value that failed validation
            expected_value: The expected value or criteria for validation

        Returns:
            Descriptive error message
        """
        if self == LockType.EXISTS:
            return f"Property '{property_path}' is required but missing or empty"

        if self == LockType.EQUALS:
            return f"Property '{property_path}' should equal '{expected_value}' but is '{actual_value}'"

        if self == LockType.GREATER_THAN:
            return f"Property '{property_path}' should be greater than {expected_value} but is {actual_value}"

        if self == LockType.LESS_THAN:
            return f"Property '{property_path}' should be less than {expected_value} but is {actual_value}"

        if self == LockType.REGEX:
            return f"Property '{property_path}' should match pattern '{expected_value}' but is '{actual_value}'"

        if self == LockType.IN_LIST:
            return f"Property '{property_path}' should be one of {expected_value} but is '{actual_value}'"

        if self == LockType.NOT_IN_LIST:
            return f"Property '{property_path}' should not be one of {expected_value} but is '{actual_value}'"

        if self == LockType.CONTAINS:
            return f"Property '{property_path}' should contain '{expected_value}' but is '{actual_value}'"

        if self == LockType.TYPE_CHECK:
            expected_type = expected_value if isinstance(expected_value, str) else getattr(expected_value, '__name__', str(expected_value))
            actual_type = type(actual_value).__name__
            return f"Property '{property_path}' should be of type '{expected_type}' but is '{actual_type}' with value '{actual_value}'"

        if self == LockType.RANGE:
            if isinstance(expected_value, (list | tuple)) and len(expected_value) == 2:
                min_val, max_val = expected_value
                return f"Property '{property_path}' should be between {min_val} and {max_val} but is {actual_value}"

        return f"Property '{property_path}' failed validation for lock type '{self.value}'"


    def validate(self, value: Any, lock_meta:LockMetaData) -> bool:
        lock_type = self
        if lock_type == LockType.EXISTS:
            return value is not None and (not isinstance(value, str) or len(value.strip()) > 0)

        if lock_type == LockType.NOT_EMPTY:
            if isinstance(value, str):
                return len(value.strip()) > 0
            elif hasattr(value, '__len__'):
                return len(value) > 0
            else:
                return value is not None

        expected_value = lock_meta.get("expected_value")
        if lock_type == LockType.EQUALS:
            return value == expected_value

        # Size/length checks
        if lock_type == LockType.LENGTH:
            try:
                length = len(value)
                if isinstance(expected_value, int):
                    return length == expected_value
                else:
                    return False
            except TypeError:
                return False
        if lock_type in [LockType.GREATER_THAN, LockType.LESS_THAN, LockType.RANGE]:
            expected_value = lock_meta.get("expected_value", 0)
            expected_value = float(expected_value) if expected_value is not None else 0
            value = value if value is not None else 0
            min_val = lock_meta.get("min_value", 0)
            min_val = float(min_val) if min_val is not None else 0
            max_val = lock_meta.get("max_value", 0)
            max_val = float(max_val) if max_val is not None else 0


            if lock_type == LockType.GREATER_THAN:
                return float(value) > expected_value
            if lock_type == LockType.LESS_THAN:
                return float(value) < expected_value
            if lock_type == LockType.RANGE:
                return float(min_val) <= float(value) <= float(max_val)

        # Text comparisons
        if lock_type == LockType.REGEX:
            if not isinstance(value, str):
                return False
            try:
                return bool(re.match(str(expected_value), value))
            except re.error:
                return False

        # Collection checks
        if lock_type == LockType.CONTAINS:
            try:
                if isinstance(value, str) and isinstance(expected_value, str):
                    return expected_value in value
                elif hasattr(value, '__contains__'):
                    # For collections, check if expected_value is in the collection
                    # or if string representation matches any element
                    return (expected_value in value or
                            str(expected_value) in [str(item) for item in value])
                else:
                    return False
            except (TypeError, AttributeError):
                return False
        if lock_type == LockType.IN_LIST:
            if not isinstance(expected_value, (list | tuple | set)):
                return False
            return value in expected_value

        if lock_type == LockType.NOT_IN_LIST:
            return value not in expected_value


        if lock_type == LockType.TYPE_CHECK:
            if isinstance(expected_value, str):
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
                expected_type = type_map.get(expected_value.lower())
                if expected_type:
                    return isinstance(value, expected_type)
                else:
                    return False
            elif isinstance(expected_value, type):
                return isinstance(value, expected_value)
            else:
                return False
        raise ValueError(f"Unsupported lock type: {lock_type}")



@dataclass(frozen=True)
class LockResult:
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

class LockDefinitionDict(TypedDict):
    type: LockType
    property_path: str
    expected_value: str | int | LockMetaData


class LockShorthandDict(TypedDict):
    exists: str | None
    is_true: str | None
    is_false: str | None


LockDefinition = LockDefinitionDict | LockShorthandDict

class Lock:
    """
    Lock class for property resolution and validation on Elements.

    Combines property path resolution with LockType validation to ensure
    data integrity and proper access control.
    """

    lock_type: LockType
    property_path: str
    expected_value: Any
    validator_name: str | None

    def __init__(
        self,
        config: LockDefinitionDict
        ) -> None:
        lock_type_value = config.get("type")
        if isinstance(lock_type_value, str):
            # Handle case-insensitive lock type names for compatibility
            self.lock_type = LockType(lock_type_value.lower())
        else:
            self.lock_type = lock_type_value
        self.property_path = config.get("property_path")
        self.expected_value = config.get("expected_value")
        self.metadata = config.get("metadata", {}) or {}


    def validate(self, element: "Element") -> LockResult:
        try:
            value = element.get_property(self.property_path)
            lock_meta= LockMetaData(
                expected_value= self.expected_value,
                min_value= self.metadata.get("min_value"),
                max_value= self.metadata.get("max_value")
        )
            is_valid = self.lock_type.validate(value, lock_meta)
            eror_message = "" if is_valid else self.lock_type.failure_message(
                self.property_path, value, self.expected_value
            )
            return LockResult(
                    success=is_valid,
                    property_path=self.property_path,
                    lock_type=self.lock_type,
                    actual_value=value,
                    expected_value=self.expected_value,
                    error_message=eror_message,
                )
        except Exception as e:
            return LockResult(
                success=False,
                property_path=self.property_path,
                lock_type=self.lock_type,
                actual_value=None,
                expected_value=self.expected_value,
                error_message=f"Error resolving property: {e}",
            )

    def to_dict(self) -> LockDefinitionDict:
        return {
            "property_path": self.property_path,
            "type": self.lock_type,
            "expected_value": self.expected_value,
        }

LockShorhands = {
        "is_true": (LockType.EQUALS, True),
        "is_false": (LockType.EQUALS, False),
        "exists": (LockType.EXISTS, True),
}


class LockFactory:
    """
    Factory for creating Lock instances from various syntax formats.

    Supports simplified shorthand syntax for common lock patterns while
    maintaining backward compatibility with verbose lock definitions.
    """

    SHORTHAND_KEYS = ["exists", "is_true", "is_false"]

    @classmethod
    def create(cls, lock_definition:  LockDefinition) -> Lock:
        if "type" in lock_definition and "property_path" in lock_definition:
            return Lock({
                "type": lock_definition["type"],
                "property_path": lock_definition["property_path"],
                "expected_value": lock_definition.get("expected_value"),
                "metadata": lock_definition.get("metadata", {}),
            })
        else:
            for key in cls.SHORTHAND_KEYS:
                if key in lock_definition and lock_definition[key] is not None:
                    lock_type, expected_value = LockShorhands[key]
                    return Lock({
                        "type": lock_type,
                        "property_path": lock_definition[key],
                        "expected_value": expected_value,
                    })
        raise ValueError("Invalid lock definition format")

