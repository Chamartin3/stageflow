"""
Core domain models for StageFlow.

This module contains the fundamental building blocks of the StageFlow framework:
- Element: Data wrapper interface
- Stage: Validation stages with gates
- Process: Multi-stage workflow orchestration

Note: Lock and Gate classes have been moved to the stageflow.gates module
for better organization and separation of concerns.
"""

from stageflow.core.element import Element
from stageflow.core.stage import Stage

# Re-export gates and locks from the dedicated gates module for backward compatibility
from stageflow.gates import (
    AccessDeniedError,
    Gate,
    InvalidPathError,
    Lock,
    LockType,
    PropertyNotFoundError,
    ValidationError,
    ValidationResult,
)

__all__ = [
    "Element",
    "Stage",
    # Re-exported from gates module for backward compatibility
    "Lock",
    "LockType",
    "ValidationResult",
    "PropertyNotFoundError",
    "ValidationError",
    "InvalidPathError",
    "AccessDeniedError",
    "Gate",
]
