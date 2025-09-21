"""Gates module for StageFlow validation framework.

This module provides the complete gates and locks system for StageFlow,
including validation logic, composition patterns, configuration interfaces,
and registry functionality.

Key Components:
- Lock: Individual validation constraints with various built-in types
- Gate: Composable validation rules using logical operations
- Registry: Custom validator and pattern registration system
- Config: TypedDict interfaces for configuration data contracts

Example Usage:
    Basic lock and gate creation:
        >>> from stageflow.gates import Lock, Gate, LockType
        >>> lock1 = Lock(LockType.EXISTS, "user.email")
        >>> lock2 = Lock(LockType.REGEX, "user.email", r"^[^@]+@[^@]+\.[^@]+$")
        >>> gate = Gate.AND(lock1, lock2, name="email_validation")

    Using custom validators:
        >>> from stageflow.gates import register_validator
        >>> def validate_domain(value, domains):
        ...     return value.split("@")[1] in domains
        >>> register_validator("domain_check", validate_domain)
        >>> domain_lock = Lock(LockType.CUSTOM, "email", ["company.com"], validator_name="domain_check")

    Configuration-driven approach:
        >>> from stageflow.gates.config import LockConfig, GateConfig
        >>> lock_config: LockConfig = {
        ...     "property_path": "user.age",
        ...     "lock_type": "greater_than",
        ...     "expected_value": 18
        ... }
"""

# Core validation components
from stageflow.gates.lock import (
    Lock,
    LockType,
    ValidationResult,
    PropertyNotFoundError,
    ValidationError,
    InvalidPathError,
    AccessDeniedError,
    register_validator as register_lock_validator,
    get_validator as get_lock_validator,
    list_validators as list_lock_validators,
    clear_validators as clear_lock_validators,
)

from stageflow.gates.gate import (
    Gate,
    GateOperation,
    GateResult,
    Evaluable,
    LockWrapper,
)

# Configuration interfaces
from stageflow.gates.config import (
    LockConfig,
    GateConfig,
    GateSetConfig,
    ValidatorConfig,
    AnyLockConfig,
    AnyGateConfig,
    ConfigDict,
    validate_lock_config,
    validate_gate_config,
    validate_gate_set_config,
    validate_validator_config,
)

# Registry system
from stageflow.gates.registry import (
    GatesRegistry,
    ValidatorEntry,
    GateBuilderEntry,
    get_global_registry,
    register_validator,
    get_validator,
    register_gate_builder,
    register_lock_pattern,
    register_gate_pattern,
)

# Re-export common functions with clear naming
register_custom_validator = register_validator
get_custom_validator = get_validator
register_pattern = register_lock_pattern

__all__ = [
    # Core lock functionality
    "Lock",
    "LockType",
    "ValidationResult",
    "PropertyNotFoundError",
    "ValidationError",
    "InvalidPathError",
    "AccessDeniedError",

    # Core gate functionality
    "Gate",
    "GateOperation",
    "GateResult",
    "Evaluable",
    "LockWrapper",

    # Configuration interfaces
    "LockConfig",
    "GateConfig",
    "GateSetConfig",
    "ValidatorConfig",
    "AnyLockConfig",
    "AnyGateConfig",
    "ConfigDict",
    "validate_lock_config",
    "validate_gate_config",
    "validate_gate_set_config",
    "validate_validator_config",

    # Registry system
    "GatesRegistry",
    "ValidatorEntry",
    "GateBuilderEntry",
    "get_global_registry",
    "register_validator",
    "get_validator",
    "register_gate_builder",
    "register_lock_pattern",
    "register_gate_pattern",

    # Legacy lock validator functions
    "register_lock_validator",
    "get_lock_validator",
    "list_lock_validators",
    "clear_lock_validators",

    # Convenience aliases
    "register_custom_validator",
    "get_custom_validator",
    "register_pattern",
]

# Module metadata
__version__ = "1.0.0"
__author__ = "StageFlow Team"
__description__ = "Gates and locks validation system for StageFlow"