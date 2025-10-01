"""Status result and evaluation state definitions for StageFlow."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..common.types import ActionType, Priority, ValidationState


class Severity(Enum):
    """Severity levels for diagnostic information."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ActionType is now imported from common.types


@dataclass(frozen=True)
class Action:
    """Represents a recommended action with metadata."""
    type: ActionType
    description: str
    priority: Priority = Priority.NORMAL
    conditions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert Action to dictionary for serialization."""
        return {
            "type": self.type.value,
            "description": self.description,
            "priority": self.priority.value,
            "conditions": self.conditions,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class DiagnosticInfo:
    """Diagnostic information for troubleshooting and analysis."""
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.INFO
    timestamp: datetime | None = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert DiagnosticInfo to dictionary for serialization."""
        return {
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass(frozen=True)
class ErrorInfo:
    """Structured error information with categorization."""
    code: str
    message: str
    category: str = "general"
    details: dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.ERROR
    timestamp: datetime | None = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert ErrorInfo to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category,
            "details": self.details,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass(frozen=True)
class WarningInfo:
    """Structured warning information."""
    code: str
    message: str
    category: str = "general"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert WarningInfo to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# EvaluationState is now imported from common.types as ValidationState
EvaluationState = ValidationState


@dataclass(frozen=True)
class StatusResult:
    """
    Immutable result of element evaluation against a process.

    Contains the complete state of evaluation including current position,
    proposed next steps, actions needed, and comprehensive diagnostic information.

    Can be created using the simplified constructor or the create() class method.
    """

    # Core identification and state
    state: EvaluationState
    element_id: str = ""
    current_stage: str | None = None
    previous_stage: str | None = None
    proposed_stage: str | None = None

    # Actions and recommendations
    actions: list[Any] = field(default_factory=list)

    # Diagnostic and error information
    diagnostics: list[DiagnosticInfo] = field(default_factory=list)
    errors: list[ErrorInfo | str] = field(default_factory=list)
    warnings: list[WarningInfo | str] = field(default_factory=list)

    # Schema validation information
    schema_validation_result: Any | None = None  # ValidationResult from schema validation

    # Metadata and context
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None

    # Performance metrics
    processing_time_ms: float | None = None
    performance_metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate result consistency and set defaults after initialization."""
        # Set timestamp if not provided
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

        # Validate state consistency
        if self.state == EvaluationState.COMPLETED and self.current_stage is not None:
            # For completed state, current_stage should typically be None
            pass

        if self.state == EvaluationState.SCOPING and not self.current_stage:
            # Scoping may not have a current stage yet
            pass

        # Set a default element_id if empty
        if not self.element_id:
            object.__setattr__(self, 'element_id', f"element_{id(self)}")

    def add_action(self, action: Action | str) -> "StatusResult":
        """Add an action to the result (returns new immutable instance)."""
        new_actions = list(self.actions) + [action]
        return self._replace(actions=new_actions)

    def add_diagnostic(self, diagnostic: DiagnosticInfo) -> "StatusResult":
        """Add a diagnostic to the result (returns new immutable instance)."""
        new_diagnostics = list(self.diagnostics) + [diagnostic]
        return self._replace(diagnostics=new_diagnostics)

    def add_error(self, error: ErrorInfo | str) -> "StatusResult":
        """Add an error to the result (returns new immutable instance)."""
        new_errors = list(self.errors) + [error]
        return self._replace(errors=new_errors)

    def add_warning(self, warning: WarningInfo | str) -> "StatusResult":
        """Add a warning to the result (returns new immutable instance)."""
        new_warnings = list(self.warnings) + [warning]
        return self._replace(warnings=new_warnings)

    def _replace(self, **changes) -> "StatusResult":
        """Create a new StatusResult with specified changes."""
        current_dict = {
            'element_id': self.element_id,
            'state': self.state,
            'current_stage': self.current_stage,
            'previous_stage': self.previous_stage,
            'proposed_stage': self.proposed_stage,
            'actions': self.actions,
            'diagnostics': self.diagnostics,
            'errors': self.errors,
            'warnings': self.warnings,
            'schema_validation_result': self.schema_validation_result,
            'metadata': self.metadata,
            'timestamp': self.timestamp,
            'processing_time_ms': self.processing_time_ms,
            'performance_metrics': self.performance_metrics
        }
        current_dict.update(changes)
        return StatusResult(**current_dict)

    @classmethod
    def create(
        cls,
        state: EvaluationState,
        element_id: str = "",
        current_stage: str | None = None,
        proposed_stage: str | None = None,
        actions: list[Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        schema_validation_result: Any | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs
    ) -> "StatusResult":
        """
        Simplified factory method for creating StatusResult instances.

        This method provides a clean interface for creating StatusResult instances
        with intelligent defaults based on the state.

        Args:
            state: The evaluation state
            element_id: Element identifier (auto-generated if empty)
            current_stage: Current stage name
            proposed_stage: Proposed next stage (defaults to current_stage for most states)
            actions: List of actions (auto-populated for some states)
            errors: List of errors
            warnings: List of warnings
            diagnostics: List of diagnostic information
            metadata: Additional metadata
            **kwargs: Additional parameters passed to constructor

        Returns:
            StatusResult instance with appropriate defaults
        """
        # Apply intelligent defaults based on state
        if proposed_stage is None and current_stage is not None:
            if state in (EvaluationState.FULFILLING, EvaluationState.QUALIFYING, EvaluationState.AWAITING):
                proposed_stage = current_stage

        # Set default actions to empty list if none provided
        # Actions should now be provided by stage-based action definitions
        if actions is None:
            actions = []

        # For completed state, clear current_stage if not explicitly set
        if state == EvaluationState.COMPLETED and current_stage is None:
            current_stage = None
            if proposed_stage is None:
                proposed_stage = None

        return cls(
            state=state,
            element_id=element_id,
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            actions=actions or [],
            errors=errors or [],
            warnings=warnings or [],
            diagnostics=diagnostics or [],
            schema_validation_result=schema_validation_result,
            metadata=metadata or {},
            **kwargs
        )

    @classmethod
    def scoping(
        cls,
        element_id: str = "",
        actions: list[Action | str] | None = None,
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create a SCOPING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.SCOPING,
            element_id=element_id,
            current_stage=None,
            proposed_stage=None,
            actions=actions,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def fulfilling(
        cls,
        current_stage: str,
        actions: list[Action | str],
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create a FULFILLING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.FULFILLING,
            element_id=element_id,
            current_stage=current_stage,
            actions=actions,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def qualifying(
        cls,
        current_stage: str,
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create a QUALIFYING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.QUALIFYING,
            element_id=element_id,
            current_stage=current_stage,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def awaiting(
        cls,
        current_stage: str,
        actions: list[Action | str],
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create an AWAITING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.AWAITING,
            element_id=element_id,
            current_stage=current_stage,
            actions=actions,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def advancing(
        cls,
        current_stage: str,
        proposed_stage: str,
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create an ADVANCING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.ADVANCING,
            element_id=element_id,
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def regressing(
        cls,
        current_stage: str,
        proposed_stage: str,
        actions: list[Action | str],
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create a REGRESSING result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.REGRESSING,
            element_id=element_id,
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            actions=actions,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    @classmethod
    def completed(
        cls,
        element_id: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[ErrorInfo | str] | None = None,
        warnings: list[WarningInfo | str] | None = None,
        diagnostics: list[DiagnosticInfo] | None = None,
        **kwargs
    ) -> "StatusResult":
        """Create a COMPLETED result. Backward compatibility method - use create() for new code."""
        return cls.create(
            state=EvaluationState.COMPLETED,
            element_id=element_id,
            current_stage=None,
            proposed_stage=None,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            diagnostics=diagnostics,
            **kwargs
        )

    def has_errors(self) -> bool:
        """Check if result contains any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if result contains any warnings."""
        return len(self.warnings) > 0

    def is_successful(self) -> bool:
        """Check if the evaluation was successful (no errors)."""
        return not self.has_errors()

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (completed or error)."""
        return self.state == EvaluationState.COMPLETED or self.has_errors()

    def has_schema_validation_errors(self) -> bool:
        """Check if schema validation failed."""
        if self.schema_validation_result is None:
            return False
        return not getattr(self.schema_validation_result, 'is_valid', True)

    def get_schema_validation_errors(self) -> list[str]:
        """Get list of schema validation error messages."""
        if self.schema_validation_result is None:
            return []
        if hasattr(self.schema_validation_result, 'errors'):
            return [str(error) for error in self.schema_validation_result.errors]
        return []

    def get_missing_schema_fields(self) -> list[str]:
        """Get list of missing required fields from schema validation."""
        if self.schema_validation_result is None:
            return []
        return getattr(self.schema_validation_result, 'missing_fields', [])

    def get_invalid_schema_fields(self) -> list[str]:
        """Get list of invalid fields from schema validation."""
        if self.schema_validation_result is None:
            return []
        return getattr(self.schema_validation_result, 'invalid_fields', [])

    def to_dict(self) -> dict[str, Any]:
        """Convert StatusResult to dictionary for serialization."""
        def serialize_item(item):
            if hasattr(item, 'to_dict'):
                return item.to_dict()
            return str(item)

        def serialize_validation_result(result):
            """Serialize schema validation result."""
            if result is None:
                return None
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return str(result)

        return {
            "element_id": self.element_id,
            "state": self.state.value,
            "current_stage": self.current_stage,
            "previous_stage": self.previous_stage,
            "proposed_stage": self.proposed_stage,
            "actions": [serialize_item(action) for action in self.actions],
            "diagnostics": [diag.to_dict() for diag in self.diagnostics],
            "errors": [serialize_item(error) for error in self.errors],
            "warnings": [serialize_item(warning) for warning in self.warnings],
            "schema_validation_result": serialize_validation_result(self.schema_validation_result),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "processing_time_ms": self.processing_time_ms,
            "performance_metrics": self.performance_metrics
        }

    def to_json(self) -> str:
        """Convert StatusResult to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def summary(self) -> str:
        """Generate a human-readable summary of the result."""
        if self.has_errors():
            error_msgs = []
            for error in self.errors:
                if isinstance(error, ErrorInfo):
                    error_msgs.append(f"{error.code}: {error.message}")
                else:
                    error_msgs.append(str(error))
            return f"Error in {self.state.value}: {'; '.join(error_msgs)}"

        stage_info = f" (stage: {self.current_stage})" if self.current_stage else ""

        action_msgs = []
        for action in self.actions:
            if isinstance(action, Action):
                action_msgs.append(action.description)
            else:
                action_msgs.append(str(action))

        action_info = f" - {'; '.join(action_msgs)}" if action_msgs else ""

        return f"{self.state.value.title()}{stage_info}{action_info}"
