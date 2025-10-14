"""
StageFlow Manager Module

Provides process management capabilities including configuration management,
process registry, and editing functionality for StageFlow processes.

This module contains:
- ManagerConfig: Configuration management for the manager submodule
- ProcessRegistry: Registry for managing multiple processes
- ProcessEditor: Interactive editing capabilities for processes
- ProcessManager: Main interface for process management operations
"""

from .config import (
    ConfigValidationError,
    ManagerConfig,
    ManagerConfigDict,
    ProcessFileFormat,
)
from .editor import ProcessEditor, ProcessEditorError, ValidationFailedError
from .manager import (
    ProcessManager,
    ProcessManagerError,
    ProcessNotFoundError,
    ProcessSyncError,
    ProcessValidationError,
)
from .registry import ProcessRegistry, ProcessRegistryError

__all__ = [
    "ManagerConfig",
    "ConfigValidationError",
    "ProcessFileFormat",
    "ManagerConfigDict",
    "ProcessEditor",
    "ProcessEditorError",
    "ValidationFailedError",
    "ProcessRegistry",
    "ProcessRegistryError",
    "ProcessManager",
    "ProcessManagerError",
    "ProcessNotFoundError",
    "ProcessValidationError",
    "ProcessSyncError",
]
