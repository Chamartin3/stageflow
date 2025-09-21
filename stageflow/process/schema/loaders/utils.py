"""
Schema parsing utilities for StageFlow loaders.

This module provides common utility functions and helper classes to support
schema parsing operations across YAML and JSON loaders. It includes file loading,
caching, path resolution, schema normalization, and error handling utilities.

Features:
- File loading with caching for performance
- Path resolution for includes and references
- Schema normalization and transformation
- Error formatting and reporting
- Integration with pydantic validation system
- Comprehensive type annotations and documentation
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML

# Cache statistics
_cache_stats = {"hits": 0, "misses": 0, "size": 0}

# File cache using functools.lru_cache for automatic size management
@lru_cache(maxsize=128)
def _cached_file_load(file_path_str: str, file_mtime: float) -> dict[str, Any]:
    """
    Internal cached file loading function.

    Uses file modification time as cache key to ensure cache invalidation
    when files are modified.

    Args:
        file_path_str: String representation of file path
        file_mtime: File modification time for cache invalidation

    Returns:
        Loaded file data as dictionary
    """
    global _cache_stats
    _cache_stats["misses"] += 1
    _cache_stats["size"] = _cached_file_load.cache_info().currsize

    file_path = Path(file_path_str)

    if file_path.suffix.lower() in {'.yaml', '.yml'}:
        yaml = YAML(typ="safe")
        with open(file_path, encoding="utf-8") as f:
            return yaml.load(f) or {}
    elif file_path.suffix.lower() == '.json':
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


def load_file_with_cache(file_path: Path) -> dict[str, Any]:
    """
    Load a file with automatic caching based on modification time.

    This function provides efficient file loading with automatic cache invalidation
    when files are modified. Supports both YAML and JSON formats.

    Args:
        file_path: Path to the file to load

    Returns:
        Loaded file data as dictionary

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported
        SchemaParsingError: If the file cannot be parsed

    Examples:
        >>> from pathlib import Path
        >>> data = load_file_with_cache(Path("config.yaml"))
        >>> print(data["name"])
    """
    global _cache_stats

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Get file modification time for cache key
        file_mtime = file_path.stat().st_mtime

        # Try to load from cache
        result = _cached_file_load(str(file_path), file_mtime)
        _cache_stats["hits"] += 1
        _cache_stats["size"] = _cached_file_load.cache_info().currsize

        return result

    except Exception as e:
        raise SchemaParsingError(
            f"Failed to load file {file_path}: {str(e)}",
            file_path=str(file_path)
        ) from e


def clear_cache() -> None:
    """
    Clear the file loading cache.

    This function clears all cached file data and resets cache statistics.
    Useful for testing or when you want to force reload of all files.

    Examples:
        >>> clear_cache()
        >>> stats = get_cache_stats()
        >>> assert stats["size"] == 0
    """
    global _cache_stats
    _cached_file_load.cache_clear()
    _cache_stats = {"hits": 0, "misses": 0, "size": 0}


def get_cache_stats() -> dict[str, int]:
    """
    Get current cache statistics.

    Returns:
        Dictionary containing cache hit count, miss count, and current size

    Examples:
        >>> stats = get_cache_stats()
        >>> print(f"Cache hits: {stats['hits']}, misses: {stats['misses']}")
    """
    global _cache_stats
    return _cache_stats.copy()


def normalize_path(path: str | Path, base_path: Path) -> Path:
    """
    Normalize a path relative to a base path.

    This function resolves relative paths against a base path and returns
    an absolute path. It also normalizes path separators and resolves
    symbolic links.

    Args:
        path: Path to normalize (can be relative or absolute)
        base_path: Base path for resolving relative paths

    Returns:
        Normalized absolute path

    Examples:
        >>> from pathlib import Path
        >>> base = Path("/project/schemas")
        >>> normalized = normalize_path("../common/base.yaml", base)
        >>> print(normalized)
        /project/common/base.yaml
    """
    path_obj = Path(path)

    if path_obj.is_absolute():
        return path_obj.resolve()
    else:
        return (base_path / path_obj).resolve()


def resolve_includes(schema_data: dict[str, Any], base_path: Path) -> dict[str, Any]:
    """
    Resolve include directives in schema data.

    This function processes include directives in schema data, loading
    referenced files and merging their content. Supports both simple
    includes and includes with key path specifications.

    Args:
        schema_data: Dictionary containing schema data with potential includes
        base_path: Base path for resolving relative include paths

    Returns:
        Schema data with includes resolved and merged

    Raises:
        SchemaParsingError: If include resolution fails

    Examples:
        >>> data = {"stages": {"$include": "common/stages.yaml"}}
        >>> resolved = resolve_includes(data, Path("/schemas"))
    """
    if not isinstance(schema_data, dict):
        return schema_data

    result = {}

    for key, value in schema_data.items():
        if key == "$include" and isinstance(value, (str, dict)):
            # Handle include directive
            try:
                included_data = _process_include_directive(value, base_path)
                # Merge included data into result
                if isinstance(included_data, dict):
                    result.update(included_data)
                else:
                    result[key] = included_data
            except Exception as e:
                raise SchemaParsingError(
                    f"Failed to resolve include: {value}",
                    file_path=str(base_path)
                ) from e
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = resolve_includes(value, base_path)
        elif isinstance(value, list):
            # Process list items
            result[key] = [
                resolve_includes(item, base_path) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def resolve_references(schema_data: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve internal references within schema data.

    This function processes internal references (like JSON pointers)
    within the schema data structure, replacing reference paths with
    the actual referenced data.

    Args:
        schema_data: Dictionary containing schema data with potential references

    Returns:
        Schema data with internal references resolved

    Raises:
        SchemaParsingError: If reference resolution fails

    Examples:
        >>> data = {"definitions": {"user": {"type": "object"}},
        ...         "schema": {"$ref": "#/definitions/user"}}
        >>> resolved = resolve_references(data)
    """
    if not isinstance(schema_data, dict):
        return schema_data

    # Create a copy to avoid modifying the original
    result = schema_data.copy()

    # Process references recursively
    result = _resolve_references_recursive(result, schema_data)

    return result


def normalize_schema(schema_data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize schema data to a consistent format.

    This function normalizes schema data by standardizing field names,
    converting values to consistent types, and applying default values
    where appropriate.

    Args:
        schema_data: Dictionary containing schema data to normalize

    Returns:
        Normalized schema data

    Examples:
        >>> data = {"Name": "process", "Stages": [...]}
        >>> normalized = normalize_schema(data)
        >>> assert "name" in normalized
    """
    if not isinstance(schema_data, dict):
        return schema_data

    result = {}

    # Normalize key names to lowercase
    for key, value in schema_data.items():
        normalized_key = key.lower()

        # Special handling for common schema fields
        if normalized_key in {"name", "description", "version"}:
            result[normalized_key] = str(value) if value is not None else ""
        elif normalized_key in {"stages", "gates", "locks", "metadata"}:
            if isinstance(value, dict):
                result[normalized_key] = {k: normalize_schema(v) if isinstance(v, dict) else v
                                        for k, v in value.items()}
            elif isinstance(value, list):
                result[normalized_key] = [normalize_schema(item) if isinstance(item, dict) else item
                                        for item in value]
            else:
                result[normalized_key] = value
        elif normalized_key in {"required_fields", "optional_fields", "stage_order"}:
            result[normalized_key] = list(value) if isinstance(value, (list, tuple, set)) else []
        elif normalized_key in {"allow_stage_skipping", "regression_detection", "allow_partial"}:
            result[normalized_key] = bool(value) if value is not None else False
        else:
            # For other fields, normalize recursively if dict, otherwise keep as-is
            if isinstance(value, dict):
                result[normalized_key] = normalize_schema(value)
            else:
                result[normalized_key] = value

    return result


def transform_legacy_format(schema_data: dict[str, Any]) -> dict[str, Any]:
    """
    Transform legacy schema format to current format.

    This function converts older schema formats to the current StageFlow
    schema format, handling field renames, structure changes, and
    deprecated features.

    Args:
        schema_data: Dictionary containing legacy schema data

    Returns:
        Schema data transformed to current format

    Examples:
        >>> legacy_data = {"process_name": "old", "step_definitions": [...]}
        >>> current = transform_legacy_format(legacy_data)
        >>> assert "name" in current and "stages" in current
    """
    if not isinstance(schema_data, dict):
        return schema_data

    result = schema_data.copy()

    # Handle legacy field name mappings
    legacy_mappings = {
        "process_name": "name",
        "step_definitions": "stages",
        "step_order": "stage_order",
        "gate_definitions": "gates",
        "lock_definitions": "locks",
        "validation_schema": "schema",
        "skip_stages": "allow_stage_skipping",
        "detect_regression": "regression_detection",
    }

    for legacy_key, current_key in legacy_mappings.items():
        if legacy_key in result and current_key not in result:
            result[current_key] = result.pop(legacy_key)

    # Transform legacy stage format
    if "stages" in result and isinstance(result["stages"], dict):
        for _stage_name, stage_data in result["stages"].items():
            if isinstance(stage_data, dict):
                # Transform legacy gate format
                if "gate_definitions" in stage_data:
                    stage_data["gates"] = stage_data.pop("gate_definitions")

                # Transform legacy schema format
                if "validation_schema" in stage_data:
                    stage_data["schema"] = stage_data.pop("validation_schema")

    # Transform legacy lock types
    if "stages" in result:
        result = _transform_legacy_lock_types(result)

    return result


def merge_schema_fragments(fragments: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Merge multiple schema fragments into a single schema.

    This function combines multiple schema fragments, handling conflicts
    and maintaining the integrity of the merged schema. Later fragments
    take precedence over earlier ones for conflicting keys.

    Args:
        fragments: List of schema dictionaries to merge

    Returns:
        Single merged schema dictionary

    Raises:
        SchemaParsingError: If fragments cannot be merged

    Examples:
        >>> base = {"name": "base", "stages": {"stage1": {...}}}
        >>> override = {"stages": {"stage2": {...}}}
        >>> merged = merge_schema_fragments([base, override])
    """
    if not fragments:
        return {}

    if len(fragments) == 1:
        return fragments[0].copy()

    result = {}

    for fragment in fragments:
        if not isinstance(fragment, dict):
            raise SchemaParsingError(f"Schema fragment must be a dictionary, got {type(fragment)}")

        result = _deep_merge_dicts(result, fragment)

    return result


def _process_include_directive(include_value: str | dict[str, Any], base_path: Path) -> dict[str, Any]:
    """Process an include directive and return the included data."""
    if isinstance(include_value, str):
        # Simple include: path/to/file.yaml
        include_path = normalize_path(include_value, base_path)
        return load_file_with_cache(include_path)

    elif isinstance(include_value, dict):
        # Complex include: {file: "path", key: "section"}
        if "file" not in include_value:
            raise SchemaParsingError("Include directive must specify 'file' key")

        include_path = normalize_path(include_value["file"], base_path)
        data = load_file_with_cache(include_path)

        # Extract specific key if specified
        if "key" in include_value:
            key_path = include_value["key"]
            data = _extract_key_path(data, key_path)

        return data

    else:
        raise SchemaParsingError(f"Invalid include directive: {include_value}")


def _resolve_references_recursive(data: Any, root_data: dict[str, Any]) -> Any:
    """Recursively resolve internal references in data structure."""
    if isinstance(data, dict):
        if "$ref" in data:
            # Resolve the reference
            ref_path = data["$ref"]
            if ref_path.startswith("#/"):
                # Internal JSON pointer
                return _resolve_json_pointer(root_data, ref_path[2:])
            else:
                raise SchemaParsingError(f"Unsupported reference format: {ref_path}")
        else:
            # Recursively process dictionary values
            return {k: _resolve_references_recursive(v, root_data) for k, v in data.items()}

    elif isinstance(data, list):
        # Recursively process list items
        return [_resolve_references_recursive(item, root_data) for item in data]

    else:
        # Return primitive values as-is
        return data


def _resolve_json_pointer(data: Any, pointer_path: str) -> Any:
    """Resolve a JSON pointer path in the data structure."""
    if not pointer_path:
        return data

    parts = pointer_path.split("/")
    current = data

    for part in parts:
        # Unescape JSON pointer special characters
        part = part.replace("~1", "/").replace("~0", "~")

        if isinstance(current, dict):
            if part not in current:
                raise SchemaParsingError(f"Reference path not found: {pointer_path}")
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError) as e:
                raise SchemaParsingError(f"Invalid array index in reference: {pointer_path}") from e
        else:
            raise SchemaParsingError(f"Cannot resolve reference in non-object/array: {pointer_path}")

    return current


def _extract_key_path(data: dict[str, Any], key_path: str) -> Any:
    """Extract data at a specific key path (dot-separated)."""
    keys = key_path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise SchemaParsingError(f"Key path '{key_path}' not found in included data")

    return current


def _transform_legacy_lock_types(schema_data: dict[str, Any]) -> dict[str, Any]:
    """Transform legacy lock type names to current format."""
    legacy_lock_mappings = {
        "exists": "exists",
        "equals": "equals",
        "not_equals": "not_equals",
        "greater_than": "greater_than",
        "less_than": "less_than",
        "contains": "contains",
        "regex": "regex_match",
        "regex_match": "regex_match",
        "in_list": "in_list",
        "not_in_list": "not_in_list",
        "custom": "custom",
    }

    def transform_locks_recursive(data):
        if isinstance(data, dict):
            if "type" in data and data["type"] in legacy_lock_mappings:
                data["type"] = legacy_lock_mappings[data["type"]]

            for value in data.values():
                transform_locks_recursive(value)
        elif isinstance(data, list):
            for item in data:
                transform_locks_recursive(item)

    result = schema_data.copy()
    transform_locks_recursive(result)
    return result


def _deep_merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with dict2 values taking precedence."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            # Override with new value
            result[key] = value

    return result


# Error handling and reporting utilities

class SchemaParsingError(Exception):
    """Exception raised for schema parsing errors with location information."""

    def __init__(self, message: str, file_path: str | None = None,
                 line: int | None = None, column: int | None = None):
        self.message = message
        self.file_path = file_path
        self.line = line
        self.column = column

        error_parts = [message]
        if file_path:
            error_parts.append(f"in file '{file_path}'")
        if line is not None:
            if column is not None:
                error_parts.append(f"at line {line}, column {column}")
            else:
                error_parts.append(f"at line {line}")

        super().__init__(" ".join(error_parts))


class SchemaValidationError(Exception):
    """Exception raised for schema validation errors."""

    def __init__(self, message: str, errors: list[str] | None = None,
                 file_path: str | None = None):
        self.message = message
        self.errors = errors or []
        self.file_path = file_path

        error_parts = [message]
        if file_path:
            error_parts.append(f"in file '{file_path}'")
        if self.errors:
            error_parts.append(f"Validation errors: {'; '.join(self.errors)}")

        super().__init__(" ".join(error_parts))


def format_parsing_error(error: Exception, context: str) -> str:
    """
    Format a parsing error with additional context information.

    Args:
        error: The original exception
        context: Additional context about where the error occurred

    Returns:
        Formatted error message with context

    Examples:
        >>> try:
        ...     # Some parsing operation
        ...     pass
        ... except Exception as e:
        ...     formatted = format_parsing_error(e, "while loading config.yaml")
    """
    base_message = str(error)

    if hasattr(error, 'file_path') and getattr(error, 'file_path', None):
        file_info = f" (file: {error.file_path}"
        if hasattr(error, 'line') and getattr(error, 'line', None):
            file_info += f", line: {error.line}"
            if hasattr(error, 'column') and getattr(error, 'column', None):
                file_info += f", column: {error.column}"
        file_info += ")"
        base_message += file_info

    return f"Error {context}: {base_message}"


def create_error_report(errors: list[Exception]) -> str:
    """
    Create a comprehensive error report from multiple errors.

    Args:
        errors: List of exceptions to include in the report

    Returns:
        Formatted error report string

    Examples:
        >>> errors = [ValueError("Invalid value"), TypeError("Wrong type")]
        >>> report = create_error_report(errors)
        >>> print(report)
    """
    if not errors:
        return "No errors to report."

    report_lines = [f"Error Report - {len(errors)} error(s) found:"]
    report_lines.append("-" * 50)

    for i, error in enumerate(errors, 1):
        error_type = type(error).__name__
        error_msg = str(error)

        report_lines.append(f"{i}. {error_type}: {error_msg}")

        # Add file location if available
        if hasattr(error, 'file_path') and getattr(error, 'file_path', None):
            location_info = f"   File: {error.file_path}"
            if hasattr(error, 'line') and getattr(error, 'line', None):
                location_info += f", Line: {error.line}"
                if hasattr(error, 'column') and getattr(error, 'column', None):
                    location_info += f", Column: {error.column}"
            report_lines.append(location_info)

        report_lines.append("")  # Empty line between errors

    return "\n".join(report_lines)


# Pydantic validation integration

def validate_with_pydantic(schema_data: dict[str, Any], model_class: type[BaseModel]) -> BaseModel:
    """
    Validate schema data using a pydantic model.

    Args:
        schema_data: Dictionary containing data to validate
        model_class: Pydantic model class to validate against

    Returns:
        Validated pydantic model instance

    Raises:
        SchemaValidationError: If validation fails

    Examples:
        >>> from pydantic import BaseModel
        >>> class ProcessModel(BaseModel):
        ...     name: str
        ...     version: str = "1.0"
        >>> data = {"name": "test_process"}
        >>> validated = validate_with_pydantic(data, ProcessModel)
    """
    try:
        return model_class(**schema_data)
    except ValidationError as e:
        errors = extract_validation_errors(e)
        raise SchemaValidationError(
            f"Pydantic validation failed for {model_class.__name__}",
            errors=errors
        ) from e


def extract_validation_errors(error: ValidationError) -> list[str]:
    """
    Extract validation error messages from a pydantic ValidationError.

    Args:
        error: Pydantic ValidationError instance

    Returns:
        List of formatted error messages

    Examples:
        >>> from pydantic import ValidationError
        >>> try:
        ...     # Some validation that fails
        ...     pass
        ... except ValidationError as e:
        ...     errors = extract_validation_errors(e)
    """
    error_messages = []

    for error_dict in error.errors():
        field_path = " -> ".join(str(loc) for loc in error_dict["loc"])
        error_type = error_dict["type"]
        message = error_dict["msg"]

        formatted_error = f"Field '{field_path}': {message} (type: {error_type})"
        error_messages.append(formatted_error)

    return error_messages


def format_validation_report(errors: list[str]) -> str:
    """
    Format a validation error report from a list of error messages.

    Args:
        errors: List of validation error messages

    Returns:
        Formatted validation report string

    Examples:
        >>> errors = ["Field 'name': required", "Field 'age': must be positive"]
        >>> report = format_validation_report(errors)
        >>> print(report)
    """
    if not errors:
        return "Validation successful - no errors found."

    report_lines = [f"Validation Report - {len(errors)} error(s) found:"]
    report_lines.append("-" * 50)

    for i, error in enumerate(errors, 1):
        report_lines.append(f"{i}. {error}")

    report_lines.append("-" * 50)
    report_lines.append("Please fix the above errors and try again.")

    return "\n".join(report_lines)

