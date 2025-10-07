"""
Simplified Schema module for StageFlow.

This module provides simple loading functionality for process definitions.
All validation is handled by the core Process class.
"""

# Import core definitions from main modules
from stageflow.process import Process, ProcessDefinition, ProcessElementEvaluationResult
from stageflow.stage import StageDefinition, ActionDefinition
from stageflow.gate import GateDefinition
from stageflow.lock import LockDefinition

# Import simplified loader
from stageflow.schema.loader import (
    LoadError,
    load_process,
    load_process_data
)

__all__ = [
    # Core classes and types
    "Process",
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "StageDefinition",
    "ActionDefinition",
    "GateDefinition",
    "LockDefinition",

    # Loader functions
    "LoadError",
    "load_process",
    "load_process_data",
]
