"""Common types and type definitions for StageFlow.

This module contains shared type definitions used throughout the StageFlow
framework to maintain consistency and type safety.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any, Protocol, TypeVar, Union

# Generic type variables
T = TypeVar('T')
ElementData = dict[str, Any]
PropertyPath = str
ValidationResult = bool


class ValidationState(Enum):
    """States in the validation workflow."""
    SCOPING = "scoping"
    FULFILLING = "fulfilling"
    QUALIFYING = "qualifying"
    AWAITING = "awaiting"
    ADVANCING = "advancing"
    REGRESSING = "regressing"
    COMPLETED = "completed"


class ActionType(Enum):
    """Types of actions that can be generated during evaluation."""
    COMPLETE_FIELD = "complete_field"
    VALIDATE_DATA = "validate_data"
    WAIT_FOR_CONDITION = "wait_for_condition"
    TRANSITION_STAGE = "transition_stage"
    MANUAL_REVIEW = "manual_review"


class Priority(Enum):
    """Priority levels for actions and notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# Protocol definitions for duck typing
class PropertyAccessible(Protocol):
    """Protocol for objects that support property access."""

    def get_property(self, path: str) -> Any:
        """Get property value by path."""
        ...

    def has_property(self, path: str) -> bool:
        """Check if property exists."""
        ...


class Evaluatable(Protocol):
    """Protocol for objects that can be evaluated."""

    def evaluate(self, element: "PropertyAccessible") -> Any:
        """Evaluate element and return result."""
        ...


class Configurable(Protocol):
    """Protocol for objects that can be created from configuration."""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Configurable":
        """Create instance from configuration."""
        ...


# Common data structures
ProcessMetadata = dict[str, Any]
ElementMetadata = dict[str, Any]
ValidationMetadata = dict[str, Any]
EvaluationContext = dict[str, Any]

# Registry types
ValidatorFunction = Union[
    Callable[[Any, Any], bool],
    Callable[[Any, Any, dict[str, Any] | None], bool]
]
GateBuilderFunction = Callable[..., Any]  # Returns a Gate-like object
