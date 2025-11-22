"""
StageFlow models package.

This package is the single source of truth for all type definitions, enums,
and data structures used throughout the StageFlow framework. All TypedDicts
and data models are defined here and imported by other modules.

Usage:
    from stageflow.models import (
        LoadResultStatus,
        LoadError,
        ProcessLoadResult,
        ProcessDefinition,
        StageDefinition,
        GateDefinition,
        LockDefinitionDict,
    )
"""

# Enumerations
# Base TypedDict definitions (single source of truth)
from .base import (
    ActionDefinition,
    ConditionalLockDict,
    ExpectedObjectSchmema,
    GateDefinition,
    LegacyProcessFileDict,
    LockDefinition,
    LockDefinitionDict,
    LockMetaData,
    LockShorthandDict,
    LockType,
    ProcessDefinition,
    ProcessElementEvaluationResult,
    ProcessFile,
    ProcessFileDict,
    StageDefinition,
    StageObjectPropertyDefinition,
)

# Consistency models
from .consistency import (
    ConsistencyIssue,
    ProcessIssueTypes,
    TerminationAnalysis,
)
from .enums import (
    ErrorSeverity,
    FileFormat,
    LoadErrorType,
    LoadResultStatus,
    LockTypeShorthand,
    ProcessSourceType,
    SpecialLockType,
)

# Error and result models
from .errors import (
    ErrorContextDict,
    LoadError,
    ProcessLoadResult,
    ProcessLoadResultDict,
)

__all__ = [
    # Enums
    "LoadResultStatus",
    "ErrorSeverity",
    "LoadErrorType",
    "ProcessSourceType",
    "FileFormat",
    "LockTypeShorthand",
    "SpecialLockType",
    "LockType",

    # Error models
    "LoadError",
    "ProcessLoadResult",
    "ProcessLoadResultDict",
    "ErrorContextDict",

    # Consistency models
    "ConsistencyIssue",
    "ProcessIssueTypes",
    "TerminationAnalysis",
    # Lock types
    "LockMetaData",
    "LockDefinitionDict",
    "LockShorthandDict",
    "ConditionalLockDict",
    "LockDefinition",
    # Gate types
    "GateDefinition",
    # Stage types
    "ActionDefinition",
    "StageObjectPropertyDefinition",
    "ExpectedObjectSchmema",
    "StageDefinition",
    # Process types
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    # File format types
    "ProcessFileDict",
    "LegacyProcessFileDict",
    "ProcessFile",
]
