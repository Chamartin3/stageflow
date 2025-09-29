"""Common utilities and shared components for StageFlow.

This package contains shared types, exceptions, and interfaces used
throughout the StageFlow framework.
"""

from .exceptions import (
    ConfigurationError,
    ElementError,
    EvaluationError,
    GateError,
    LoaderError,
    LockError,
    ProcessDefinitionError,
    PropertyResolutionError,
    RegistryError,
    SchemaError,
    StageFlowError,
    ValidationError,
)
from .interfaces import (
    ComponentFactory,
    ElementInterface,
    ExtensionInterface,
    GateInterface,
    GateResultInterface,
    LoaderInterface,
    LockInterface,
    LockResultInterface,
    ProcessInterface,
    RegistryInterface,
    ResultInterface,
    StageInterface,
    StageResultInterface,
    ValidatorInterface,
)
from .types import (
    ActionType,
    Configurable,
    ElementMetadata,
    Evaluatable,
    EvaluationContext,
    GateBuilderFunction,
    Priority,
    ProcessMetadata,
    PropertyAccessible,
    ValidationMetadata,
    ValidationState,
    ValidatorFunction,
)

__all__ = [
    # Types
    "ValidationState",
    "ActionType",
    "Priority",
    "PropertyAccessible",
    "Evaluatable",
    "Configurable",
    "ProcessMetadata",
    "ElementMetadata",
    "ValidationMetadata",
    "EvaluationContext",
    "ValidatorFunction",
    "GateBuilderFunction",

    # Exceptions
    "StageFlowError",
    "ValidationError",
    "ConfigurationError",
    "ProcessDefinitionError",
    "ElementError",
    "PropertyResolutionError",
    "RegistryError",
    "GateError",
    "LockError",
    "EvaluationError",
    "SchemaError",
    "LoaderError",

    # Interfaces
    "ElementInterface",
    "ValidatorInterface",
    "LockInterface",
    "GateInterface",
    "StageInterface",
    "ProcessInterface",
    "RegistryInterface",
    "LoaderInterface",
    "ExtensionInterface",
    "ResultInterface",
    "LockResultInterface",
    "GateResultInterface",
    "StageResultInterface",
    "ComponentFactory",
]
