"""
Centralized exports for the StageFlow schema loaders module.

This module consolidates all the imports and exports from the various
loader components to simplify the __init__.py file.
"""

# JSON loader imports
from stageflow.process.schema.loaders.json import (
    JsonLoader, JSONLoadError, JSONSchemaError, JSONReferenceError,
    load_process as load_json_process,
    load_process_from_string as load_json_process_from_string
)

# YAML loader imports
from stageflow.process.schema.loaders.yaml import (
    YamlLoader, YAMLLoadError, YAMLSchemaError, YAMLIncludeError,
    load_process, load_process_from_string
)

# Utilities imports
from stageflow.process.schema.loaders.utils import (
    SchemaParsingError, SchemaValidationError,
    clear_cache, create_error_report, extract_validation_errors,
    format_parsing_error, format_validation_report, get_cache_stats,
    load_file_with_cache, merge_schema_fragments, normalize_path,
    normalize_schema, resolve_includes, resolve_references,
    transform_legacy_format, validate_with_pydantic
)

# Schema models imports
from stageflow.process.schema.models import (
    validate_stageflow_schema, validate_process_definition,
    ValidationContext, StageFlowSchemaModel, ProcessModel,
    StageModel, GateModel, LockModel, ItemSchemaModel,
    FieldDefinitionModel, ActionDefinitionModel, StageActionDefinitionsModel
)

# Define all exports in a single place
ALL_EXPORTS = [
    # Loaders
    "YamlLoader",
    "JsonLoader",
    # YAML loader exports
    "YAMLLoadError",
    "YAMLSchemaError",
    "YAMLIncludeError",
    "load_process",
    "load_process_from_string",
    # JSON loader exports
    "JSONLoadError",
    "JSONSchemaError",
    "JSONReferenceError",
    "load_json_process",
    "load_json_process_from_string",
    # Utility functions
    "SchemaParsingError",
    "SchemaValidationError",
    "clear_cache",
    "create_error_report",
    "extract_validation_errors",
    "format_parsing_error",
    "format_validation_report",
    "get_cache_stats",
    "load_file_with_cache",
    "merge_schema_fragments",
    "normalize_path",
    "normalize_schema",
    "resolve_includes",
    "resolve_references",
    "transform_legacy_format",
    "validate_with_pydantic",
    # Validation models and functions
    "validate_stageflow_schema",
    "validate_process_definition",
    "ValidationContext",
    "StageFlowSchemaModel",
    "ProcessModel",
    "StageModel",
    "GateModel",
    "LockModel",
    "ItemSchemaModel",
    "FieldDefinitionModel",
    "ActionDefinitionModel",
    "StageActionDefinitionsModel",
]

