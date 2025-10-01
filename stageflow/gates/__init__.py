r"""Gates module for StageFlow validation framework.

This module provides the complete gates and locks system for StageFlow,
including validation logic, composition patterns, configuration interfaces,
and registry functionality.

Key Components:
- Lock: Individual validation constraints with various built-in types
- Gate: Composable validation rules using logical operations
- Registry: Custom validator and pattern registration system
- Config: TypedDict interfaces for configuration data contracts

"""

from stageflow.gates.gate import (
    Gate,
    GateDefinition,
    GateResult,
)
from stageflow.gates.lock import (
    Lock,
    LockDefinition,
    LockResult,
    LockType,
)

__all__ = [
    "Lock",
    "LockType",
    "LockResult",
    "LockDefinition",
    "Gate",
    "GateResult",
    "GateDefinition",
]
