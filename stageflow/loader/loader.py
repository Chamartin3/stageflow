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

# Note: Consistency issues are now accessed directly via process.issues
# and process.is_valid - no mapping to LoadError needed
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

        # Phase 3: Structure extraction (pass base_path for include resolution)
        process_config = self._extract_process_config(raw_data, errors, file_path.parent)
        if not process_config:
            return ProcessLoadResult(
                status=LoadResultStatus.STRUCTURE_ERROR,
                process=None,
                errors=errors,
                source=str(file_path),
            )

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

            # Collect validation warnings
            warnings: list[LoadError] = []
            if validator.has_warnings:
                warnings.extend(
                    [e for e in validator.errors if e.severity == ErrorSeverity.WARNING]
                )

            # Process is created - consistency issues are accessible via process.issues
            # and process.is_valid. No mapping needed.
            return ProcessLoadResult(
                status=LoadResultStatus.SUCCESS,
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
        self, raw_data: Any, errors: list[LoadError], base_path: Path | None = None
    ) -> dict[str, Any] | None:
        """
        Extract process configuration from raw file data.

        Handles both legacy format (process at root) and new format
        (process under "process" key). Also resolves $include directives
        for external stage files.

        Args:
            raw_data: Parsed YAML/JSON data
            errors: Error list to append to
            base_path: Base path for resolving relative includes

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
            # Resolve includes in stages
            if base_path and "stages" in process_config:
                process_config["stages"] = self._resolve_stage_includes(
                    process_config["stages"], base_path, errors
                )
            return process_config

        # Legacy format: process definition at root
        return raw_data

    def _resolve_stage_includes(
        self, stages: dict[str, Any], base_path: Path, errors: list[LoadError]
    ) -> dict[str, Any]:
        """
        Resolve $include directives in stage definitions.

        Supports:
        - stage_id: {$include: "path/to/stage.yaml"}
        - stage_id: {$include: "path/to/stage.yaml", ...extra_fields}

        Args:
            stages: Stages dictionary from process config
            base_path: Base path for resolving relative paths
            errors: Error list to append to

        Returns:
            Stages dictionary with includes resolved
        """
        resolved_stages: dict[str, Any] = {}
        yaml_parser = YAML()

        for stage_id, stage_def in stages.items():
            if not isinstance(stage_def, dict):
                resolved_stages[stage_id] = stage_def
                continue

            if "$include" in stage_def:
                include_path = base_path / stage_def["$include"]
                try:
                    if not include_path.exists():
                        errors.append(
                            LoadError(
                                error_type=LoadErrorType.FILE_NOT_FOUND,
                                severity=ErrorSeverity.FATAL,
                                message=f"Stage include file not found: {include_path}",
                                context={"stage": stage_id, "path": str(include_path)},
                            )
                        )
                        resolved_stages[stage_id] = stage_def
                        continue

                    with open(include_path, encoding="utf-8") as f:
                        file_format = self._detect_file_format(include_path)
                        if file_format == FileFormat.YAML:
                            included_data = yaml_parser.load(f)
                        else:
                            included_data = json.load(f)

                    if not isinstance(included_data, dict):
                        errors.append(
                            LoadError(
                                error_type=LoadErrorType.INVALID_FORMAT,
                                severity=ErrorSeverity.FATAL,
                                message=f"Stage include must be a dictionary: {include_path}",
                                context={"stage": stage_id, "path": str(include_path)},
                            )
                        )
                        resolved_stages[stage_id] = stage_def
                        continue

                    # Merge included data with any extra fields (except $include)
                    merged = dict(included_data)
                    for key, value in stage_def.items():
                        if key != "$include":
                            merged[key] = value

                    resolved_stages[stage_id] = merged

                except Exception as e:
                    errors.append(
                        LoadError(
                            error_type=LoadErrorType.FILE_ENCODING_ERROR,
                            severity=ErrorSeverity.FATAL,
                            message=f"Failed to load stage include: {e}",
                            context={"stage": stage_id, "path": str(include_path)},
                        )
                    )
                    resolved_stages[stage_id] = stage_def
            else:
                resolved_stages[stage_id] = stage_def

        return resolved_stages
