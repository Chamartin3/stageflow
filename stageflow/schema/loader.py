"""Simple file loader for StageFlow that creates Process objects directly."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stageflow.element import Element, create_element
from stageflow.gate import GateDefinition
from stageflow.lock import (
    LockDefinition,
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
        # Check if this is a validation error we can handle gracefully
        if "not found in stages definition" in str(e) or "must have" in str(e):
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

                # Collect validation errors
                errors = []

                # Check stages structure
                stages = process_config.get("stages", {})
                initial_stage = process_config.get("initial_stage", "")
                final_stage = process_config.get("final_stage", "")

                if not stages:
                    errors.append("No stages defined")
                elif len(stages) < 2:
                    errors.append("Process must have at least two stages")
                else:
                    stage_names = set(stages.keys())

                    if initial_stage and initial_stage not in stage_names:
                        available = ", ".join(sorted(stage_names))
                        errors.append(
                            f"initial_stage '{initial_stage}' not found. Available stages: {available}"
                        )

                    if final_stage and final_stage not in stage_names:
                        available = ", ".join(sorted(stage_names))
                        errors.append(
                            f"final_stage '{final_stage}' not found. Available stages: {available}"
                        )

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


def _convert_process_config(config: dict[str, Any]) -> ProcessDefinition:
    """
    Convert intuitive YAML format to internal ProcessDefinition format with validation.

    Validates the structure using TypedDicts and transforms:
    - stages dict with keys as names -> stages dict with name fields
    - gates dict with keys as names -> gates list with name fields
    - lock definitions with proper type validation

    Args:
        config: Raw configuration dictionary from YAML/JSON

    Returns:
        Validated ProcessDefinition

    Raises:
        LoadError: If validation fails or required fields are missing
    """
    # Only validate fields if this is called from load_process (has all required fields)
    # The _convert_process_config function can be called with partial configs for testing
    if all(
        field in config for field in ["name", "stages", "initial_stage", "final_stage"]
    ):
        _validate_process_structure(config)

    converted: dict[str, Any] = dict(config)

    # Pass through stage_prop if present
    if "stage_prop" in config:
        converted["stage_prop"] = config["stage_prop"]

    if "stages" in config:
        if not isinstance(config["stages"], dict):
            raise LoaderValidationError(
                "'stages' must be a dictionary with stage IDs as keys"
            )

        converted_stages: dict[str, StageDefinition] = {}
        for stage_id, stage_data in config["stages"].items():
            if not isinstance(stage_data, dict):
                raise LoaderValidationError(f"Stage '{stage_id}' must be a dictionary")

            converted_stage = _convert_stage_config(stage_id, stage_data)
            converted_stages[stage_id] = converted_stage

        converted["stages"] = converted_stages

    # Validate final structure matches ProcessDefinition only if we have all required fields
    if all(
        field in converted
        for field in ["name", "stages", "initial_stage", "final_stage"]
    ):
        _validate_process_definition(converted)

    return converted  # type: ignore


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
) -> list[LockDefinition]:
    """Convert and validate locks configuration."""
    if not isinstance(locks_data, list):
        raise LoaderValidationError(
            f"Locks in gate '{gate_name}' (stage '{stage_id}') must be a list"
        )

    converted_locks: list[LockDefinition] = []

    for i, lock_config in enumerate(locks_data):
        if not isinstance(lock_config, dict):
            raise LoaderValidationError(
                f"Lock {i} in gate '{gate_name}' (stage '{stage_id}') must be a dictionary"
            )

        validated_lock = _validate_lock_definition(lock_config, i, gate_name, stage_id)
        converted_locks.append(validated_lock)

    return converted_locks


def _validate_lock_definition(
    lock_config: dict[str, Any], lock_index: int, gate_name: str, stage_id: str
) -> LockDefinition:
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


def _convert_shorthand_lock(
    lock_config: dict[str, Any], shorthand_key: str, location: str
) -> LockDefinition:
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
