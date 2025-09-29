"""Common exceptions for StageFlow framework.

This module defines all exception types used throughout the StageFlow
framework to provide consistent error handling and clear error semantics.
"""

from typing import Any


class StageFlowError(Exception):
    """Base exception for all StageFlow-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        """Initialize exception with message and optional context."""
        super().__init__(message)
        self.context = context or {}


class ValidationError(StageFlowError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        property_path: str | None = None,
        expected_value: Any | None = None,
        actual_value: Any | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize validation error with details."""
        super().__init__(message, context)
        self.property_path = property_path
        self.expected_value = expected_value
        self.actual_value = actual_value


class ConfigurationError(StageFlowError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_section: str | None = None,
        config_key: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize configuration error with details."""
        super().__init__(message, context)
        self.config_section = config_section
        self.config_key = config_key


class ProcessDefinitionError(StageFlowError):
    """Raised when process definition is invalid."""

    def __init__(
        self,
        message: str,
        process_name: str | None = None,
        stage_name: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize process definition error with details."""
        super().__init__(message, context)
        self.process_name = process_name
        self.stage_name = stage_name


class ElementError(StageFlowError):
    """Raised when element operations fail."""

    def __init__(
        self,
        message: str,
        element_id: str | None = None,
        property_path: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize element error with details."""
        super().__init__(message, context)
        self.element_id = element_id
        self.property_path = property_path


class PropertyResolutionError(ElementError):
    """Raised when property resolution fails."""

    def __init__(
        self,
        message: str,
        property_path: str,
        element_id: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize property resolution error."""
        super().__init__(message, element_id, property_path, context)


class RegistryError(StageFlowError):
    """Raised when registry operations fail."""

    def __init__(
        self,
        message: str,
        registry_type: str | None = None,
        item_name: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize registry error with details."""
        super().__init__(message, context)
        self.registry_type = registry_type
        self.item_name = item_name


class GateError(StageFlowError):
    """Raised when gate operations fail."""

    def __init__(
        self,
        message: str,
        gate_name: str | None = None,
        lock_name: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize gate error with details."""
        super().__init__(message, context)
        self.gate_name = gate_name
        self.lock_name = lock_name


class LockError(GateError):
    """Raised when lock operations fail."""

    def __init__(
        self,
        message: str,
        lock_name: str,
        property_path: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize lock error with details."""
        super().__init__(message, None, lock_name, context)
        self.property_path = property_path


class EvaluationError(StageFlowError):
    """Raised when evaluation process fails."""

    def __init__(
        self,
        message: str,
        element_id: str | None = None,
        stage_name: str | None = None,
        evaluation_state: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize evaluation error with details."""
        super().__init__(message, context)
        self.element_id = element_id
        self.stage_name = stage_name
        self.evaluation_state = evaluation_state


class SchemaError(StageFlowError):
    """Raised when schema operations fail."""

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        field_name: str | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize schema error with details."""
        super().__init__(message, context)
        self.schema_name = schema_name
        self.field_name = field_name


class LoaderError(StageFlowError):
    """Raised when loading operations fail."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        loader_type: str | None = None,
        line_number: int | None = None,
        context: dict[str, Any] | None = None
    ):
        """Initialize loader error with details."""
        super().__init__(message, context)
        self.file_path = file_path
        self.loader_type = loader_type
        self.line_number = line_number


# Exception hierarchy for type checking
__all__ = [
    'StageFlowError',
    'ValidationError',
    'ConfigurationError',
    'ProcessDefinitionError',
    'ElementError',
    'PropertyResolutionError',
    'RegistryError',
    'GateError',
    'LockError',
    'EvaluationError',
    'SchemaError',
    'LoaderError'
]
