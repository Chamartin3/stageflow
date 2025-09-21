"""Configuration interfaces for gates and locks using TypedDict.

This module defines the data contract interfaces for gate and lock configuration
using TypedDict for type safety and validation. These interfaces provide a
clear specification of what configuration data is expected and its types.
"""

from typing import Any, NotRequired, TypedDict, Union
from typing_extensions import TypedDict as TypedDictExt


class LockConfig(TypedDict):
    """Configuration interface for lock creation.

    Defines the required and optional fields for configuring a lock
    with proper type annotations and documentation.
    """

    # Core lock identification
    property_path: str  # Path to the property being validated
    lock_type: str  # String representation of LockType enum

    # Validation parameters
    expected_value: NotRequired[Any]  # Value to validate against (type depends on lock_type)
    validator_name: NotRequired[str]  # Name of custom validator (for CUSTOM lock_type)

    # Optional metadata
    metadata: NotRequired[dict[str, Any]]  # Additional lock metadata
    description: NotRequired[str]  # Human-readable description

    # Advanced configuration
    error_message: NotRequired[str]  # Custom error message template
    action_message: NotRequired[str]  # Custom action suggestion
    allow_missing: NotRequired[bool]  # Whether missing properties are allowed
    case_sensitive: NotRequired[bool]  # Case sensitivity for string comparisons


class GateConfig(TypedDict):
    """Configuration interface for gate creation.

    Defines the required and optional fields for configuring a gate
    with its logical operation and component locks/gates.
    """

    # Core gate identification
    name: str  # Unique name for the gate
    operation: str  # Logical operation ("and", "or", "not")

    # Gate components - can be lock configs or nested gate configs
    components: list[Union["GateConfig", LockConfig]]

    # Optional configuration
    metadata: NotRequired[dict[str, Any]]  # Additional gate metadata
    description: NotRequired[str]  # Human-readable description

    # Evaluation behavior
    short_circuit: NotRequired[bool]  # Enable short-circuit evaluation
    timeout_ms: NotRequired[int]  # Maximum evaluation time in milliseconds

    # Error handling
    error_strategy: NotRequired[str]  # How to handle component errors ("fail", "skip", "continue")
    custom_error_message: NotRequired[str]  # Override default error messages


class GateSetConfig(TypedDict):
    """Configuration interface for a set of gates in a stage.

    Defines how multiple gates work together within a stage context.
    """

    # Gate set identification
    stage_name: str  # Name of the stage these gates belong to
    gates: list[GateConfig]  # List of gate configurations

    # Evaluation strategy
    evaluation_mode: NotRequired[str]  # "all", "any", "sequential", "parallel"
    continue_on_failure: NotRequired[bool]  # Whether to continue evaluating after failures

    # Performance settings
    parallel_execution: NotRequired[bool]  # Enable parallel gate evaluation
    max_concurrent: NotRequired[int]  # Maximum concurrent evaluations

    # Metadata
    metadata: NotRequired[dict[str, Any]]  # Additional gate set metadata
    description: NotRequired[str]  # Human-readable description


class ValidatorConfig(TypedDict):
    """Configuration interface for custom validator registration.

    Defines the interface for registering custom validation functions
    in the validator registry.
    """

    # Validator identification
    name: str  # Unique name for the validator
    description: str  # Human-readable description

    # Function signature information
    expected_params: NotRequired[dict[str, str]]  # Expected parameter descriptions
    return_type: NotRequired[str]  # Expected return type description

    # Metadata
    version: NotRequired[str]  # Validator version
    author: NotRequired[str]  # Validator author
    tags: NotRequired[list[str]]  # Categorization tags

    # Validation behavior
    is_async: NotRequired[bool]  # Whether validator is asynchronous
    thread_safe: NotRequired[bool]  # Whether validator is thread-safe

    # Example usage
    examples: NotRequired[list[dict[str, Any]]]  # Example configurations


# Type aliases for common configurations
AnyLockConfig = LockConfig
AnyGateConfig = GateConfig
ConfigDict = dict[str, Any]

# Configuration validation helpers
def validate_lock_config(config: dict[str, Any]) -> bool:
    """Validate that a dictionary conforms to LockConfig interface.

    Args:
        config: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_keys = {"property_path", "lock_type"}
    return all(key in config for key in required_keys)


def validate_gate_config(config: dict[str, Any]) -> bool:
    """Validate that a dictionary conforms to GateConfig interface.

    Args:
        config: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_keys = {"name", "operation", "components"}
    return all(key in config for key in required_keys)


def validate_gate_set_config(config: dict[str, Any]) -> bool:
    """Validate that a dictionary conforms to GateSetConfig interface.

    Args:
        config: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_keys = {"stage_name", "gates"}
    return (
        all(key in config for key in required_keys)
        and isinstance(config.get("gates"), list)
    )


def validate_validator_config(config: dict[str, Any]) -> bool:
    """Validate that a dictionary conforms to ValidatorConfig interface.

    Args:
        config: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_keys = {"name", "description"}
    return all(key in config for key in required_keys)