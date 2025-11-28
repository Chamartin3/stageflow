"""
Error models and result structures for StageFlow process loading.

This module defines the error handling and result reporting structures used
throughout the process loading pipeline.

Note: This module must NOT import from any stageflow modules except .enums
to maintain a clean vertical hierarchy and avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Any, TypedDict

from .enums import ErrorSeverity, LoadErrorType, LoadResultStatus


class ErrorContextDict(TypedDict, total=False):
    """Context information for load errors."""

    field: str  # Field name causing the error
    value: Any  # Value that caused the error
    expected_type: str  # Expected type for the field
    actual_type: str  # Actual type received
    line: int  # Line number in source file
    column: int  # Column number in source file
    path: str  # Path to the problematic field
    stage_name: str  # Stage name if error is stage-specific
    gate_name: str  # Gate name if error is gate-specific
    lock_index: int  # Lock index if error is lock-specific
    details: str  # Additional context details


def _default_error_context() -> ErrorContextDict:
    """Factory function for default ErrorContextDict."""
    return {}  # type: ignore[return-value]


@dataclass(frozen=True)
class LoadError:
    """Structured error information from process loading.

    Attributes:
        error_type: Categorized error type
        severity: Error severity level
        message: Human-readable error description
        context: Additional context information (flexible dictionary)
    """

    error_type: LoadErrorType
    severity: ErrorSeverity
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": dict(self.context),
        }


class ProcessLoadResultDict(TypedDict):
    """JSON-serializable dictionary format for ProcessLoadResult."""

    status: str  # LoadResultStatus value
    process: dict[str, Any] | None  # Process.to_dict() or None
    errors: list[dict[str, Any]]  # List of LoadError.to_dict()
    warnings: list[dict[str, Any]]  # List of LoadError.to_dict()
    source: str  # Source file path or registry identifier


@dataclass(frozen=True)
class ProcessLoadResult:
    """Unified result object for process loading operations.

    This class provides a consistent structure for all process load outcomes,
    whether successful, failed, or partially successful with warnings.

    Attributes:
        status: Overall load operation status
        process: Loaded Process instance (None if loading failed)
        errors: List of errors encountered (fatal errors prevent process creation)
        warnings: List of warnings (process created but has issues)
        source: Source identifier (file path or registry name)
    """

    status: LoadResultStatus
    process: Any | None  # Process type, but using Any to avoid circular import
    errors: list[LoadError] = field(default_factory=list)
    warnings: list[LoadError] = field(default_factory=list)
    source: str = ""

    @property
    def success(self) -> bool:
        """Check if load was successful (process created)."""
        return self.status in (LoadResultStatus.SUCCESS, LoadResultStatus.CONSISTENCY_WARNING)

    @property
    def is_valid(self) -> bool:
        """Check if process was loaded AND has no blocking consistency issues.

        This is the primary check for whether a process can be used.
        - success: process was created (no load errors)
        - is_valid: process was created AND has no blocking issues
        """
        return self.success and self.process is not None and self.process.is_valid

    @property
    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were encountered."""
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        """Total number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Total number of warnings."""
        return len(self.warnings)

    def to_dict(self) -> ProcessLoadResultDict:
        """Convert result to JSON-serializable dictionary."""
        return ProcessLoadResultDict(
            status=self.status.value,
            process=self.process.to_dict() if self.process else None,
            errors=[error.to_dict() for error in self.errors],
            warnings=[warning.to_dict() for warning in self.warnings],
            source=self.source,
        )

    def get_error_summary(self) -> str:
        """Get a human-readable summary of errors and warnings."""
        lines = []

        if self.success:
            lines.append(f"✓ Process loaded successfully from: {self.source}")
            if self.has_warnings:
                lines.append(f"  ⚠ {self.warning_count} warning(s)")
        else:
            lines.append(f"✗ Failed to load process from: {self.source}")
            lines.append(f"  Status: {self.status.value}")
            lines.append(f"  Errors: {self.error_count}")

        # Add error details
        if self.has_errors:
            lines.append("\nErrors:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. [{error.error_type.value}] {error.message}")
                if error.context:
                    for key, value in error.context.items():
                        lines.append(f"     {key}: {value}")

        # Add warning details
        if self.has_warnings:
            lines.append("\nWarnings:")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. [{warning.error_type.value}] {warning.message}")
                if warning.context:
                    for key, value in warning.context.items():
                        lines.append(f"     {key}: {value}")

        return "\n".join(lines)
