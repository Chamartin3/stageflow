"""
Loader module for StageFlow - Process Loading and Parsing.

This module provides process loading functionality with comprehensive
error collection and unified result types. It handles loading process
definitions from YAML/JSON files and registry sources.

All type definitions are imported from stageflow.models for consistency.
"""

import json
from pathlib import Path

from ruamel.yaml import YAML

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


def _parse_yaml(content: str) -> dict | None:
    """
    Parse YAML content using ruamel.yaml.

    Args:
        content: YAML string content

    Returns:
        Parsed data as dict, or None if parsing fails or result is not a dict
    """
    yaml_parser = YAML(typ="safe")
    try:
        data = yaml_parser.load(content)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def _parse_markdown_frontmatter(content: str) -> dict | None:
    """
    Extract YAML frontmatter from Markdown content.

    Frontmatter must be at the start of the file, delimited by '---' lines.

    Args:
        content: Raw Markdown file content

    Returns:
        Parsed frontmatter as dict, or None if no valid frontmatter found
    """
    content = content.lstrip()
    if not content.startswith("---"):
        return None

    # Find the closing delimiter
    end_index = content.find("\n---", 3)
    if end_index == -1:
        return None

    frontmatter_text = content[3:end_index].strip()
    if not frontmatter_text:
        return None

    return _parse_yaml(frontmatter_text)


def load_element(file_path: str | Path) -> Element:
    """
    Load an Element from a JSON, YAML, or Markdown file.

    Supported formats:
    - JSON files (.json)
    - YAML files (.yaml, .yml)
    - Markdown files (.md) with YAML frontmatter

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

    suffix = file_path.suffix.lower()

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse based on file extension
        data: dict | None = None
        if suffix == ".json":
            data = json.loads(content)
        elif suffix in (".yaml", ".yml"):
            data = _parse_yaml(content)
            if data is None:
                raise LoadError(f"Error parsing YAML in {file_path}")
        elif suffix == ".md":
            data = _parse_markdown_frontmatter(content)
            if data is None:
                raise LoadError(
                    f"Markdown file {file_path} has no valid YAML frontmatter. "
                    "Element data must be in frontmatter delimited by '---' lines."
                )
        else:
            # Try JSON first, then YAML
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                data = _parse_yaml(content)
                if data is None:
                    raise LoadError(
                        f"Could not parse {file_path} as JSON or YAML"
                    ) from e

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
