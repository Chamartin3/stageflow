"""
Validator models for process configuration structures.

Each validator serves as the single source of truth for:
1. Field names (as class attributes)
2. Required fields (in __post_init__)
3. Validation logic (in __post_init__)
4. Error collection (via _errors attribute)

These validators use frozen dataclasses for immutability and validate
on initialization via __post_init__.
"""

from dataclasses import dataclass, field
from typing import Any

from stageflow.models import ErrorSeverity, LoadError, LoadErrorType, LockTypeShorthand


@dataclass(frozen=True)
class LockConfigValidator:
    """Validator for lock configuration with automatic validation.

    Handles three lock formats:
    1. Shorthand: {exists: "path"}
    2. Full: {type: "EXISTS", property_path: "path"}
    3. Special: {type: "CONDITIONAL", if: [...], then: [...]}
    """

    data: dict[str, Any]

    # Field names
    TYPE: str = "type"
    PROPERTY_PATH: str = "property_path"
    EXPECTED_VALUE: str = "expected_value"
    ERROR_MESSAGE: str = "error_message"
    IF: str = "if"
    THEN: str = "then"
    ELSE: str = "else"
    CONDITIONS: str = "conditions"
    LOCKS: str = "locks"

    def __post_init__(self):
        """Validate lock configuration on initialization."""
        errors: list[LoadError] = []

        # Detect lock format
        if self.is_shorthand:
            # Shorthand format - validate it has exactly one shorthand key
            shorthand_keys = {
                k for k in self.data.keys() if k in {e.value for e in LockTypeShorthand}
            }
            if len(shorthand_keys) != 1:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_LOCK_DEFINITION,
                        severity=ErrorSeverity.FATAL,
                        message=f"Shorthand lock must have exactly one lock type key, found: {shorthand_keys}",
                        context={"found_keys": list(shorthand_keys)},
                    )
                )
        elif self.is_conditional:
            # Conditional format - validate required fields
            if self.IF not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_LOCK_DEFINITION,
                        severity=ErrorSeverity.FATAL,
                        message="CONDITIONAL lock missing required 'if' field",
                        context={"field": self.IF},
                    )
                )
            if self.THEN not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_LOCK_DEFINITION,
                        severity=ErrorSeverity.FATAL,
                        message="CONDITIONAL lock missing required 'then' field",
                        context={"field": self.THEN},
                    )
                )
        elif self.is_or_logic:
            # OR_LOGIC format - validate conditions field
            if self.CONDITIONS not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_LOCK_DEFINITION,
                        severity=ErrorSeverity.FATAL,
                        message="OR_LOGIC lock missing required 'conditions' field",
                        context={"field": self.CONDITIONS},
                    )
                )
            elif not isinstance(self.data[self.CONDITIONS], list):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_TYPE,
                        severity=ErrorSeverity.FATAL,
                        message="OR_LOGIC 'conditions' must be a list",
                        context={
                            "field": self.CONDITIONS,
                            "expected_type": "list",
                            "actual_type": type(self.data[self.CONDITIONS]).__name__,
                        },
                    )
                )
        else:
            # Full format - validate required fields
            if self.TYPE not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.MISSING_REQUIRED_FIELD,
                        severity=ErrorSeverity.FATAL,
                        message=f"Lock missing required field: '{self.TYPE}'",
                        context={"field": self.TYPE},
                    )
                )
            if self.PROPERTY_PATH not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.MISSING_REQUIRED_FIELD,
                        severity=ErrorSeverity.FATAL,
                        message=f"Lock missing required field: '{self.PROPERTY_PATH}'",
                        context={"field": self.PROPERTY_PATH},
                    )
                )

        if errors:
            object.__setattr__(self, "_errors", errors)

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return not hasattr(self, "_errors")

    @property
    def errors(self) -> list[LoadError]:
        """Get validation errors."""
        return getattr(self, "_errors", [])

    @property
    def is_shorthand(self) -> bool:
        """Check if this is shorthand format."""
        shorthand_keys = {e.value for e in LockTypeShorthand}
        return any(k in shorthand_keys for k in self.data.keys())

    @property
    def is_conditional(self) -> bool:
        """Check if this is conditional lock."""
        return self.data.get(self.TYPE) == "CONDITIONAL"

    @property
    def is_or_logic(self) -> bool:
        """Check if this is OR logic lock."""
        return self.data.get(self.TYPE) == "OR_LOGIC"

    def get(self, field: str, default: Any = None) -> Any:
        """Get field value safely."""
        return self.data.get(field, default)


@dataclass(frozen=True)
class GateConfigValidator:
    """Validator for gate configuration with automatic validation."""

    data: dict[str, Any]

    # Field names
    NAME: str = "name"
    TARGET_STAGE: str = "target_stage"
    LOCKS: str = "locks"
    DESCRIPTION: str = "description"
    PARENT_STAGE: str = "parent_stage"

    # Required fields
    REQUIRED: tuple[str, ...] = (NAME, TARGET_STAGE, LOCKS)

    def __post_init__(self):
        """Validate gate configuration on initialization."""
        errors: list[LoadError] = []

        # Check required fields
        for field_name in self.REQUIRED:
            if field_name not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.MISSING_REQUIRED_FIELD,
                        severity=ErrorSeverity.FATAL,
                        message=f"Gate missing required field: '{field_name}'",
                        context={"field": field_name},
                    )
                )

        # Validate locks field is a list
        if self.LOCKS in self.data and not isinstance(self.data[self.LOCKS], list):
            errors.append(
                LoadError(
                    error_type=LoadErrorType.INVALID_FIELD_TYPE,
                    severity=ErrorSeverity.FATAL,
                    message=f"Gate field '{self.LOCKS}' must be a list",
                    context={
                        "field": self.LOCKS,
                        "expected_type": "list",
                        "actual_type": type(self.data[self.LOCKS]).__name__,
                    },
                )
            )

        # Validate locks list is not empty
        if self.LOCKS in self.data and isinstance(self.data[self.LOCKS], list):
            if len(self.data[self.LOCKS]) == 0:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_GATE_DEFINITION,
                        severity=ErrorSeverity.FATAL,
                        message="Gate must have at least one lock",
                        context={"field": self.LOCKS},
                    )
                )

        if errors:
            object.__setattr__(self, "_errors", errors)

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return not hasattr(self, "_errors")

    @property
    def errors(self) -> list[LoadError]:
        """Get validation errors."""
        return getattr(self, "_errors", [])

    def get(self, field: str, default: Any = None) -> Any:
        """Get field value safely."""
        return self.data.get(field, default)


@dataclass(frozen=True)
class StageConfigValidator:
    """Validator for stage configuration with automatic validation."""

    data: dict[str, Any]
    stage_id: str = field(default="")

    # Field names
    NAME: str = "name"
    DESCRIPTION: str = "description"
    GATES: str = "gates"
    EXPECTED_ACTIONS: str = "expected_actions"
    EXPECTED_PROPERTIES: str = "expected_properties"
    IS_FINAL: str = "is_final"

    # No required fields - all are optional with defaults

    def __post_init__(self):
        """Validate stage configuration on initialization."""
        errors: list[LoadError] = []

        # Validate gates if present
        if self.GATES in self.data:
            gates = self.data[self.GATES]
            if not isinstance(gates, (list, dict)):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_TYPE,
                        severity=ErrorSeverity.FATAL,
                        message=f"Stage '{self.stage_id}' field '{self.GATES}' must be a list or dict",
                        context={
                            "field": self.GATES,
                            "stage_name": self.stage_id,
                            "expected_type": "list or dict",
                            "actual_type": type(gates).__name__,
                        },
                    )
                )

        # Validate expected_actions if present
        if self.EXPECTED_ACTIONS in self.data:
            actions = self.data[self.EXPECTED_ACTIONS]
            if not isinstance(actions, list):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_TYPE,
                        severity=ErrorSeverity.FATAL,
                        message=f"Stage '{self.stage_id}' field '{self.EXPECTED_ACTIONS}' must be a list",
                        context={
                            "field": self.EXPECTED_ACTIONS,
                            "stage_name": self.stage_id,
                            "expected_type": "list",
                            "actual_type": type(actions).__name__,
                        },
                    )
                )

        # Validate expected_properties if present
        if self.EXPECTED_PROPERTIES in self.data:
            props = self.data[self.EXPECTED_PROPERTIES]
            if not isinstance(props, dict):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_TYPE,
                        severity=ErrorSeverity.FATAL,
                        message=f"Stage '{self.stage_id}' field '{self.EXPECTED_PROPERTIES}' must be a dict",
                        context={
                            "field": self.EXPECTED_PROPERTIES,
                            "stage_name": self.stage_id,
                            "expected_type": "dict",
                            "actual_type": type(props).__name__,
                        },
                    )
                )

        if errors:
            object.__setattr__(self, "_errors", errors)

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return not hasattr(self, "_errors")

    @property
    def errors(self) -> list[LoadError]:
        """Get validation errors."""
        return getattr(self, "_errors", [])

    def get(self, field: str, default: Any = None) -> Any:
        """Get field value safely."""
        return self.data.get(field, default)


@dataclass(frozen=True)
class ProcessConfigValidator:
    """Validator for process configuration with automatic validation."""

    data: dict[str, Any]

    # Field names
    NAME: str = "name"
    DESCRIPTION: str = "description"
    INITIAL_STAGE: str = "initial_stage"
    FINAL_STAGE: str = "final_stage"
    STAGE_PROP: str = "stage_prop"
    STAGES: str = "stages"

    # Required fields
    REQUIRED: tuple[str, ...] = (NAME, INITIAL_STAGE, FINAL_STAGE, STAGES)

    def __post_init__(self):
        """Validate process configuration on initialization."""
        errors: list[LoadError] = []

        # Check required fields
        for field_name in self.REQUIRED:
            if field_name not in self.data:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.MISSING_REQUIRED_FIELD,
                        severity=ErrorSeverity.FATAL,
                        message=f"Process missing required field: '{field_name}'",
                        context={"field": field_name},
                    )
                )

        # Validate name is not empty
        if self.NAME in self.data:
            name = self.data[self.NAME]
            if not isinstance(name, str) or not name.strip():
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_VALUE,
                        severity=ErrorSeverity.FATAL,
                        message=f"Process field '{self.NAME}' must be a non-empty string",
                        context={"field": self.NAME, "value": name},
                    )
                )

        # Validate stages is a dict
        if self.STAGES in self.data:
            stages = self.data[self.STAGES]
            if not isinstance(stages, dict):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_TYPE,
                        severity=ErrorSeverity.FATAL,
                        message=f"Process field '{self.STAGES}' must be a dict",
                        context={
                            "field": self.STAGES,
                            "expected_type": "dict",
                            "actual_type": type(stages).__name__,
                        },
                    )
                )
            elif len(stages) == 0:
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FIELD_VALUE,
                        severity=ErrorSeverity.FATAL,
                        message="Process must have at least one stage",
                        context={"field": self.STAGES},
                    )
                )

        # Validate initial_stage and final_stage exist in stages
        if self.STAGES in self.data and isinstance(self.data[self.STAGES], dict):
            stage_names = set(self.data[self.STAGES].keys())

            if self.INITIAL_STAGE in self.data:
                initial = self.data[self.INITIAL_STAGE]
                if initial not in stage_names:
                    errors.append(
                        LoadError(
                            error_type=LoadErrorType.MISSING_STAGE_REFERENCE,
                            severity=ErrorSeverity.WARNING,
                            message=f"Initial stage '{initial}' not found in stages",
                            context={
                                "field": self.INITIAL_STAGE,
                                "value": initial,
                                "available_stages": list(stage_names),
                            },
                        )
                    )

            if self.FINAL_STAGE in self.data:
                final = self.data[self.FINAL_STAGE]
                if final not in stage_names:
                    errors.append(
                        LoadError(
                            error_type=LoadErrorType.MISSING_STAGE_REFERENCE,
                            severity=ErrorSeverity.WARNING,
                            message=f"Final stage '{final}' not found in stages",
                            context={
                                "field": self.FINAL_STAGE,
                                "value": final,
                                "available_stages": list(stage_names),
                            },
                        )
                    )

        if errors:
            object.__setattr__(self, "_errors", errors)

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return not hasattr(self, "_errors")

    @property
    def errors(self) -> list[LoadError]:
        """Get validation errors."""
        return getattr(self, "_errors", [])

    @property
    def has_fatal_errors(self) -> bool:
        """Check if any errors are fatal."""
        return any(e.severity == ErrorSeverity.FATAL for e in self.errors)

    @property
    def has_warnings(self) -> bool:
        """Check if any errors are warnings."""
        return any(e.severity == ErrorSeverity.WARNING for e in self.errors)

    def get(self, field: str, default: Any = None) -> Any:
        """Get field value safely."""
        return self.data.get(field, default)
