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
    FileReader,
    Loader,
    LoadError,
    load_element,
    load_process,
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
    "Loader",           # Class-based interface for loading
    "LoadError",
    "FileReader",       # Advanced I/O operations
    "load_process",
    "load_element",     # Element loader function
]
