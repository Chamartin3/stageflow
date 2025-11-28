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
# Analysis data models
from .analysis import (
    ProcessGraph,
    StageSchemaMutations,
)
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
    RegressionDetails,
    RegressionPolicyLiteral,
    StageDefinition,
    StageFieldsDefinition,
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
    IssueSeverity,
    LoadErrorType,
    LoadResultStatus,
    LockTypeShorthand,
    ProcessSourceType,
    RegressionPolicy,
    SpecialLockType,
)

# Error and result models
from .errors import (
    ErrorContextDict,
    LoadError,
    ProcessLoadResult,
    ProcessLoadResultDict,
)

# Property models (new unified system)
from .properties import (
    BoolProperty,
    DictProperty,
    ListProperty,
    NumberProperty,
    PropertiesParser,
    Property,
    PropertyType,
    PropertyValidator,
    StringProperty,
)

# Schema lifecycle types
from .schema import (
    ExtractedProperty,
    InferredType,
    PropertySchema,
    PropertySource,
    SchemaType,
    StageSchema,
)

__all__ = [
    # Enums
    "LoadResultStatus",
    "ErrorSeverity",
    "IssueSeverity",
    "LoadErrorType",
    "ProcessSourceType",
    "FileFormat",
    "LockTypeShorthand",
    "RegressionPolicy",
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
    "StageFieldsDefinition",
    "StageDefinition",
    # Process types
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "RegressionDetails",
    "RegressionPolicyLiteral",
    # File format types
    "ProcessFileDict",
    "LegacyProcessFileDict",
    "ProcessFile",
    # Property models (new unified system)
    "Property",
    "PropertyType",
    "StringProperty",
    "NumberProperty",
    "BoolProperty",
    "ListProperty",
    "DictProperty",
    "PropertiesParser",
    "PropertyValidator",
    # Schema lifecycle types
    "SchemaType",
    "PropertySource",
    "InferredType",
    "ExtractedProperty",
    "PropertySchema",
    "StageSchema",
    # Analysis data models
    "ProcessGraph",
    "StageSchemaMutations",
]
