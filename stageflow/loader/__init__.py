"""
Loader module for StageFlow - Process Loading and Parsing.

This module provides process loading functionality with comprehensive
error collection and unified result types. It handles loading process
definitions from YAML/JSON files and registry sources.

All type definitions are imported from stageflow.models for consistency.
"""

import json
from pathlib import Path

from stageflow.elements import Element, create_element

# Core definitions from main modules
from stageflow.gate import GateDefinition

# Process loader and validators (now directly in loader/)
from stageflow.loader.loader import ProcessLoader
from stageflow.loader.validators import (
    GateConfigValidator,
    LockConfigValidator,
    ProcessConfigValidator,
    StageConfigValidator,
)
from stageflow.lock import LockDefinition
from stageflow.models import (
    ErrorSeverity,
    LoadErrorType,
    LoadResultStatus,
    ProcessLoadResult,
    ProcessSourceType,
)

# Unified models and enums
from stageflow.models import (
    LoadError as LoadErrorModel,
)
from stageflow.process import Process, ProcessDefinition, ProcessElementEvaluationResult
from stageflow.stage import ActionDefinition, StageDefinition


class LoadError(Exception):
    """Exception raised when loading fails."""

    pass


def load_process(file_path: str | Path) -> Process:
    """
    Load a Process from a file.

    This is a convenience function that wraps ProcessLoader
    and provides simple error handling.

    Args:
        file_path: Path to the process definition file

    Returns:
        Process object if successful

    Raises:
        LoadError: If loading fails
    """
    loader = ProcessLoader()
    result = loader.load(file_path)

    if result.success and result.process:
        return result.process

    # Collect error messages
    error_messages = [error.message for error in result.errors]
    error_summary = "\n  • ".join(error_messages)
    raise LoadError(f"Failed to load process from {file_path}:\n  • {error_summary}")


def load_element(file_path: str | Path) -> Element:
    """
    Load an Element from a JSON file.

    Args:
        file_path: Path to the element data file

    Returns:
        Element instance

    Raises:
        LoadError: If file cannot be loaded or parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise LoadError(f"File not found: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise LoadError("Element data must be a dictionary")

        return create_element(data)

    except json.JSONDecodeError as e:
        raise LoadError(f"Error parsing JSON in {file_path}: {e}") from e
    except PermissionError as e:
        raise LoadError(f"Permission denied reading {file_path}") from e
    except Exception as e:
        if isinstance(e, LoadError):
            raise
        raise LoadError(f"Element validation failed: {e}") from e


__all__ = [
    # Core classes and types
    "Process",
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "StageDefinition",
    "ActionDefinition",
    "GateDefinition",
    "LockDefinition",
    # Unified models
    "LoadErrorModel",
    "LoadErrorType",
    "LoadResultStatus",
    "ProcessLoadResult",
    "ProcessSourceType",
    "ErrorSeverity",
    # Loader
    "ProcessLoader",
    # Validators
    "ProcessConfigValidator",
    "StageConfigValidator",
    "GateConfigValidator",
    "LockConfigValidator",
    # Public API
    "LoadError",
    "load_process",
    "load_element",
]
