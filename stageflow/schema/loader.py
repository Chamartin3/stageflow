"""Simple file loader for StageFlow that creates Process objects directly."""

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stageflow.element import Element, create_element
from stageflow.gate import GateDefinition
from stageflow.lock import (
    LockType,
)
from stageflow.process import Process, ProcessDefinition
from stageflow.stage import (
    StageDefinition,
)


class LoadError(Exception):
    """Exception raised when loading fails."""

    pass


class LoaderValidationError(Exception):
    """Exception raised during validation within the loader conversion process."""

    pass


class ConfigValidationError(Exception):
    """
    Exception raised when process configuration validation fails.

    This exception collects all validation errors encountered during
    configuration parsing and validation, allowing for comprehensive
    error reporting.
    """

    def __init__(self, errors: list[str], config: dict[str, Any] | None = None):
        """
        Initialize with a list of validation errors.

        Args:
            errors: List of validation error messages
            config: Optional raw configuration that failed validation
        """
        self.errors = errors
        self.config = config
        self.error_count = len(errors)

        # Create a formatted error message
        if self.error_count == 1:
            message = f"Configuration validation failed with 1 error:\n  • {errors[0]}"
        else:
            error_list = "\n  • ".join(errors)
            message = f"Configuration validation failed with {self.error_count} errors:\n  • {error_list}"

        super().__init__(message)

    def get_error_summary(self) -> str:
        """Get a formatted summary of all errors."""
        if self.error_count == 1:
            return f"1 validation error: {self.errors[0]}"
        return f"{self.error_count} validation errors:\n" + "\n".join(
            f"  {i+1}. {error}" for i, error in enumerate(self.errors)
        )


@dataclass
class ProcessWithErrors:
    """Container for processes that failed validation but still need to be workable."""

    name: str
    description: str
    file_path: str | Path
    raw_config: dict
    validation_errors: list[str]
    partial_process: "Process | None" = None

    @property
    def valid(self) -> bool:
        return len(self.validation_errors) == 0

    def get_error_summary(self) -> str:
        """Get a human-readable summary of validation errors."""
        if not self.validation_errors:
            return "No errors"
        return f"{len(self.validation_errors)} validation error(s):\n" + "\n".join(
            f"     • {error}" for error in self.validation_errors
        )


class FileReader:
    """Simple file reading abstraction with format detection."""

    @staticmethod
    def read_file(file_path: str | Path) -> dict:
        """
        Read and parse file content based on extension.

        Returns:
            Parsed file content as dictionary

        Raises:
            LoadError: For I/O or parsing errors
        """
        file_path = Path(file_path)

        # Handle relative paths: use STAGEFLOW_ACTUAL_CWD if set (for CLI wrapper),
        # otherwise resolve relative to current working directory
        if not file_path.is_absolute():
            actual_cwd = os.environ.get("STAGEFLOW_ACTUAL_CWD")
            if actual_cwd:
                file_path = Path(actual_cwd) / file_path
            else:
                file_path = file_path.resolve()

        if not file_path.exists():
            raise LoadError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                suffix = file_path.suffix.lower()
                if suffix in [".yml", ".yaml"]:
                    try:
                        return FileReader._parse_yaml(f)
                    except Exception as e:
                        raise LoadError(
                            f"Error parsing YAML in {file_path}: {e}"
                        ) from e
                elif suffix == ".json":
                    try:
                        return FileReader._parse_json(f)
                    except json.JSONDecodeError as e:
                        raise LoadError(
                            f"Error parsing JSON in {file_path}: {e}"
                        ) from e
                else:
                    raise LoadError(f"Unsupported file format: {file_path.suffix}")

        except PermissionError as e:
            raise LoadError(f"Permission denied reading {file_path}") from e
        except UnicodeDecodeError as e:
            raise LoadError(f"Encoding error reading {file_path}: {e}") from e

    @staticmethod
    def _parse_yaml(file_handle) -> dict:
        """Parse YAML content."""
        yaml = YAML(typ="safe", pure=True)
        return yaml.load(file_handle)

    @staticmethod
    def _parse_json(file_handle) -> dict:
        """Parse JSON content."""
        return json.load(file_handle)


def load_process(file_path: str | Path) -> Process:
    """
    Load a Process from a YAML or JSON file.

    The file can contain either:
    1. New format: {'process': {...process definition...}}
    2. Legacy format: {...process definition directly at root...}

    All validation is handled by the Process constructor.

    Args:
        file_path: Path to the process definition file

    Returns:
        Process object

    Raises:
        LoadError: If file cannot be loaded or parsed
    """
    try:
        # Use FileReader for clean I/O separation
        data = FileReader.read_file(file_path)

        if not isinstance(data, dict):
            raise LoadError("File must contain a dictionary")

        # Handle both new format with 'process' key and legacy format without it
        if "process" in data:
            # New format: {'process': {...process definition...}}
            process_config = data["process"]
        else:
            # Legacy format: {...process definition directly at root...}
            # Check if this looks like a process definition by checking for required fields
            required_process_fields = ["name", "stages", "initial_stage", "final_stage"]
            if all(field in data for field in required_process_fields):
                process_config = data
            else:
                available_keys = list(data.keys())
                raise LoadError(
                    f"File must contain either a 'process' key or process definition at root level. "
                    f"Found keys: {available_keys}. Missing required process fields: "
                    f"{[f for f in required_process_fields if f not in data]}. "
                    f"If this is element data, use load_element() instead."
                )

        # Convert YAML format to internal format
        converted_config = _convert_process_config(process_config)

        # Let Process handle its own validation and error reporting
        return Process(converted_config)

    except ConfigValidationError as e:
        # Convert ConfigValidationError to LoadError with detailed message
        raise LoadError(f"Failed to load {file_path}: {e.get_error_summary()}") from e
    except Exception as e:
        if isinstance(e, LoadError):
            raise
        raise LoadError(f"Failed to load {file_path}: {e}") from e


def load_process_graceful(file_path: str | Path) -> Process | ProcessWithErrors:
    """
    Load a Process with graceful error handling.

    Unlike load_process(), this function will return a ProcessWithErrors object
    for processes that have validation issues, allowing users to see what's wrong
    and potentially edit the file to fix issues.

    Args:
        file_path: Path to the process definition file

    Returns:
        Process object if valid, ProcessWithErrors if invalid but parseable

    Raises:
        LoadError: Only for file I/O or severe parsing errors
    """
    try:
        # First try normal loading
        return load_process(file_path)
    except LoadError as e:
        # Check if this was caused by ConfigValidationError
        if e.__cause__ and isinstance(e.__cause__, ConfigValidationError):
            # Extract ConfigValidationError for detailed error handling
            config_error = e.__cause__

            try:
                # Try to load the raw config for ProcessWithErrors
                data = FileReader.read_file(file_path)

                if not isinstance(data, dict):
                    raise  # Re-raise original error for parsing issues

                # Handle both new format with 'process' key and legacy format without it
                if "process" in data:
                    process_config = data["process"]
                else:
                    required_process_fields = [
                        "name",
                        "stages",
                        "initial_stage",
                        "final_stage",
                    ]
                    if all(field in data for field in required_process_fields):
                        process_config = data
                    else:
                        raise  # Re-raise original error

                # Extract basic info
                name = process_config.get("name", "Unknown Process")
                description = process_config.get("description", "")

                # Use errors from ConfigValidationError
                return ProcessWithErrors(
                    name=name,
                    description=description,
                    file_path=file_path,
                    raw_config=process_config,
                    validation_errors=config_error.errors,
                )

            except Exception:
                # If graceful handling fails, re-raise original error
                raise e from None

        # Check for other validation patterns we can handle gracefully
        elif "not found in stages definition" in str(e) or "must have" in str(e):
            try:
                # Try to load the raw config for analysis
                data = FileReader.read_file(file_path)

                if not isinstance(data, dict):
                    raise  # Re-raise original error for parsing issues

                # Handle both new format with 'process' key and legacy format without it
                if "process" in data:
                    process_config = data["process"]
                else:
                    required_process_fields = [
                        "name",
                        "stages",
                        "initial_stage",
                        "final_stage",
                    ]
                    if all(field in data for field in required_process_fields):
                        process_config = data
                    else:
                        raise  # Re-raise original error

                # Extract basic info
                name = process_config.get("name", "Unknown Process")
                description = process_config.get("description", "")

                # Parse error message to extract validation errors
                errors = [str(e).replace(f"Failed to load {file_path}: ", "")]

                return ProcessWithErrors(
                    name=name,
                    description=description,
                    file_path=file_path,
                    raw_config=process_config,
                    validation_errors=errors,
                )

            except Exception:
                # If graceful handling fails, re-raise original error
                raise e from None
        else:
            # Re-raise for non-validation errors
            raise


def load_element(file_path: str | Path) -> Element:
    """
    Load an Element from a JSON file.

    The file should contain element data as a JSON object.
    Element validation is handled by the Element constructor.

    Args:
        file_path: Path to the element data file

    Returns:
        Element instance

    Raises:
        LoadError: If file cannot be loaded or parsed
    """
    try:
        # Use FileReader for clean I/O separation
        data = FileReader.read_file(file_path)

        if not isinstance(data, dict):
            raise LoadError("Element data must be a dictionary")

        # Let Element handle its own validation and error reporting
        return create_element(data)

    except Exception as e:
        if isinstance(e, LoadError):
            raise
        raise LoadError(f"Element validation failed: {e}") from e


class Loader:
    """Central loader class for StageFlow data types."""

    @classmethod
    def process(cls, file_path: str | Path) -> Process:
        """
        Load process definition from YAML/JSON file.

        Args:
            file_path: Path to the process definition file

        Returns:
            Process instance

        Raises:
            LoadError: If file cannot be loaded or parsed
        """
        return load_process(file_path)

    @classmethod
    def element(cls, file_path: str | Path) -> Element:
        """
        Load element data from JSON file.

        Args:
            file_path: Path to the element data file

        Returns:
            Element instance

        Raises:
            LoadError: If file cannot be loaded or parsed
        """
        return load_element(file_path)


class ProcessSourceType(Enum):
    """
    Enum representing the type of source for process loading.

    Attributes:
        FILE: Process is loaded from a file path
        REGISTRY: Process is loaded from a registry reference (prefixed with '@')
    """
    FILE = "file"
    REGISTRY = "registry"


class ProcessLoader:
    """
    Unified process loader that handles both file paths and registry references.

    This class provides a consistent interface for loading processes from different sources:
    - Direct file paths (YAML/JSON files)
    - Registry references (prefixed with '@')

    Example:
        # Load from file
        loader = ProcessLoader()
        process = loader.load("path/to/process.yaml")

        # Load from registry
        process = loader.load("@my_process")

        # Load with graceful error handling
        result = loader.load("process.yaml", graceful=True)
        if isinstance(result, ProcessWithErrors):
            print(result.get_error_summary())
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the ProcessLoader.

        Args:
            verbose: Whether to output progress messages during loading
        """
        self.verbose = verbose
        self._registry = None

    def detect_source_type(self, source: str) -> ProcessSourceType:
        """
        Detect whether source is a file path or registry reference.

        Args:
            source: The source string to analyze

        Returns:
            ProcessSourceType.FILE or ProcessSourceType.REGISTRY
        """
        if source.startswith("@"):
            return ProcessSourceType.REGISTRY
        return ProcessSourceType.FILE

    def load(
        self,
        source: str,
        graceful: bool = False
    ) -> Process | ProcessWithErrors:
        """
        Load a process from either a file path or registry reference.

        Args:
            source: File path or registry reference (prefixed with '@')
            graceful: If True, return ProcessWithErrors for validation errors
                     instead of raising exceptions

        Returns:
            Process instance if valid, ProcessWithErrors if graceful=True and invalid

        Raises:
            LoadError: If file/registry cannot be accessed or parsing fails (unless graceful=True)
        """
        source_type = self.detect_source_type(source)

        if source_type == ProcessSourceType.FILE:
            return self._load_from_file(source, graceful)
        else:
            return self._load_from_registry(source, graceful)

    def _load_from_file(
        self,
        file_path: str,
        graceful: bool
    ) -> Process | ProcessWithErrors:
        """Load process from a file path."""
        if self.verbose:
            self._show_progress(f"Loading process from file: {file_path}")

        if graceful:
            return load_process_graceful(file_path)
        return load_process(file_path)

    def _load_from_registry(
        self,
        source: str,
        graceful: bool
    ) -> Process | ProcessWithErrors:
        """Load process from registry reference."""
        from stageflow.manager import ManagerConfig, ProcessRegistry

        process_name = source[1:]  # Remove @ prefix

        if self.verbose:
            self._show_progress(f"Loading process from registry: {process_name}")

        try:
            # Lazy initialize registry
            if self._registry is None:
                config = ManagerConfig.from_env()
                self._registry = ProcessRegistry(config)

            # Get process file path from registry
            process_file_path = self._registry.get_process_file_path(process_name)

            if not process_file_path or not process_file_path.exists():
                raise LoadError(f"Process '{process_name}' not found in registry")

            # Load the process file
            if graceful:
                return load_process_graceful(process_file_path)
            return load_process(process_file_path)

        except Exception as e:
            if isinstance(e, LoadError):
                raise
            raise LoadError(f"Failed to load process from registry: {e}") from e

    def _show_progress(self, message: str) -> None:
        """Show progress message if verbose mode is enabled."""
        if self.verbose:
            # Simple print for now - CLI can override this with rich formatting
            print(f"[ProcessLoader] {message}")


class ProcessConfigParser:
    """
    Parser and validator for process configuration dictionaries.

    This class handles the conversion of raw YAML/JSON configuration into
    validated ProcessDefinition format. It collects all validation errors
    rather than throwing immediately, allowing for comprehensive error reporting.

    Example:
        parser = ProcessConfigParser(config)
        try:
            process_def = parser.parse_and_validate()
        except ConfigValidationError as e:
            print(f"Found {e.error_count} errors:")
            for error in e.errors:
                print(f"  - {error}")
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize parser with configuration dictionary.

        Args:
            config: Raw configuration dictionary from YAML/JSON
                   Must contain at minimum: name, stages, initial_stage, final_stage
        """
        self.config = config
        self.errors: list[str] = []

    def parse_and_validate(self) -> ProcessDefinition:
        """
        Parse and validate the configuration.

        Returns:
            ProcessDefinition if validation succeeds

        Raises:
            ConfigValidationError: If validation fails with collected errors
        """
        # Always validate basic structure
        self._validate_basic_structure()

        # If basic validation failed, stop here
        if self.errors:
            raise ConfigValidationError(self.errors, self.config)

        # Convert configuration
        converted = self._convert_config()

        # Final validation
        if self.errors:
            raise ConfigValidationError(self.errors, self.config)

        return converted  # type: ignore

    def _validate_basic_structure(self) -> None:
        """Validate basic process structure requirements."""
        required_fields = ["name", "stages", "initial_stage", "final_stage"]

        for field in required_fields:
            if field not in self.config:
                self.errors.append(
                    f"Required field '{field}' is missing from process definition"
                )

        # Validate field types if present
        if "name" in self.config:
            if not isinstance(self.config["name"], str) or not self.config["name"].strip():
                self.errors.append("Process 'name' must be a non-empty string")

        if "initial_stage" in self.config:
            if (
                not isinstance(self.config["initial_stage"], str)
                or not self.config["initial_stage"].strip()
            ):
                self.errors.append("Process 'initial_stage' must be a non-empty string")

        if "final_stage" in self.config:
            if (
                not isinstance(self.config["final_stage"], str)
                or not self.config["final_stage"].strip()
            ):
                self.errors.append("Process 'final_stage' must be a non-empty string")

        # Validate stage_prop if present
        if "stage_prop" in self.config:
            if (
                not isinstance(self.config["stage_prop"], str)
                or not self.config["stage_prop"].strip()
            ):
                self.errors.append("Process 'stage_prop' must be a non-empty string")

    def _convert_config(self) -> dict[str, Any]:
        """Convert configuration to ProcessDefinition format."""
        converted: dict[str, Any] = dict(self.config)

        # Pass through stage_prop if present
        if "stage_prop" in self.config:
            converted["stage_prop"] = self.config["stage_prop"]

        # Convert stages
        if "stages" in self.config:
            if not isinstance(self.config["stages"], dict):
                self.errors.append("'stages' must be a dictionary with stage IDs as keys")
            else:
                converted_stages: dict[str, StageDefinition] = {}
                for stage_id, stage_data in self.config["stages"].items():
                    if not isinstance(stage_data, dict):
                        self.errors.append(f"Stage '{stage_id}' must be a dictionary")
                        continue

                    converted_stage = self._convert_stage(stage_id, stage_data)
                    if converted_stage:
                        converted_stages[stage_id] = converted_stage

                converted["stages"] = converted_stages

        # Note: Stage reference validation (checking if initial_stage and final_stage
        # exist in the stages dict) is intentionally NOT done here. This validation
        # is handled by the Process class itself, which treats these as "consistency errors"
        # rather than "structural errors". This allows processes with invalid references
        # to still be loaded and viewed (with warnings) rather than failing completely.

        # Add description if missing
        if "description" not in converted:
            converted["description"] = ""

        return converted

    def _convert_stage(
        self, stage_id: str, stage_data: dict[str, Any]
    ) -> StageDefinition | None:
        """Convert and validate stage configuration."""
        converted_stage = dict(stage_data)

        # Add name field
        if "name" not in converted_stage:
            converted_stage["name"] = stage_id

        # Validate and convert gates
        if "gates" in converted_stage:
            gates_data = converted_stage["gates"]
            converted_gates = self._convert_gates(stage_id, gates_data)
            converted_stage["gates"] = converted_gates
        else:
            converted_stage["gates"] = []

        # Add default fields with proper types
        if "description" not in converted_stage:
            converted_stage["description"] = ""
        if "expected_actions" not in converted_stage:
            converted_stage["expected_actions"] = []
        if "expected_properties" not in converted_stage:
            converted_stage["expected_properties"] = None
        if "is_final" not in converted_stage:
            converted_stage["is_final"] = False

        # Validate expected_actions if present and properly structured
        if converted_stage["expected_actions"]:
            if all(
                isinstance(action, dict) for action in converted_stage["expected_actions"]
            ):
                self._validate_expected_actions(
                    converted_stage["expected_actions"], stage_id
                )

        # Validate expected_properties if present
        if converted_stage["expected_properties"] is not None:
            self._validate_expected_properties(
                converted_stage["expected_properties"], stage_id
            )

        return converted_stage  # type: ignore

    def _convert_gates(
        self, stage_id: str, gates_data: Any
    ) -> list[GateDefinition]:
        """Convert and validate gates configuration."""
        gates_list: list[GateDefinition] = []

        if isinstance(gates_data, dict):
            # Convert dict format to list format
            for gate_name, gate_config in gates_data.items():
                if not isinstance(gate_config, dict):
                    self.errors.append(
                        f"Gate '{gate_name}' in stage '{stage_id}' must be a dictionary"
                    )
                    continue

                gate_def = dict(gate_config)
                gate_def["name"] = gate_name
                gate_def["parent_stage"] = stage_id

                if "description" not in gate_def:
                    gate_def["description"] = ""

                if "locks" not in gate_def:
                    self.errors.append(
                        f"Gate '{gate_name}' in stage '{stage_id}' must have 'locks' field"
                    )
                    continue

                gate_def["locks"] = self._convert_locks(
                    gate_def["locks"], gate_name, stage_id
                )
                self._validate_gate(gate_def, stage_id)
                gates_list.append(gate_def)  # type: ignore

        elif isinstance(gates_data, list):
            # Already a list, validate each gate
            for i, gate_config in enumerate(gates_data):
                if not isinstance(gate_config, dict):
                    self.errors.append(
                        f"Gate {i} in stage '{stage_id}' must be a dictionary"
                    )
                    continue

                gate_def = dict(gate_config)
                if "parent_stage" not in gate_def:
                    gate_def["parent_stage"] = stage_id
                if "description" not in gate_def:
                    gate_def["description"] = ""

                if "name" not in gate_def:
                    self.errors.append(
                        f"Gate {i} in stage '{stage_id}' must have a 'name' field"
                    )
                    continue

                if "locks" not in gate_def:
                    self.errors.append(
                        f"Gate '{gate_def['name']}' in stage '{stage_id}' must have 'locks' field"
                    )
                    continue

                gate_def["locks"] = self._convert_locks(
                    gate_def["locks"], gate_def["name"], stage_id
                )
                self._validate_gate(gate_def, stage_id)
                gates_list.append(gate_def)  # type: ignore
        else:
            self.errors.append(
                f"Gates in stage '{stage_id}' must be a dictionary or list"
            )

        return gates_list

    def _convert_locks(
        self, locks_data: Any, gate_name: str, stage_id: str
    ) -> list[dict[str, Any]]:
        """Convert and validate locks configuration."""
        if not isinstance(locks_data, list):
            self.errors.append(
                f"Locks in gate '{gate_name}' (stage '{stage_id}') must be a list"
            )
            return []

        converted_locks: list[dict[str, Any]] = []

        for i, lock_config in enumerate(locks_data):
            if not isinstance(lock_config, dict):
                self.errors.append(
                    f"Lock {i} in gate '{gate_name}' (stage '{stage_id}') must be a dictionary"
                )
                continue

            validated_lock = self._validate_lock(lock_config, i, gate_name, stage_id)
            if validated_lock:
                converted_locks.append(validated_lock)

        return converted_locks

    def _validate_lock(
        self, lock_config: dict[str, Any], lock_index: int, gate_name: str, stage_id: str
    ) -> dict[str, Any] | None:
        """Validate a single lock definition."""
        location = f"lock {lock_index} in gate '{gate_name}' (stage '{stage_id}')"

        # Define shorthand keys
        shorthand_keys = {
            "exists", "equals", "greater_than", "less_than", "contains",
            "regex", "type_check", "range", "length", "not_empty",
            "in_list", "not_in_list", "is_true", "is_false"
        }

        # Check for shorthand format
        provided_shorthand_keys = set(lock_config.keys()) & shorthand_keys

        if provided_shorthand_keys:
            if len(provided_shorthand_keys) != 1:
                self.errors.append(
                    f"Shorthand lock at {location} must have exactly one shorthand key. "
                    f"Found: {provided_shorthand_keys}"
                )
                return None
            return lock_config  # Shorthand format is valid

        # Check for conditional lock
        if lock_config.get("type") == "CONDITIONAL":
            self._validate_conditional_lock(lock_config, location)
            return lock_config

        # Check for OR_LOGIC lock
        if lock_config.get("type") == "OR_LOGIC":
            self._validate_or_logic_lock(lock_config, location)
            return lock_config

        # Validate full format
        if "type" not in lock_config:
            self.errors.append(f"Lock at {location} must have 'type' field")
            return None

        if "property_path" not in lock_config:
            self.errors.append(f"Lock at {location} must have 'property_path' field")
            return None

        # Validate lock type
        lock_type_str = lock_config["type"]
        try:
            if isinstance(lock_type_str, str):
                LockType(lock_type_str)
            else:
                self.errors.append(f"Lock type at {location} must be a string")
                return None
        except ValueError:
            valid_types = [t.value for t in LockType]
            self.errors.append(
                f"Invalid lock type '{lock_type_str}' at {location}. "
                f"Valid types: {valid_types}"
            )
            return None

        # Validate property_path
        if (
            not isinstance(lock_config["property_path"], str)
            or not lock_config["property_path"].strip()
        ):
            self.errors.append(
                f"Lock property_path at {location} must be a non-empty string"
            )
            return None

        return lock_config

    def _validate_conditional_lock(
        self, lock_config: dict[str, Any], location: str
    ) -> None:
        """Validate a conditional lock definition."""
        if "if" not in lock_config:
            self.errors.append(f"Conditional lock at {location} must have 'if' field")

        if "then" not in lock_config:
            self.errors.append(f"Conditional lock at {location} must have 'then' field")

        if "if" in lock_config and not isinstance(lock_config["if"], list):
            self.errors.append(
                f"Conditional lock 'if' field at {location} must be a list"
            )

        if "then" in lock_config and not isinstance(lock_config["then"], list):
            self.errors.append(
                f"Conditional lock 'then' field at {location} must be a list"
            )

        if "else" in lock_config and not isinstance(lock_config["else"], list):
            self.errors.append(
                f"Conditional lock 'else' field at {location} must be a list"
            )

        if "if" in lock_config and isinstance(lock_config["if"], list):
            if not lock_config["if"]:
                self.errors.append(
                    f"Conditional lock 'if' field at {location} cannot be empty"
                )

        if "then" in lock_config and isinstance(lock_config["then"], list):
            if not lock_config["then"]:
                self.errors.append(
                    f"Conditional lock 'then' field at {location} cannot be empty"
                )

    def _validate_or_logic_lock(
        self, lock_config: dict[str, Any], location: str
    ) -> None:
        """Validate an OR logic lock definition."""
        if "conditions" not in lock_config:
            self.errors.append(
                f"OR_LOGIC lock at {location} must have 'conditions' field"
            )
            return

        if not isinstance(lock_config["conditions"], list):
            self.errors.append(
                f"OR_LOGIC lock 'conditions' field at {location} must be a list"
            )
            return

        if not lock_config["conditions"]:
            self.errors.append(
                f"OR_LOGIC lock 'conditions' field at {location} cannot be empty"
            )
            return

        for i, condition in enumerate(lock_config["conditions"]):
            condition_location = f"{location}, condition group {i + 1}"

            if "locks" not in condition:
                self.errors.append(
                    f"Condition group at {condition_location} must have 'locks' field"
                )
                continue

            if not isinstance(condition["locks"], list):
                self.errors.append(
                    f"Condition group 'locks' field at {condition_location} must be a list"
                )
                continue

            if not condition["locks"]:
                self.errors.append(
                    f"Condition group 'locks' field at {condition_location} cannot be empty"
                )

    def _validate_gate(self, gate_def: dict[str, Any], stage_id: str) -> None:
        """Validate gate definition structure."""
        required_fields = ["name", "target_stage", "parent_stage", "locks"]

        for field in required_fields:
            if field not in gate_def:
                self.errors.append(
                    f"Gate '{gate_def.get('name', 'unnamed')}' in stage '{stage_id}' "
                    f"missing required field '{field}'"
                )

        if "name" in gate_def:
            if not isinstance(gate_def["name"], str) or not gate_def["name"].strip():
                self.errors.append(
                    f"Gate name in stage '{stage_id}' must be a non-empty string"
                )

        if "target_stage" in gate_def:
            if (
                not isinstance(gate_def["target_stage"], str)
                or not gate_def["target_stage"].strip()
            ):
                self.errors.append(
                    f"Gate '{gate_def.get('name', 'unnamed')}' target_stage must be a non-empty string"
                )

    def _validate_expected_actions(self, actions: Any, stage_id: str) -> None:
        """Validate expected_actions structure."""
        if not isinstance(actions, list):
            self.errors.append(
                f"expected_actions in stage '{stage_id}' must be a list"
            )
            return

        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                self.errors.append(
                    f"Action {i} in stage '{stage_id}' must be a dictionary"
                )
                continue

            if "description" not in action:
                self.errors.append(
                    f"Action {i} in stage '{stage_id}' must have 'description' field"
                )

            if "related_properties" not in action:
                self.errors.append(
                    f"Action {i} in stage '{stage_id}' must have 'related_properties' field"
                )

            if "related_properties" in action and not isinstance(
                action["related_properties"], list
            ):
                self.errors.append(
                    f"Action {i} 'related_properties' in stage '{stage_id}' must be a list"
                )

    def _validate_expected_properties(self, properties: Any, stage_id: str) -> None:
        """Validate expected_properties structure."""
        if not isinstance(properties, dict):
            self.errors.append(
                f"expected_properties in stage '{stage_id}' must be a dictionary"
            )
            return

        for prop_name, prop_def in properties.items():
            if prop_def is not None and not isinstance(prop_def, dict):
                self.errors.append(
                    f"Property '{prop_name}' definition in stage '{stage_id}' "
                    f"must be a dictionary or None"
                )
                continue

            if isinstance(prop_def, dict):
                if (
                    "type" in prop_def
                    and prop_def["type"] is not None
                    and not isinstance(prop_def["type"], str)
                ):
                    self.errors.append(
                        f"Property '{prop_name}' type in stage '{stage_id}' "
                        f"must be a string or None"
                    )


def _convert_process_config(config: dict[str, Any]) -> ProcessDefinition:
    """
    Convert intuitive YAML format to internal ProcessDefinition format with validation.

    This function uses ProcessConfigParser for comprehensive error collection.
    Always requires a complete configuration with all required fields.

    Args:
        config: Raw configuration dictionary from YAML/JSON
               Must contain: name, stages, initial_stage, final_stage

    Returns:
        Validated ProcessDefinition

    Raises:
        ConfigValidationError: If validation fails (with all collected errors)
        LoaderValidationError: For backward compatibility with legacy code
    """
    try:
        parser = ProcessConfigParser(config)
        return parser.parse_and_validate()
    except ConfigValidationError:
        # Re-raise ConfigValidationError as-is for new code
        raise
    except Exception as e:
        # Wrap unexpected errors in LoaderValidationError for backward compatibility
        raise LoaderValidationError(str(e)) from e


# Schema Integration Functions


def add_schema_to_yaml_output(
    process_dict: dict[str, Any],
    schema_url: str = "https://stageflow.dev/schemas/process.json",
) -> dict[str, Any]:
    """
    Add JSON Schema reference to process dictionary for YAML output.

    This enables IDE validation and auto-completion support in YAML editors.

    Args:
        process_dict: Process definition dictionary
        schema_url: URL to the JSON schema (defaults to official StageFlow schema)

    Returns:
        Process dictionary with $schema property added
    """
    result = {"$schema": schema_url}
    result.update(process_dict)
    return result


def save_process_with_schema(
    process: Process,
    file_path: str | Path,
    include_schema: bool = True,
    schema_url: str = "https://stageflow.dev/schemas/process.json",
) -> None:
    """
    Save a Process object to YAML file with optional schema reference.

    Args:
        process: Process object to save
        file_path: Output file path
        include_schema: Whether to include $schema reference (default: True)
        schema_url: URL to the JSON schema

    Raises:
        IOError: If file cannot be written
    """
    file_path = Path(file_path)

    # Convert Process to dictionary format
    process_dict = process.to_dict()

    # Convert enum values to strings for YAML serialization
    process_dict = _sanitize_for_yaml(process_dict)

    # Wrap in 'process' key for new format
    output_dict = {"process": process_dict}

    # Add schema reference if requested
    if include_schema:
        output_dict = add_schema_to_yaml_output(output_dict, schema_url)

    # Save to YAML file
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(output_dict, f)


def _sanitize_for_yaml(data: Any) -> Any:
    """
    Recursively convert enum values and other non-serializable types to strings.

    Args:
        data: Data structure to sanitize

    Returns:
        Sanitized data structure safe for YAML serialization
    """
    from enum import Enum

    if isinstance(data, Enum):
        return data.value
    elif isinstance(data, dict):
        return {key: _sanitize_for_yaml(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_sanitize_for_yaml(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(_sanitize_for_yaml(item) for item in data)
    else:
        return data


def get_local_schema_path() -> Path:
    """
    Get the path to the local schema file.

    Returns:
        Path to the stageflow-process-schema.yaml file
    """
    # Schema is in the repository root
    current_dir = Path(__file__).parent
    repo_root = current_dir.parent.parent
    return repo_root / "stageflow-process-schema.yaml"


def save_process_with_local_schema(process: Process, file_path: str | Path) -> None:
    """
    Save a Process object to YAML file with reference to local schema file.

    This is useful for development when working with the local schema file.

    Args:
        process: Process object to save
        file_path: Output file path

    Raises:
        IOError: If file cannot be written
    """
    local_schema = get_local_schema_path()
    if local_schema.exists():
        schema_url = f"file://{local_schema.absolute()}"
        save_process_with_schema(
            process, file_path, include_schema=True, schema_url=schema_url
        )
    else:
        # Fallback to no schema if local file doesn't exist
        save_process_with_schema(process, file_path, include_schema=False)


def _validate_process_structure(config: dict[str, Any]) -> None:
    """Validate basic process structure requirements."""
    required_fields = ["name", "stages", "initial_stage", "final_stage"]

    for field in required_fields:
        if field not in config:
            raise LoaderValidationError(
                f"Required field '{field}' is missing from process definition"
            )

    if not isinstance(config["name"], str) or not config["name"].strip():
        raise LoaderValidationError("Process 'name' must be a non-empty string")

    if (
        not isinstance(config["initial_stage"], str)
        or not config["initial_stage"].strip()
    ):
        raise LoaderValidationError(
            "Process 'initial_stage' must be a non-empty string"
        )

    if not isinstance(config["final_stage"], str) or not config["final_stage"].strip():
        raise LoaderValidationError("Process 'final_stage' must be a non-empty string")

    # Validate stage_prop if present
    if "stage_prop" in config:
        if (
            not isinstance(config["stage_prop"], str)
            or not config["stage_prop"].strip()
        ):
            raise LoaderValidationError(
                "Process 'stage_prop' must be a non-empty string"
            )


def _convert_stage_config(stage_id: str, stage_data: dict[str, Any]) -> StageDefinition:
    """Convert and validate stage configuration."""
    converted_stage = dict(stage_data)

    # Add name field
    if "name" not in converted_stage:
        converted_stage["name"] = stage_id

    # Validate and convert gates
    if "gates" in converted_stage:
        gates_data = converted_stage["gates"]
        converted_stage["gates"] = _convert_gates_config(stage_id, gates_data)
    else:
        converted_stage["gates"] = []

    # Add default fields with proper types
    if "description" not in converted_stage:
        converted_stage["description"] = ""
    if "expected_actions" not in converted_stage:
        converted_stage["expected_actions"] = []
    if "expected_properties" not in converted_stage:
        converted_stage["expected_properties"] = None
    if "is_final" not in converted_stage:
        converted_stage["is_final"] = False

    # Validate expected_actions if present and properly structured
    if converted_stage["expected_actions"]:
        # Check if all items are dictionaries (proper ActionDefinition format)
        if all(
            isinstance(action, dict) for action in converted_stage["expected_actions"]
        ):
            _validate_expected_actions(converted_stage["expected_actions"], stage_id)
        # Otherwise, assume it's legacy format (list of strings) and allow it

    # Validate expected_properties if present
    if converted_stage["expected_properties"] is not None:
        _validate_expected_properties(converted_stage["expected_properties"], stage_id)

    return converted_stage  # type: ignore


def _convert_gates_config(stage_id: str, gates_data: Any) -> list[GateDefinition]:
    """Convert and validate gates configuration."""
    gates_list: list[GateDefinition] = []

    if isinstance(gates_data, dict):
        # Convert dict format to list format
        for gate_name, gate_config in gates_data.items():
            if not isinstance(gate_config, dict):
                raise LoaderValidationError(
                    f"Gate '{gate_name}' in stage '{stage_id}' must be a dictionary"
                )

            gate_def = dict(gate_config)
            gate_def["name"] = gate_name
            gate_def["parent_stage"] = stage_id

            # Add description if missing
            if "description" not in gate_def:
                gate_def["description"] = ""

            # Validate and convert locks
            if "locks" not in gate_def:
                raise LoaderValidationError(
                    f"Gate '{gate_name}' in stage '{stage_id}' must have 'locks' field"
                )

            gate_def["locks"] = _convert_locks_config(
                gate_def["locks"], gate_name, stage_id
            )
            _validate_gate_definition(gate_def, stage_id)
            gates_list.append(gate_def)  # type: ignore

    elif isinstance(gates_data, list):
        # Already a list, validate each gate
        for i, gate_config in enumerate(gates_data):
            if not isinstance(gate_config, dict):
                raise LoaderValidationError(
                    f"Gate {i} in stage '{stage_id}' must be a dictionary"
                )

            gate_def = dict(gate_config)
            if "parent_stage" not in gate_def:
                gate_def["parent_stage"] = stage_id
            if "description" not in gate_def:
                gate_def["description"] = ""

            if "name" not in gate_def:
                raise LoaderValidationError(
                    f"Gate {i} in stage '{stage_id}' must have a 'name' field"
                )

            # Validate and convert locks
            if "locks" not in gate_def:
                raise LoaderValidationError(
                    f"Gate '{gate_def['name']}' in stage '{stage_id}' must have 'locks' field"
                )

            gate_def["locks"] = _convert_locks_config(
                gate_def["locks"], gate_def["name"], stage_id
            )
            _validate_gate_definition(gate_def, stage_id)
            gates_list.append(gate_def)  # type: ignore
    else:
        raise LoaderValidationError(
            f"Gates in stage '{stage_id}' must be a dictionary or list"
        )

    return gates_list


def _convert_locks_config(
    locks_data: Any, gate_name: str, stage_id: str
) -> list[dict[str, Any]]:
    """Convert and validate locks configuration."""
    if not isinstance(locks_data, list):
        raise LoaderValidationError(
            f"Locks in gate '{gate_name}' (stage '{stage_id}') must be a list"
        )

    converted_locks: list[dict[str, Any]] = []

    for i, lock_config in enumerate(locks_data):
        if not isinstance(lock_config, dict):
            raise LoaderValidationError(
                f"Lock {i} in gate '{gate_name}' (stage '{stage_id}') must be a dictionary"
            )

        validated_lock = _validate_lock_definition(lock_config, i, gate_name, stage_id)
        converted_locks.append(validated_lock)

    return converted_locks


def _validate_or_logic_lock(
    lock_config: dict[str, Any], location: str
) -> dict[str, Any]:
    """Validate an OR logic lock definition."""
    # Must have 'conditions' field
    if "conditions" not in lock_config:
        raise LoaderValidationError(
            f"OR_LOGIC lock at {location} must have 'conditions' field"
        )

    # 'conditions' must be a list
    if not isinstance(lock_config["conditions"], list):
        raise LoaderValidationError(
            f"OR_LOGIC lock 'conditions' field at {location} must be a list"
        )

    # Must have at least one condition
    if not lock_config["conditions"]:
        raise LoaderValidationError(
            f"OR_LOGIC lock 'conditions' field at {location} cannot be empty"
        )

    # Validate each condition group
    for i, condition in enumerate(lock_config["conditions"]):
        condition_location = f"{location}, condition group {i + 1}"

        # Each condition must have 'locks' field
        if "locks" not in condition:
            raise LoaderValidationError(
                f"Condition group at {condition_location} must have 'locks' field"
            )

        # 'locks' must be a list
        if not isinstance(condition["locks"], list):
            raise LoaderValidationError(
                f"Condition group 'locks' field at {condition_location} must be a list"
            )

        # 'locks' cannot be empty
        if not condition["locks"]:
            raise LoaderValidationError(
                f"Condition group 'locks' field at {condition_location} cannot be empty"
            )

    return lock_config


def _validate_lock_definition(
    lock_config: dict[str, Any], lock_index: int, gate_name: str, stage_id: str
) -> dict[str, Any]:
    """Validate a single lock definition."""
    location = f"lock {lock_index} in gate '{gate_name}' (stage '{stage_id}')"

    # Define all possible shorthand keys (lock type names from LockType enum)
    # Must match exactly with LockType enum values
    shorthand_keys = {
        "exists",
        "equals",
        "greater_than",
        "less_than",
        "contains",
        "regex",
        "type_check",
        "range",
        "length",
        "not_empty",
        "in_list",
        "not_in_list",
        "is_true",
        "is_false",  # These are special shorthand forms
    }

    # Check for shorthand format
    provided_shorthand_keys = set(lock_config.keys()) & shorthand_keys

    if provided_shorthand_keys:
        # Validate shorthand format
        if len(provided_shorthand_keys) != 1:
            raise LoaderValidationError(
                f"Shorthand lock at {location} must have exactly one shorthand key. Found: {provided_shorthand_keys}"
            )

        # Convert shorthand to full format
        shorthand_key = next(iter(provided_shorthand_keys))
        return _convert_shorthand_lock(lock_config, shorthand_key, location)

    # Check for conditional lock format
    if lock_config.get("type") == "CONDITIONAL":
        return _validate_conditional_lock(lock_config, location)

    # Check for OR_LOGIC lock format
    if lock_config.get("type") == "OR_LOGIC":
        return _validate_or_logic_lock(lock_config, location)

    # Validate full format
    if "type" not in lock_config:
        raise LoaderValidationError(f"Lock at {location} must have 'type' field")

    if "property_path" not in lock_config:
        raise LoaderValidationError(
            f"Lock at {location} must have 'property_path' field"
        )

    # Validate lock type
    lock_type_str = lock_config["type"]
    try:
        if isinstance(lock_type_str, str):
            # Convert string to LockType enum to validate it
            LockType(lock_type_str)
        else:
            raise LoaderValidationError(f"Lock type at {location} must be a string")
    except ValueError as e:
        valid_types = [t.value for t in LockType]
        raise LoaderValidationError(
            f"Invalid lock type '{lock_type_str}' at {location}. Valid types: {valid_types}"
        ) from e

    # Validate property_path
    if (
        not isinstance(lock_config["property_path"], str)
        or not lock_config["property_path"].strip()
    ):
        raise LoaderValidationError(
            f"Lock property_path at {location} must be a non-empty string"
        )

    return lock_config  # type: ignore


def _validate_conditional_lock(
    lock_config: dict[str, Any], location: str
) -> dict[str, Any]:
    """Validate a conditional lock definition."""
    # Must have 'if' field
    if "if" not in lock_config:
        raise LoaderValidationError(
            f"Conditional lock at {location} must have 'if' field"
        )

    # Must have 'then' field
    if "then" not in lock_config:
        raise LoaderValidationError(
            f"Conditional lock at {location} must have 'then' field"
        )

    # 'if' and 'then' must be lists
    if not isinstance(lock_config["if"], list):
        raise LoaderValidationError(
            f"Conditional lock 'if' field at {location} must be a list"
        )

    if not isinstance(lock_config["then"], list):
        raise LoaderValidationError(
            f"Conditional lock 'then' field at {location} must be a list"
        )

    # 'else' is optional but must be a list if present
    if "else" in lock_config and not isinstance(lock_config["else"], list):
        raise LoaderValidationError(
            f"Conditional lock 'else' field at {location} must be a list"
        )

    # Validate that 'if' and 'then' are not empty
    if not lock_config["if"]:
        raise LoaderValidationError(
            f"Conditional lock 'if' field at {location} cannot be empty"
        )

    if not lock_config["then"]:
        raise LoaderValidationError(
            f"Conditional lock 'then' field at {location} cannot be empty"
        )

    return lock_config


def _convert_shorthand_lock(
    lock_config: dict[str, Any], shorthand_key: str, location: str
) -> dict[str, Any]:
    """Convert shorthand lock format to full format."""

    # Handle simple shorthand formats where the value is the property path
    if shorthand_key in ("exists", "is_true", "is_false"):
        # These are handled by LockFactory directly, pass them through
        return lock_config  # type: ignore

    # Handle complex shorthand formats
    shorthand_value = lock_config[shorthand_key]

    if isinstance(shorthand_value, str):
        # Simple format: key: "property_path"
        converted_lock = {"type": shorthand_key, "property_path": shorthand_value}
    elif isinstance(shorthand_value, dict):
        # Complex format: key: {property_path: "path", expected_value: value}
        if "property_path" not in shorthand_value:
            raise LoaderValidationError(
                f"Shorthand lock at {location} missing 'property_path'"
            )

        converted_lock = {
            "type": shorthand_key,
            "property_path": shorthand_value["property_path"],
        }

        if "expected_value" in shorthand_value:
            converted_lock["expected_value"] = shorthand_value["expected_value"]
    else:
        raise LoaderValidationError(
            f"Shorthand lock at {location} has invalid value type. "
            f"Expected string or dict, got {type(shorthand_value)}"
        )

    return converted_lock  # type: ignore


def _validate_gate_definition(gate_def: dict[str, Any], stage_id: str) -> None:
    """Validate gate definition structure."""
    required_fields = ["name", "target_stage", "parent_stage", "locks"]

    for field in required_fields:
        if field not in gate_def:
            raise LoaderValidationError(
                f"Gate '{gate_def.get('name', 'unnamed')}' in stage '{stage_id}' missing required field '{field}'"
            )

    if not isinstance(gate_def["name"], str) or not gate_def["name"].strip():
        raise LoaderValidationError(
            f"Gate name in stage '{stage_id}' must be a non-empty string"
        )

    if (
        not isinstance(gate_def["target_stage"], str)
        or not gate_def["target_stage"].strip()
    ):
        raise LoaderValidationError(
            f"Gate '{gate_def['name']}' target_stage must be a non-empty string"
        )


def _validate_expected_actions(actions: Any, stage_id: str) -> None:
    """Validate expected_actions structure."""
    if not isinstance(actions, list):
        raise LoaderValidationError(
            f"expected_actions in stage '{stage_id}' must be a list"
        )

    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise LoaderValidationError(
                f"Action {i} in stage '{stage_id}' must be a dictionary"
            )

        if "description" not in action:
            raise LoaderValidationError(
                f"Action {i} in stage '{stage_id}' must have 'description' field"
            )

        if "related_properties" not in action:
            raise LoaderValidationError(
                f"Action {i} in stage '{stage_id}' must have 'related_properties' field"
            )

        if not isinstance(action["related_properties"], list):
            raise LoaderValidationError(
                f"Action {i} 'related_properties' in stage '{stage_id}' must be a list"
            )


def _validate_expected_properties(properties: Any, stage_id: str) -> None:
    """Validate expected_properties structure."""
    if not isinstance(properties, dict):
        raise LoaderValidationError(
            f"expected_properties in stage '{stage_id}' must be a dictionary"
        )

    for prop_name, prop_def in properties.items():
        if prop_def is not None and not isinstance(prop_def, dict):
            raise LoaderValidationError(
                f"Property '{prop_name}' definition in stage '{stage_id}' must be a dictionary or None"
            )

        if isinstance(prop_def, dict):
            if (
                "type" in prop_def
                and prop_def["type"] is not None
                and not isinstance(prop_def["type"], str)
            ):
                raise LoaderValidationError(
                    f"Property '{prop_name}' type in stage '{stage_id}' must be a string or None"
                )


def _validate_process_definition(converted: dict[str, Any]) -> None:
    """Final validation that the converted config matches ProcessDefinition structure."""
    required_fields = ["name", "stages", "initial_stage", "final_stage"]

    for field in required_fields:
        if field not in converted:
            raise LoaderValidationError(
                f"Final process definition missing required field '{field}'"
            )

    # Add description if missing
    if "description" not in converted:
        converted["description"] = ""

    # Validate stages exist for initial and final stage references
    stages = converted.get("stages", {})
    initial_stage = converted.get("initial_stage")
    final_stage = converted.get("final_stage")

    if initial_stage not in stages:
        raise LoaderValidationError(
            f"initial_stage '{initial_stage}' not found in stages definition"
        )

    if final_stage not in stages:
        raise LoaderValidationError(
            f"final_stage '{final_stage}' not found in stages definition"
        )
