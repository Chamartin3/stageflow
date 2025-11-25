"""
Improved process loader with comprehensive error handling.

This loader provides:
- Unified ProcessLoadResult for all operations
- Comprehensive error collection
- Support for both file and registry sources
- JSON-serializable results
"""

import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stageflow.models import (
    ErrorSeverity,
    FileFormat,
    LoadError,
    LoadErrorType,
    LoadResultStatus,
    ProcessLoadResult,
    ProcessSourceType,
)
from stageflow.process import Process

from .validators import (
    ProcessConfigValidator,
)


class ProcessLoader:
    """
    Process loader with unified error handling and result reporting.

    This loader uses validator models to check configuration structures and
    returns a unified ProcessLoadResult for all operations.
    """

    def __init__(self):
        """Initialize process loader."""
        pass

    def load(self, source: str | Path) -> ProcessLoadResult:
        """
        Load process from file or registry.

        This is the main entry point for loading processes. It automatically
        detects the source type and delegates to the appropriate loader.

        Args:
            source: File path or registry identifier (e.g., "@my_process")

        Returns:
            ProcessLoadResult with status, process (if successful), and errors
        """
        source_str = str(source)
        source_type = self.detect_source_type(source_str)

        if source_type == ProcessSourceType.FILE:
            return self._load_from_file(Path(source_str))
        else:
            return self._load_from_registry(source_str)

    def detect_source_type(self, source: str) -> ProcessSourceType:
        """
        Detect whether source is a file or registry reference.

        Args:
            source: Source string to check

        Returns:
            ProcessSourceType.FILE or ProcessSourceType.REGISTRY
        """
        if source.startswith("@"):
            return ProcessSourceType.REGISTRY
        return ProcessSourceType.FILE

    def _load_from_file(self, file_path: Path) -> ProcessLoadResult:
        """
        Load process from file with comprehensive error handling.

        Args:
            file_path: Path to process definition file

        Returns:
            ProcessLoadResult with status and errors
        """
        errors: list[LoadError] = []

        # Phase 1: File access
        if not file_path.exists():
            errors.append(
                LoadError(
                    error_type=LoadErrorType.FILE_NOT_FOUND,
                    severity=ErrorSeverity.FATAL,
                    message=f"Process file not found: {file_path}",
                    context={"path": str(file_path)},
                )
            )
            return ProcessLoadResult(
                status=LoadResultStatus.FILE_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

        # Phase 2: File parsing
        try:
            file_format = self._detect_file_format(file_path)
            with open(file_path, encoding="utf-8") as f:
                if file_format == FileFormat.YAML:
                    yaml_parser = YAML()
                    raw_data = yaml_parser.load(f)
                elif file_format == FileFormat.JSON:
                    raw_data = json.load(f)
                else:
                    errors.append(
                        LoadError(
                            error_type=LoadErrorType.INVALID_FORMAT,
                            severity=ErrorSeverity.FATAL,
                            message=f"Unsupported file format: {file_path.suffix}",
                            context={
                                "path": str(file_path),
                                "suffix": file_path.suffix,
                            },
                        )
                    )
                    return ProcessLoadResult(
                        status=LoadResultStatus.PARSE_ERROR,
                        process=None,
                        errors=errors,
                        source=str(file_path),
                    )
        except json.JSONDecodeError as e:
            errors.append(
                LoadError(
                    error_type=LoadErrorType.JSON_PARSE_ERROR,
                    severity=ErrorSeverity.FATAL,
                    message=f"JSON parsing failed: {e}",
                    context={
                        "path": str(file_path),
                        "line": e.lineno,
                        "column": e.colno,
                        "exception": str(e),
                    },
                )
            )
            return ProcessLoadResult(
                status=LoadResultStatus.PARSE_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )
        except Exception as e:
            errors.append(
                LoadError(
                    error_type=LoadErrorType.FILE_ENCODING_ERROR,
                    severity=ErrorSeverity.FATAL,
                    message=f"Failed to read file: {e}",
                    context={"path": str(file_path), "exception": str(e)},
                )
            )
            return ProcessLoadResult(
                status=LoadResultStatus.FILE_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

        # Phase 3: Structure extraction
        process_config = self._extract_process_config(raw_data, errors)
        if not process_config:
            return ProcessLoadResult(
                status=LoadResultStatus.STRUCTURE_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

        # Phase 3.5: Preprocess schema sections
        self._preprocess_schemas(process_config)

        # Phase 4: Configuration validation
        validator = ProcessConfigValidator(process_config)
        if not validator.is_valid:
            errors.extend(validator.errors)

        # Check for fatal errors
        if validator.has_fatal_errors:
            return ProcessLoadResult(
                status=LoadResultStatus.VALIDATION_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

        # Phase 5: Process instantiation
        try:
            process = Process(process_config)  # type: ignore[arg-type]

            # Check for consistency warnings
            warnings: list[LoadError] = []
            if validator.has_warnings:
                warnings.extend(
                    [e for e in validator.errors if e.severity == ErrorSeverity.WARNING]
                )

            # Collect consistency issues from the process
            if process.consistency_issues:
                for issue in process.consistency_issues:
                    # Convert ConsistencyIssue to LoadError
                    severity = ErrorSeverity.WARNING if issue.severity == "warning" else ErrorSeverity.INFO
                    if issue.severity == "fatal":
                        severity = ErrorSeverity.FATAL

                    # Map ProcessIssueTypes to LoadErrorType
                    from stageflow.models.consistency import ProcessIssueTypes

                    error_type_map = {
                        ProcessIssueTypes.MISSING_STAGE: LoadErrorType.MISSING_STAGE_REFERENCE,
                        ProcessIssueTypes.INVALID_TRANSITION: LoadErrorType.INVALID_TRANSITION,
                        ProcessIssueTypes.DEAD_END_STAGE: LoadErrorType.UNREACHABLE_STAGE,
                        ProcessIssueTypes.UNREACHABLE_STAGE: LoadErrorType.UNREACHABLE_STAGE,
                        ProcessIssueTypes.ORPHANED_STAGE: LoadErrorType.ORPHANED_STAGE,
                        ProcessIssueTypes.CIRCULAR_DEPENDENCY: LoadErrorType.CIRCULAR_DEPENDENCY,
                        ProcessIssueTypes.LOGICAL_CONFLICT: LoadErrorType.VALIDATION_ERROR,
                        ProcessIssueTypes.MULTIPLE_GATES_SAME_TARGET: LoadErrorType.VALIDATION_ERROR,
                        ProcessIssueTypes.SELF_REFERENCING_GATE: LoadErrorType.CIRCULAR_DEPENDENCY,
                        ProcessIssueTypes.INFINITE_CYCLE: LoadErrorType.CIRCULAR_DEPENDENCY,
                        ProcessIssueTypes.UNCONTROLLED_CYCLE: LoadErrorType.CIRCULAR_DEPENDENCY,
                        ProcessIssueTypes.CONTROLLED_CYCLE: LoadErrorType.CIRCULAR_DEPENDENCY,
                    }

                    error_type = error_type_map.get(issue.issue_type, LoadErrorType.VALIDATION_ERROR)

                    warnings.append(
                        LoadError(
                            error_type=error_type,
                            severity=severity,
                            message=issue.description,
                            context={
                                "issue_type": issue.issue_type,
                                "stages": issue.stages,
                                "details": issue.details if hasattr(issue, "details") else {},
                            },
                        )
                    )

            # Determine final status
            if warnings:
                status = LoadResultStatus.CONSISTENCY_WARNING
            else:
                status = LoadResultStatus.SUCCESS

            return ProcessLoadResult(
                status=status,
                process=process,
                errors=[],
                warnings=warnings,
                source=str(file_path),
            )

        except ValueError as e:
            # Categorize ValueError based on message content
            error_msg = str(e).lower()
            if "lock" in error_msg:
                error_type = LoadErrorType.INVALID_LOCK_DEFINITION
            elif "gate" in error_msg:
                error_type = LoadErrorType.INVALID_GATE_DEFINITION
            elif "stage" in error_msg:
                error_type = LoadErrorType.INVALID_STAGE_DEFINITION
            else:
                error_type = LoadErrorType.VALIDATION_ERROR

            errors.append(
                LoadError(
                    error_type=error_type,
                    severity=ErrorSeverity.FATAL,
                    message=f"Validation error: {e}",
                    context={"exception_type": "ValueError", "exception": str(e)},
                )
            )
            return ProcessLoadResult(
                status=LoadResultStatus.VALIDATION_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )
        except Exception as e:
            # Catch any other unexpected errors
            errors.append(
                LoadError(
                    error_type=LoadErrorType.VALIDATION_ERROR,
                    severity=ErrorSeverity.FATAL,
                    message=f"Unexpected error creating Process instance: {e}",
                    context={"exception_type": type(e).__name__, "exception": str(e)},
                )
            )
            return ProcessLoadResult(
                status=LoadResultStatus.VALIDATION_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

    def _load_from_registry(self, registry_id: str) -> ProcessLoadResult:
        """
        Load process from registry.

        Args:
            registry_id: Registry identifier (e.g., "@my_process")

        Returns:
            ProcessLoadResult with status and errors
        """
        # Registry loading not yet implemented
        errors = [
            LoadError(
                error_type=LoadErrorType.FILE_NOT_FOUND,
                severity=ErrorSeverity.FATAL,
                message=f"Registry loading not yet implemented: {registry_id}",
                context={"registry_id": registry_id},
            )
        ]
        return ProcessLoadResult(
            status=LoadResultStatus.FILE_ERROR,
            process=None,
            errors=errors,
            source=registry_id,
        )

    def _detect_file_format(self, file_path: Path) -> FileFormat:
        """
        Detect file format from extension.

        Args:
            file_path: Path to file

        Returns:
            FileFormat enum value
        """
        suffix = file_path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            return FileFormat.YAML
        elif suffix == ".json":
            return FileFormat.JSON
        else:
            # Default to YAML
            return FileFormat.YAML

    def _extract_process_config(
        self, raw_data: Any, errors: list[LoadError]
    ) -> dict[str, Any] | None:
        """
        Extract process configuration from raw file data.

        Handles both legacy format (process at root) and new format
        (process under "process" key).

        Args:
            raw_data: Parsed YAML/JSON data
            errors: Error list to append to

        Returns:
            Process configuration dict or None if extraction failed
        """
        if not isinstance(raw_data, dict):
            errors.append(
                LoadError(
                    error_type=LoadErrorType.INVALID_FORMAT,
                    severity=ErrorSeverity.FATAL,
                    message=f"Process file must contain a dictionary, got {type(raw_data).__name__}",
                    context={"actual_type": type(raw_data).__name__},
                )
            )
            return None

        # Check for new format: {"process": {...}}
        if "process" in raw_data:
            process_config = raw_data["process"]
            if not isinstance(process_config, dict):
                errors.append(
                    LoadError(
                        error_type=LoadErrorType.INVALID_FORMAT,
                        severity=ErrorSeverity.FATAL,
                        message=f"'process' field must be a dictionary, got {type(process_config).__name__}",
                        context={"actual_type": type(process_config).__name__},
                    )
                )
                return None
            return process_config

        # Legacy format: process definition at root
        return raw_data

    def _preprocess_schemas(self, process_config: dict[str, Any]) -> None:
        """
        Preprocess stage schemas to convert schema.required_fields into expected_properties.

        This allows stages to use the simpler required_fields syntax:
            schema:
              required_fields:
                - email
                - address.city

        Which gets converted to expected_properties:
            expected_properties:
              email: {type: "string"}
              address:
                city: {type: "string"}

        Args:
            process_config: Process configuration dict (modified in place)
        """
        stages = process_config.get("stages", {})
        if not isinstance(stages, dict):
            return

        for _stage_id, stage_config in stages.items():
            if not isinstance(stage_config, dict):
                continue

            # Ensure schema section exists
            if "schema" not in stage_config:
                stage_config["schema"] = {}

            schema_section = stage_config["schema"]
            if not isinstance(schema_section, dict):
                stage_config["schema"] = {}
                schema_section = stage_config["schema"]

            required_fields = schema_section.get("required_fields", [])
            if not required_fields:
                continue

            # Convert required_fields list to expected_properties dict
            expected_props = stage_config.get("expected_properties", {})
            if not isinstance(expected_props, dict):
                expected_props = {}

            for field_path in required_fields:
                if not isinstance(field_path, str):
                    continue

                # Add to expected_properties with default string type
                self._add_nested_property(expected_props, field_path)

            # Update stage config
            stage_config["expected_properties"] = expected_props

    def _add_nested_property(
        self, expected_props: dict[str, Any], field_path: str
    ) -> None:
        """
        Add a nested property to expected_properties structure.

        Handles dot notation (e.g., "address.city") and array indices (e.g., "items[0].id").

        Creates nested containers for intermediate properties:
            "address.city" -> {"address": {"city": {"type": "string"}}}
            "items[0].id" -> {"items": {"id": {"type": "string"}}}

        Args:
            expected_props: Expected properties dict (modified in place)
            field_path: Property path to add
        """
        import re

        if expected_props is None:
            return

        # Parse the path
        parts = field_path.split(".")
        current = expected_props

        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1

            # Check for array indexing - remove [index] notation
            match = re.match(r"^([^\[]+)(\[\d+\])?$", part)
            if not match:
                continue

            prop_name = match.group(1)
            # has_array_index = match.group(2) is not None

            if is_last:
                # Last part - add as string type property
                if prop_name not in current:
                    current[prop_name] = {"type": "string"}
            else:
                # Intermediate part - ensure it exists as a container (no type definition)
                if prop_name not in current:
                    current[prop_name] = {}
                elif self._is_leaf_property(current[prop_name]):
                    # It's a leaf property but we need to nest further
                    # This is a conflict - convert it to a container
                    current[prop_name] = {}

                # Navigate deeper
                if isinstance(current[prop_name], dict):
                    current = current[prop_name]
                else:
                    break

    def _is_leaf_property(self, prop_def: Any) -> bool:
        """Check if a property definition is a leaf (has type) vs a container.

        A leaf property looks like: {"type": "string"}
        A container looks like: {"city": {"type": "string"}} or {"type": {"type": "string"}}

        Args:
            prop_def: Property definition to check

        Returns:
            True if it's a leaf property with a type definition
        """
        if not isinstance(prop_def, dict):
            return False

        # Check if it has a "type" key with a string value (not a nested dict)
        if "type" in prop_def and isinstance(prop_def["type"], str):
            return True

        return False
