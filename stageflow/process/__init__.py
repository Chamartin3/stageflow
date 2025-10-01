"""Process domain for StageFlow - orchestration and validation."""

from .config import ProcessConfig

# Import main process components
from .main import Process
from .result import (
    Action,
    ActionType,
    DiagnosticInfo,
    ErrorInfo,
    EvaluationState,
    Priority,
    Severity,
    StatusResult,
    WarningInfo,
)

# Import submodule handling
from .submodules import get_submodule

# Add main components to exports
__all__ = [
    "Process",
    "ProcessConfig",
    "StatusResult",
    "EvaluationState",
    "Action",
    "DiagnosticInfo",
    "ErrorInfo",
    "WarningInfo",
    "Priority",
    "Severity",
    "ActionType",
]

# Simple attribute access for submodules
def __getattr__(name: str):
    """Get process submodules."""
    return get_submodule(name)
