"""Lock types and validation logic for StageFlow."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeAlias, TypedDict

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
    CONDITIONAL = "conditional"
    OR_LOGIC = "or_logic"
    OR_GROUP = "or_group"

    def failure_message(
        self, property_path: str, actual_value: Any, expected_value: Any = None
    ) -> str:
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
            expected_type = (
                expected_value
                if isinstance(expected_value, str)
                else getattr(expected_value, "__name__", str(expected_value))
            )
            actual_type = type(actual_value).__name__
            return f"Property '{property_path}' should be of type '{expected_type}' but is '{actual_type}' with value '{actual_value}'"

        if self == LockType.RANGE:
            if isinstance(expected_value, (list | tuple)) and len(expected_value) == 2:
                min_val, max_val = expected_value
                return f"Property '{property_path}' should be between {min_val} and {max_val} but is {actual_value}"

        return (
            f"Property '{property_path}' failed validation for lock type '{self.value}'"
        )

    def validate(self, value: Any, lock_meta: LockMetaData) -> bool:
        lock_type = self
        if lock_type == LockType.EXISTS:
            return value is not None and (
                not isinstance(value, str) or len(value.strip()) > 0
            )

        if lock_type == LockType.NOT_EMPTY:
            if isinstance(value, str):
                return len(value.strip()) > 0
            elif hasattr(value, "__len__"):
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
                elif hasattr(value, "__contains__"):
                    # For collections, check if expected_value is in the collection
                    # or if string representation matches any element
                    # Type ignore needed because value could be various types
                    return (
                        expected_value in value  # type: ignore[operator]
                        or str(expected_value) in [str(item) for item in value]
                    )  # type: ignore[arg-type]
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
                    "str": str,
                    "string": str,
                    "int": int,
                    "integer": int,
                    "float": float,
                    "bool": bool,
                    "boolean": bool,
                    "list": list,
                    "dict": dict,
                    "dictionary": dict,
                    "tuple": tuple,
                    "set": set,
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
    Result of lock validation with support for hierarchical error reporting.

    For simple locks, this contains the validation result for a single property.
    For composite locks (ConditionalLock, OrLogicLock), this can contain nested
    failures showing the hierarchy of validation attempts.

    Attributes:
        success: Whether validation passed
        property_path: Path to the property that was validated
        lock_type: Type of lock that was evaluated
        actual_value: Actual value found (if applicable)
        expected_value: Expected value for comparison (if applicable)
        error_message: Human-readable error message
        nested_failures: List of nested LockResult failures (for composite locks)
        context: Contextual information (e.g., "if condition", "then branch", "Path 1")
        passing_path: Which path passed in OR logic (1-indexed, None if not OR logic)
    """

    success: bool
    property_path: str
    lock_type: LockType
    actual_value: Any = None
    expected_value: Any = None
    error_message: str = ""
    nested_failures: list['LockResult'] = field(default_factory=list)
    context: str = ""
    passing_path: int | None = None

    def format_error_tree(self, indent: int = 0) -> str:
        """
        Format errors as indented tree showing hierarchy.

        For simple locks, returns the error message.
        For composite locks, shows the full tree of nested failures.

        Args:
            indent: Current indentation level (for recursion)

        Returns:
            Formatted error tree as string
        """
        lines = []
        prefix = "  " * indent

        # Add context if present
        if self.context:
            lines.append(f"{prefix}[{self.context}]")

        # Add error message if present
        if self.error_message:
            lines.append(f"{prefix}→ {self.error_message}")

        # Add nested failures recursively
        for nested in self.nested_failures:
            lines.append(nested.format_error_tree(indent + 1))

        return "\n".join(lines)


class LockDefinitionDict(TypedDict, total=False):
    """Lock configuration with optional custom error message."""

    type: LockType
    property_path: str
    expected_value: str | int | LockMetaData
    error_message: str


class LockShorthandDict(TypedDict, total=False):
    exists: str | None
    is_true: str | None
    is_false: str | None
    error_message: str


# ConditionalLockDict uses dict instead of TypedDict because 'if', 'then', 'else'
# are Python keywords and cannot be used as TypedDict field names
# Structure: {"type": LockType.CONDITIONAL, "if": [...], "then": [...], "else": [...]}
ConditionalLockDict: TypeAlias = dict[str, Any]

LockDefinition = LockDefinitionDict | LockShorthandDict | ConditionalLockDict


class BaseLock(ABC):
    """
    Abstract base class for all lock types.

    All locks must implement the validate() method that checks
    an Element against validation rules and returns a LockResult.

    This base class enables composite locks (ConditionalLock, OrLogicLock)
    that can contain other locks, while maintaining compatibility with
    simple property-based locks.

    This class defines abstract methods that all locks must implement.
    SimpleLock and ConditionalLock both implement these in their own ways.

    Attributes:
        property_path: Path to the property being validated
        lock_type: Type of lock validation to perform
    """

    # Type hints for attributes (not enforced as abstract to allow
    # SimpleLock to use instance attributes and ConditionalLock to use properties)
    property_path: str
    lock_type: LockType

    @abstractmethod
    def validate(self, element: Element) -> "LockResult":
        """
        Validate element against this lock's rules.

        Args:
            element: The Element to validate

        Returns:
            LockResult indicating success/failure with error details
        """
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """
        Convert lock to dictionary representation.

        Returns:
            Dictionary representation of the lock configuration
        """
        pass


class SimpleLock(BaseLock):
    """
    Simple property-based lock for validating Element properties.

    SimpleLock validates a single property path against an expected value
    using a specified LockType (EXISTS, EQUALS, GREATER_THAN, etc.).

    This is the traditional lock type in StageFlow. For composite locks
    that contain other locks, see ConditionalLock and OrLogicLock.
    """

    lock_type: LockType
    property_path: str
    expected_value: Any
    validator_name: str | None
    custom_error_message: str | None

    def __init__(self, config: LockDefinitionDict) -> None:
        lock_type_value = config.get("type")
        if isinstance(lock_type_value, str):
            # Handle case-insensitive lock type names for compatibility
            self.lock_type = LockType(lock_type_value.lower())
        else:
            self.lock_type = lock_type_value  # type: ignore[assignment]
        self.property_path = config.get("property_path")  # type: ignore[assignment]
        self.expected_value = config.get("expected_value")
        self.metadata = config.get("metadata", {}) or {}
        self.custom_error_message = config.get("error_message")

    def validate(self, element: "Element") -> LockResult:
        try:
            value = element.get_property(self.property_path)
            lock_meta = LockMetaData(
                expected_value=self.expected_value,
                min_value=self.metadata.get("min_value"),
                max_value=self.metadata.get("max_value"),
            )
            is_valid = self.lock_type.validate(value, lock_meta)

            # Generate error message: use custom if provided, otherwise generate
            if is_valid:
                error_message = ""
            elif self.custom_error_message:
                error_message = self.custom_error_message
            else:
                error_message = self.lock_type.failure_message(
                    self.property_path, value, self.expected_value
                )

            return LockResult(
                success=is_valid,
                property_path=self.property_path,
                lock_type=self.lock_type,
                actual_value=value,
                expected_value=self.expected_value,
                error_message=error_message,
            )
        except Exception as e:
            # Use custom message for exceptions too, if provided
            if self.custom_error_message:
                error_message = self.custom_error_message
            else:
                error_message = f"Error resolving property: {e}"

            return LockResult(
                success=False,
                property_path=self.property_path,
                lock_type=self.lock_type,
                actual_value=None,
                expected_value=self.expected_value,
                error_message=error_message,
            )

    def to_dict(self) -> LockDefinitionDict:
        return {
            "property_path": self.property_path,
            "type": self.lock_type,
            "expected_value": self.expected_value,
        }


@dataclass
class ConditionalLock(BaseLock):
    """
    Lock that evaluates different validation rules based on runtime conditions.

    Implements if-then-else logic for validation:
    - IF condition: All locks in if_locks must pass (AND logic)
    - THEN branch: Evaluated if IF condition passes
    - ELSE branch: Evaluated if IF condition fails (optional)

    If the IF condition fails and no ELSE branch exists, the lock passes
    (the requirement is not applicable).

    Attributes:
        if_locks: Locks to evaluate as condition (AND logic)
        then_locks: Locks to evaluate if condition passes (AND logic)
        else_locks: Locks to evaluate if condition fails (AND logic, optional)
        max_depth: Maximum nesting depth to prevent infinite recursion
    """

    if_locks: list[BaseLock]
    then_locks: list[BaseLock]
    else_locks: list[BaseLock]
    max_depth: int = 5

    def __init__(
        self,
        if_locks: list[BaseLock],
        then_locks: list[BaseLock],
        else_locks: list[BaseLock] | None = None,
        max_depth: int = 5
    ):
        """
        Initialize ConditionalLock.

        Args:
            if_locks: Condition locks (all must pass for THEN to evaluate)
            then_locks: Locks to evaluate if condition passes
            else_locks: Locks to evaluate if condition fails (optional)
            max_depth: Maximum nesting depth (default 5)

        Raises:
            ValueError: If if_locks or then_locks are empty
        """
        if not if_locks:
            raise ValueError("ConditionalLock must have at least one IF lock")
        if not then_locks:
            raise ValueError("ConditionalLock must have at least one THEN lock")

        self.if_locks = if_locks
        self.then_locks = then_locks
        self.else_locks = else_locks or []
        self.max_depth = max_depth

    @property
    def property_path(self) -> str:
        """Return a descriptive property path for conditional locks."""
        return "<conditional>"

    @property
    def lock_type(self) -> LockType:
        """Return the lock type for conditional locks."""
        return LockType.CONDITIONAL

    def validate(self, element: Element, depth: int = 0) -> LockResult:
        """
        Validate element using conditional logic.

        Args:
            element: Element to validate
            depth: Current recursion depth (for nested conditionals)

        Returns:
            LockResult with nested failures if applicable
        """
        # Check recursion depth
        if depth > self.max_depth:
            return LockResult(
                success=False,
                property_path="<conditional>",
                lock_type=LockType.CONDITIONAL,
                error_message=f"Maximum conditional nesting depth ({self.max_depth}) exceeded",
                context="depth_limit"
            )

        # Evaluate IF condition (all locks must pass)
        if_result = self._evaluate_locks(self.if_locks, element, depth, "if condition")

        if if_result.success:
            # Condition passed - evaluate THEN branch
            then_result = self._evaluate_locks(
                self.then_locks,
                element,
                depth,
                "then branch"
            )
            return then_result

        elif self.else_locks:
            # Condition failed - evaluate ELSE branch
            else_result = self._evaluate_locks(
                self.else_locks,
                element,
                depth,
                "else branch"
            )
            return else_result

        else:
            # Condition failed, no ELSE - lock passes (not applicable)
            return LockResult(
                success=True,
                property_path="<conditional>",
                lock_type=LockType.CONDITIONAL,
                error_message="",
                context="condition not applicable"
            )

    def _evaluate_locks(
        self,
        locks: list[BaseLock],
        element: Element,
        depth: int,
        context: str
    ) -> LockResult:
        """
        Evaluate a list of locks with AND logic.

        Args:
            locks: Locks to evaluate
            element: Element to validate
            depth: Current recursion depth
            context: Context string for error reporting

        Returns:
            LockResult with all failures or success
        """
        failed = []

        for lock in locks:
            # Handle recursive validation for nested conditionals
            if isinstance(lock, ConditionalLock):
                result = lock.validate(element, depth + 1)
            else:
                result = lock.validate(element)

            if not result.success:
                failed.append(result)

        if failed:
            return LockResult(
                success=False,
                property_path="<conditional>",
                lock_type=LockType.CONDITIONAL,
                error_message=f"Conditional {context} failed",
                nested_failures=failed,
                context=context
            )
        else:
            return LockResult(
                success=True,
                property_path="<conditional>",
                lock_type=LockType.CONDITIONAL,
                context=context
            )

    def to_dict(self) -> ConditionalLockDict:
        """Convert ConditionalLock to dictionary representation."""
        result: ConditionalLockDict = {
            "type": LockType.CONDITIONAL,
            "if": [lock.to_dict() for lock in self.if_locks],
            "then": [lock.to_dict() for lock in self.then_locks],
        }
        if self.else_locks:
            result["else"] = [lock.to_dict() for lock in self.else_locks]
        return result


@dataclass
class OrLogicLock(BaseLock):
    """
    Lock that passes if ANY condition group passes (OR logic).

    Each condition group contains locks evaluated with AND logic.
    Groups are evaluated sequentially until one passes (short-circuit).

    Example:
        Complete task normally (path 1) OR cancel with reason (path 2)

    Attributes:
        condition_groups: List of lock groups (each group uses AND logic)
        short_circuit: Stop evaluation at first passing group (default True)
    """

    condition_groups: list[list[BaseLock]]
    short_circuit: bool = True

    def __init__(
        self,
        condition_groups: list[list[BaseLock]],
        short_circuit: bool = True
    ):
        """
        Initialize OrLogicLock.

        Args:
            condition_groups: List of lock groups (each group AND logic)
            short_circuit: Stop at first passing group (default True)

        Raises:
            ValueError: If no groups or empty groups provided
        """
        if not condition_groups:
            raise ValueError("OR_LOGIC must have at least one condition group")

        for i, group in enumerate(condition_groups):
            if not group:
                raise ValueError(
                    f"Condition group {i + 1} is empty - "
                    f"each group must have at least one lock"
                )

        self.condition_groups = condition_groups
        self.short_circuit = short_circuit

    @property
    def property_path(self) -> str:
        """Return a descriptive property path for OR logic locks."""
        return "<or_logic>"

    @property
    def lock_type(self) -> LockType:
        """Return the lock type for OR logic locks."""
        return LockType.OR_LOGIC

    def validate(self, element: Element) -> LockResult:
        """
        Evaluate condition groups with OR logic.

        Evaluates groups sequentially. If short_circuit is True,
        stops at first passing group. Otherwise, evaluates all groups.

        Args:
            element: Element to validate

        Returns:
            LockResult with success if any group passed, failure with
            all group results if all failed
        """
        all_group_results = []

        for i, group in enumerate(self.condition_groups):
            group_result = self._evaluate_group(group, element, i + 1)
            all_group_results.append(group_result)

            if group_result.success and self.short_circuit:
                # First passing group found - short-circuit
                return LockResult(
                    success=True,
                    property_path="<or_logic>",
                    lock_type=LockType.OR_LOGIC,
                    context=f"Path {i + 1}",
                    passing_path=i + 1,
                    error_message=""
                )

        # Check if any group passed (non-short-circuit mode)
        passing_groups = [r for r in all_group_results if r.success]
        if passing_groups:
            # At least one group passed
            passing_indices = [
                i + 1 for i, r in enumerate(all_group_results) if r.success
            ]
            return LockResult(
                success=True,
                property_path="<or_logic>",
                lock_type=LockType.OR_LOGIC,
                context=f"Paths {', '.join(map(str, passing_indices))} passed",
                passing_path=passing_indices[0],
                error_message=""
            )

        # All groups failed
        return LockResult(
            success=False,
            property_path="<or_logic>",
            lock_type=LockType.OR_LOGIC,
            error_message="All alternative paths failed validation",
            nested_failures=all_group_results,
            context="or_logic"
        )

    def _evaluate_group(
        self,
        locks: list[BaseLock],
        element: Element,
        group_number: int
    ) -> LockResult:
        """
        Evaluate a single condition group with AND logic.

        Args:
            locks: Locks in this group (all must pass)
            element: Element to validate
            group_number: Group number (1-indexed) for context

        Returns:
            LockResult with success if all locks passed
        """
        failed = []
        passed = []

        for lock in locks:
            result = lock.validate(element)
            if result.success:
                passed.append(result)
            else:
                failed.append(result)

        if failed:
            return LockResult(
                success=False,
                property_path="<or_group>",
                lock_type=LockType.OR_GROUP,
                error_message=f"Path {group_number} failed",
                nested_failures=failed,
                context=f"Path {group_number}"
            )
        else:
            return LockResult(
                success=True,
                property_path="<or_group>",
                lock_type=LockType.OR_GROUP,
                context=f"Path {group_number}",
                error_message=""
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert OrLogicLock to dictionary representation."""
        result: dict[str, Any] = {
            "type": LockType.OR_LOGIC,
            "conditions": [
                {"locks": [lock.to_dict() for lock in group]}
                for group in self.condition_groups
            ]
        }
        if not self.short_circuit:
            result["short_circuit"] = False
        return result


# Backward compatibility: Lock is an alias for SimpleLock  # noqa: F811
# This MUST remain as a simple assignment, not a TypeAlias, for backward compatibility
Lock = SimpleLock


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
    def create(cls, lock_definition: LockDefinition) -> BaseLock:
        """
        Create appropriate lock type from configuration.

        Supports:
        - Simple locks (EXISTS, EQUALS, etc.)
        - Shorthand syntax (exists, is_true, etc.)
        - Conditional locks (if-then-else)
        - OR logic locks (alternative paths)

        Args:
            lock_definition: Lock configuration dictionary

        Returns:
            BaseLock instance (SimpleLock, ConditionalLock, or OrLogicLock)

        Raises:
            ValueError: If configuration is invalid
        """
        lock_type = lock_definition.get("type")

        # Handle CONDITIONAL lock type
        if lock_type == "CONDITIONAL":
            return cls._create_conditional(dict(lock_definition))

        # Handle OR_LOGIC lock type
        if lock_type == "OR_LOGIC":
            return cls._create_or_logic(dict(lock_definition))

        # Prioritize explicit "type" field over shorthand syntax
        # Only use shorthand if no explicit "type" is provided
        if not lock_type:
            # Handle shorthand syntax
            for key in cls.SHORTHAND_KEYS:
                if key in lock_definition and lock_definition[key] is not None:
                    lock_type, expected_value = LockShorhands[key]
                    lock_config = {
                        "type": lock_type,
                        "property_path": lock_definition[key],  # type: ignore[assignment]
                        "expected_value": expected_value,
                    }
                    # Add error_message if present
                    if "error_message" in lock_definition:
                        lock_config["error_message"] = lock_definition["error_message"]  # type: ignore[assignment]
                    return SimpleLock(lock_config)  # type: ignore[arg-type]

        # Handle full type/property_path syntax for SimpleLock
        if "type" in lock_definition and "property_path" in lock_definition:
            # Create base lock config without metadata (not part of TypedDict)
            lock_config: LockDefinitionDict = {
                "type": lock_definition["type"],  # type: ignore[typeddict-item]
                "property_path": lock_definition["property_path"],  # type: ignore[typeddict-item]
                "expected_value": lock_definition.get("expected_value"),  # type: ignore[typeddict-item]
            }
            # Add error_message if present
            if "error_message" in lock_definition:
                lock_config["error_message"] = lock_definition["error_message"]  # type: ignore[typeddict-item]
            # Add metadata if present (needed for RANGE locks and others)
            if "metadata" in lock_definition:
                lock_config["metadata"] = lock_definition["metadata"]  # type: ignore[typeddict-item]
            return SimpleLock(lock_config)

        raise ValueError("Invalid lock definition format")

    @classmethod
    def _create_conditional(cls, lock_definition: dict[str, Any]) -> ConditionalLock:
        """
        Create ConditionalLock from configuration.

        Args:
            lock_definition: Configuration with 'if', 'then', 'else' fields

        Returns:
            ConditionalLock instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if "if" not in lock_definition:
            raise ValueError("ConditionalLock requires 'if' field")
        if "then" not in lock_definition:
            raise ValueError("ConditionalLock requires 'then' field")

        # Recursively create IF locks
        if_locks = []
        for lock_config in lock_definition["if"]:
            if_locks.append(cls.create(lock_config))

        # Recursively create THEN locks
        then_locks = []
        for lock_config in lock_definition["then"]:
            then_locks.append(cls.create(lock_config))

        # Recursively create ELSE locks (optional)
        else_locks = []
        if "else" in lock_definition:
            for lock_config in lock_definition["else"]:
                else_locks.append(cls.create(lock_config))

        return ConditionalLock(
            if_locks=if_locks,
            then_locks=then_locks,
            else_locks=else_locks if else_locks else None
        )

    @classmethod
    def _create_or_logic(cls, lock_definition: dict[str, Any]) -> OrLogicLock:
        """
        Create OrLogicLock from configuration.

        Args:
            lock_definition: Configuration with 'conditions' field

        Returns:
            OrLogicLock instance

        Raises:
            ValueError: If 'conditions' field is missing or invalid
        """
        if "conditions" not in lock_definition:
            raise ValueError("OR_LOGIC requires 'conditions' field")

        conditions = lock_definition["conditions"]
        if not isinstance(conditions, list):
            raise ValueError("'conditions' must be a list of condition groups")

        condition_groups = []
        for i, group_def in enumerate(conditions):
            if "locks" not in group_def:
                raise ValueError(
                    f"Condition group {i + 1} missing 'locks' field"
                )

            # Recursively create locks for this group
            group_locks = []
            for lock_config in group_def["locks"]:
                group_locks.append(cls.create(lock_config))

            condition_groups.append(group_locks)

        # Get optional short_circuit parameter
        short_circuit = lock_definition.get("short_circuit", True)

        return OrLogicLock(
            condition_groups=condition_groups,
            short_circuit=short_circuit
        )
