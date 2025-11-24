"""
Base model definitions for StageFlow.

This module is the single source of truth for all TypedDict definitions used
throughout the StageFlow framework. All data structures are defined here and
imported by other modules.
"""

import re
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, NotRequired, Required, TypedDict

if TYPE_CHECKING:
    from ..stage import StageEvaluationResult

__all__ = [
    # Lock types
    "LockType",
    "LockMetaData",
    "LockDefinitionDict",
    "LockShorthandDict",
    "ConditionalLockDict",
    "LockDefinition",
    # Gate types
    "GateDefinition",
    # Stage types
    "ActionDefinition",
    "StageObjectPropertyDefinition",
    "ExpectedObjectSchmema",
    "StageDefinition",
    # Process types
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "RegressionDetails",
    # File format types
    "ProcessFileDict",
    "LegacyProcessFileDict",
    "ProcessFile",
]


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

    def validate(self, value: Any, lock_meta: "LockMetaData") -> bool:
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


# ============================================================================
# Lock Type Definitions
# ============================================================================


class LockMetaData(TypedDict, total=False):
    """Metadata for lock validation."""

    expected_value: Any
    min_value: int | None
    max_value: int | None


class LockDefinitionDict(TypedDict, total=False):
    """Lock configuration with optional custom error message."""

    type: LockType
    property_path: str
    expected_value: str | int | LockMetaData
    metadata: LockMetaData
    error_message: str


class LockShorthandDict(TypedDict, total=False):
    """Shorthand lock format (e.g., {exists: "path"})."""

    exists: str | None
    is_true: str | None
    is_false: str | None
    error_message: str


# ConditionalLockDict cannot use TypedDict because 'if', 'then', 'else' are Python keywords
# Instead, we use a dict with Literal keys for type safety
# The structure is: {"type": "CONDITIONAL", "if": [...], "then": [...], "else": [...]}
ConditionalLockDict = dict[Literal["type", "if", "then", "else", "error_message"], Any]


LockDefinition = LockDefinitionDict | LockShorthandDict | ConditionalLockDict
# ============================================================================
# Gate Type Definitions
# ============================================================================


class GateDefinition(TypedDict):
    """Gate configuration definition."""

    name: str
    description: str
    target_stage: str
    parent_stage: str | None
    locks: list[LockDefinition]


# ============================================================================
# Stage Type Definitions
# ============================================================================


class ActionDefinition(TypedDict):
    """TypedDict for action definition with enhanced structure.

    Fields:
        description: Brief summary of what the action accomplishes (required)
        name: Optional unique identifier for the action within the stage
        instructions: Optional list of guidelines for completing the action
        related_properties: Optional list of property paths involved in this action
    """

    description: str  # Required: Brief summary
    name: NotRequired[str]  # Optional: Action identifier
    instructions: NotRequired[list[str]]  # Optional: List of guidelines
    related_properties: NotRequired[list[str]]  # Optional: Related property paths


class StageObjectPropertyDefinition(TypedDict):
    """Property definition in expected_properties."""

    type: str | None
    default: Any | None


# Type alias for stage expected properties schema
ExpectedObjectSchmema = dict[str, StageObjectPropertyDefinition | None] | None


class StageDefinition(TypedDict, total=False):
    """TypedDict for stage definition."""

    name: Required[str]  # Required
    description: Required[str]  # Required
    gates: Required[list[GateDefinition]]  # Required
    expected_actions: Required[list[ActionDefinition]]  # Required
    expected_properties: Required[ExpectedObjectSchmema]  # Required
    is_final: Required[bool]  # Required


# ============================================================================
# Process Type Definitions
# ============================================================================


class ProcessDefinition(TypedDict):
    """TypedDict for process definition.

    Defines the structure of a process configuration loaded from YAML/JSON.

    Fields:
        name: Process identifier
        description: Human-readable process description
        initial_stage: ID of the starting stage
        final_stage: ID of the terminal stage
        stage_prop: (Optional) Property path for auto-extracting stage from element
        regression_policy: (Optional) How to handle regression detection.
            One of: "ignore", "warn" (default), "block"
        stages: Map of stage_id → StageDefinition

    Examples:
        >>> # Minimal process
        >>> process: ProcessDefinition = {
        ...     "name": "simple_flow",
        ...     "description": "A simple process",
        ...     "initial_stage": "start",
        ...     "final_stage": "end",
        ...     "stages": {...}
        ... }

        >>> # With regression policy
        >>> process: ProcessDefinition = {
        ...     "name": "strict_flow",
        ...     "description": "Process with strict regression blocking",
        ...     "initial_stage": "start",
        ...     "final_stage": "end",
        ...     "regression_policy": "block",  # Block transitions on regression
        ...     "stages": {...}
        ... }
    """

    name: str
    description: str
    initial_stage: str
    final_stage: str
    stage_prop: NotRequired[str]
    regression_policy: NotRequired[str]  # NEW: RegressionPolicy enum value, default="warn"
    stages: dict[str, StageDefinition]


class RegressionDetails(TypedDict):
    """Detailed information about regression detection.

    Provides comprehensive data about which previous stages failed
    re-evaluation and why, enabling targeted data repair.

    This replaces the simple boolean 'regression' field with structured
    information that helps users understand and fix data quality issues.

    Fields:
        detected: Whether regression was detected (any previous stage failed)
        policy: Policy used for this evaluation (from RegressionPolicy enum)
        failed_stages: List of stage IDs that failed re-evaluation
        failed_statuses: Map of stage_id → status (incomplete/blocked)
        missing_properties: (Optional) Map of stage_id → list of missing property paths
        failed_gates: (Optional) Map of stage_id → list of failed gate names

    Examples:
        >>> # No regression detected
        >>> details = RegressionDetails(
        ...     detected=False,
        ...     policy="warn",
        ...     failed_stages=[],
        ...     failed_statuses={}
        ... )

        >>> # Regression detected with details
        >>> details = RegressionDetails(
        ...     detected=True,
        ...     policy="block",
        ...     failed_stages=["registration", "verification"],
        ...     failed_statuses={
        ...         "registration": "incomplete",
        ...         "verification": "blocked"
        ...     },
        ...     missing_properties={
        ...         "registration": ["email", "password"]
        ...     },
        ...     failed_gates={
        ...         "verification": ["email_verified"]
        ...     }
        ... )
    """
    detected: bool                      # Whether regression was detected
    policy: str                         # Policy used (from RegressionPolicy enum)
    failed_stages: list[str]           # Stage IDs that failed re-evaluation
    failed_statuses: dict[str, str]    # stage_id → status (incomplete/blocked)
    missing_properties: NotRequired[dict[str, list[str]]]  # stage_id → [property paths]
    failed_gates: NotRequired[dict[str, list[str]]]        # stage_id → [gate names]


class ProcessElementEvaluationResult(TypedDict):
    """Result of process-level element evaluation.

    Includes both stage-level validation (current stage) and
    process-level quality checks (regression detection).

    Fields:
        stage: Current stage ID
        stage_result: Detailed stage evaluation result
        regression_details: Enhanced regression information with details
    """
    stage: str
    stage_result: "StageEvaluationResult"
    regression_details: RegressionDetails


# ============================================================================
# File Format Type Definitions
# ============================================================================


class ProcessFileDict(TypedDict):
    """New format: {'process': {...}}"""

    process: ProcessDefinition
    # Optional schema reference for validation
    schema: NotRequired[str]


class LegacyProcessFileDict(ProcessDefinition):
    """Legacy format at root level."""

    pass


# Union type for both file formats
ProcessFile = ProcessFileDict | LegacyProcessFileDict
