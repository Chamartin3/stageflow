"""
Schema module for StageFlow process domain.

This module centralizes all schema-related functionality including model definitions,
core schema types, and loaders for various formats (YAML, JSON).
"""

# Core schema types
from stageflow.process.schema.core import (
    FieldDefinition,
    ItemSchema,
    ItemSchemaModel,
    SchemaError,
    ValidationError,
    ValidationResult,
)

# Loaders
from stageflow.process.schema.loaders import (
    JsonLoader,
    JSONLoadError,
    JSONReferenceError,
    JSONSchemaError,
    SchemaParsingError,
    SchemaValidationError,
    YAMLIncludeError,
    YamlLoader,
    YAMLLoadError,
    YAMLSchemaError,
    load_json_process,
    load_json_process_from_string,
    load_process,
    load_process_from_string,
)

# Schema models and validation
from stageflow.process.schema.models import (
    BaseStageFlowModel,
    FieldDefinitionModel,
    GateModel,
    LockModel,
    ProcessConfigModel,
    ProcessModel,
    StageFlowSchemaModel,
    StageModel,
    ValidationContext,
    validate_process_definition,
    validate_stageflow_schema,
)

__all__ = [
    # Core schema types
    "FieldDefinition",
    "ItemSchema",
    "ItemSchemaModel",
    "SchemaError",
    "ValidationError",
    "ValidationResult",
    # Schema models
    "BaseStageFlowModel",
    "FieldDefinitionModel",
    "GateModel",
    "LockModel",
    "ProcessConfigModel",
    "ProcessModel",
    "StageFlowSchemaModel",
    "StageModel",
    "ValidationContext",
    "validate_process_definition",
    "validate_stageflow_schema",
    # Loaders
    "JsonLoader",
    "JSONLoadError",
    "JSONReferenceError",
    "JSONSchemaError",
    "SchemaParsingError",
    "SchemaValidationError",
    "YamlLoader",
    "YAMLIncludeError",
    "YAMLLoadError",
    "YAMLSchemaError",
    "load_json_process",
    "load_json_process_from_string",
    "load_process",
    "load_process_from_string",
]
