"""
Enums and constants for StageFlow process loading.

This module defines all enums and constant classes to avoid magic strings
throughout the codebase.

Usage:
    from stageflow.models.enums import (
        LoadResultStatus,
        LoadErrorType,
        PROCESS_FIELDS,
    )
"""

from enum import StrEnum

# ============================================================================
# Load Result Enums
# ============================================================================


class LoadResultStatus(StrEnum):
    """Status of a process load operation."""

    SUCCESS = "success"
    FILE_ERROR = "file_error"
    PARSE_ERROR = "parse_error"
    STRUCTURE_ERROR = "structure_error"
    VALIDATION_ERROR = "validation_error"
    CONSISTENCY_WARNING = "consistency_warning"


class ErrorSeverity(StrEnum):
    """Severity level of load errors."""

    FATAL = "fatal"  # Cannot create Process object
    WARNING = "warning"  # Process created but has issues
    INFO = "info"  # Informational messages


class LoadErrorType(StrEnum):
    """Categorized error types for better error handling."""

    # File-level errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION_DENIED = "file_permission_denied"
    FILE_ENCODING_ERROR = "file_encoding_error"

    # Parse-level errors
    YAML_PARSE_ERROR = "yaml_parse_error"
    JSON_PARSE_ERROR = "json_parse_error"
    INVALID_FORMAT = "invalid_format"

    # Structure-level errors
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FIELD_TYPE = "invalid_field_type"
    INVALID_FIELD_VALUE = "invalid_field_value"

    # Configuration validation errors
    INVALID_LOCK_DEFINITION = "invalid_lock_definition"
    INVALID_GATE_DEFINITION = "invalid_gate_definition"
    INVALID_STAGE_DEFINITION = "invalid_stage_definition"
    INVALID_EXPECTED_ACTIONS = "invalid_expected_actions"
    INVALID_EXPECTED_PROPERTIES = "invalid_expected_properties"
    VALIDATION_ERROR = "validation_error"  # Generic validation error

    # Consistency warnings
    MISSING_STAGE_REFERENCE = "missing_stage_reference"
    INVALID_TRANSITION = "invalid_transition"
    UNREACHABLE_STAGE = "unreachable_stage"
    ORPHANED_STAGE = "orphaned_stage"
    CIRCULAR_DEPENDENCY = "circular_dependency"


# ============================================================================
# Source and Format Enums
# ============================================================================


class ProcessSourceType(StrEnum):
    """Type of source for process loading."""

    FILE = "file"
    REGISTRY = "registry"


class FileFormat(StrEnum):
    """Supported file formats."""

    YAML = "yaml"
    JSON = "json"


# ============================================================================
# Lock Type Enums
# ============================================================================


class LockTypeShorthand(StrEnum):
    """Shorthand keys for lock definitions."""

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
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class SpecialLockType(StrEnum):
    """Special lock types requiring special handling."""

    CONDITIONAL = "CONDITIONAL"
    OR_LOGIC = "OR_LOGIC"
