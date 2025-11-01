"""
Simplified Schema module for StageFlow.

This module provides simple loading functionality for process definitions.
All validation is handled by the core Process class.
"""

# Import core definitions from main modules
from stageflow.gate import GateDefinition
from stageflow.lock import LockDefinition
from stageflow.process import Process, ProcessDefinition, ProcessElementEvaluationResult

# Import simplified loader
from stageflow.schema.loader import (
    ConfigValidationError,
    FileReader,
    Loader,
    LoadError,
    ProcessConfigParser,
    ProcessLoader,
    ProcessSourceType,
    ProcessWithErrors,
    add_schema_to_yaml_output,
    get_local_schema_path,
    load_element,
    load_process,
    load_process_graceful,
    save_process_with_local_schema,
    save_process_with_schema,
)
from stageflow.stage import ActionDefinition, StageDefinition

__all__ = [
    # Core classes and types
    "Process",
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "StageDefinition",
    "ActionDefinition",
    "GateDefinition",
    "LockDefinition",
    # Loader interface
    "Loader",  # Class-based interface for loading
    "LoadError",
    "ConfigValidationError",  # Comprehensive validation error with error collection
    "ProcessConfigParser",  # Parser and validator for process configuration
    "ProcessLoader",  # Unified loader for files and registry
    "ProcessSourceType",  # Enum for source type detection
    "ProcessWithErrors",  # Graceful error handling
    "FileReader",  # Advanced I/O operations
    "load_process",
    "load_process_graceful",  # Graceful loading
    "load_element",  # Element loader function
    # Schema integration functions
    "add_schema_to_yaml_output",  # Add $schema to process dictionaries
    "save_process_with_schema",  # Save process with schema reference
    "save_process_with_local_schema",  # Save with local schema file reference
    "get_local_schema_path",  # Get path to local schema file
]
