"""Simple file loader for StageFlow that creates Process objects directly."""

import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

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


def load_process(file_path: str | Path) -> Process:
    """
    Load a Process from a YAML or JSON file.

    The file should contain a 'process' key with process configuration.
    All validation is handled by the Process constructor.

    Args:
        file_path: Path to the process definition file

    Returns:
        Process object

    Raises:
        LoadError: If file cannot be loaded or parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise LoadError(f"File not found: {file_path}")

    try:
        with open(file_path, encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                yaml = YAML(typ='safe', pure=True)
                data = yaml.load(f)
            elif file_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise LoadError(f"Unsupported file format: {file_path.suffix}")

        if not isinstance(data, dict):
            raise LoadError("File must contain a dictionary")

        if 'process' not in data:
            # Check if this looks like element data instead of process data
            if any(key in data for key in ['email', 'user_id', 'profile', 'first_name', 'last_name']):
                raise LoaderValidationError(
                    "This appears to be an element data file (JSON), not a process definition file. "
                    "Use a YAML file containing a 'process' key for process definitions. "
                    "Element files are used with the -e/--elem flag for evaluation."
                )
            else:
                raise LoaderValidationError(
                    "File must contain a 'process' key. This should be a process definition file (YAML), "
                    "not an element data file (JSON)."
                )

        # Convert YAML format to internal format
        # Convert YAML format to internal format
        converted_config = _convert_process_config(data['process'])

        # Let the Process constructor handle all validation
        return Process(converted_config)

    except Exception as e:
        if isinstance(e, LoadError):
            raise
        if isinstance(e, LoaderValidationError):
            raise LoadError(f"Failed to load {file_path}: {e}") from e
        raise LoadError(f"Failed to load {file_path}: {e}") from e


def load_process_data(file_path: str | Path) -> ProcessDefinition:
    """
    Load raw process data from a file without creating a Process object.

    Useful for inspection or custom processing.

    Args:
        file_path: Path to the process definition file

    Returns:
        Raw process data dictionary

    Raises:
        LoadError: If file cannot be loaded or parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise LoadError(f"File not found: {file_path}")

    try:
        with open(file_path, encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                yaml = YAML(typ='safe', pure=True)
                data = yaml.load(f)
            elif file_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise LoadError(f"Unsupported file format: {file_path.suffix}")

        if not isinstance(data, dict):
            raise LoadError("File must contain a dictionary")

        if 'process' not in data:
            # Check if this looks like element data instead of process data
            if any(key in data for key in ['email', 'user_id', 'profile', 'first_name', 'last_name']):
                raise LoaderValidationError(
                    "This appears to be an element data file (JSON), not a process definition file. "
                    "Use a YAML file containing a 'process' key for process definitions. "
                    "Element files are used with the -e/--elem flag for evaluation."
                )
            else:
                raise LoaderValidationError(
                    "File must contain a 'process' key. This should be a process definition file (YAML), "
                    "not an element data file (JSON)."
                )

        return data['process']

    except Exception as e:
        if isinstance(e, LoadError):
            raise
        if isinstance(e, LoaderValidationError):
            raise LoadError(f"Failed to load {file_path}: {e}") from e
        raise LoadError(f"Failed to load {file_path}: {e}") from e


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
    if all(field in config for field in ['name', 'stages', 'initial_stage', 'final_stage']):
        _validate_process_structure(config)

    converted: dict[str, Any] = dict(config)

    if 'stages' in config:
        if not isinstance(config['stages'], dict):
            raise LoaderValidationError("'stages' must be a dictionary with stage IDs as keys")

        converted_stages: dict[str, StageDefinition] = {}
        for stage_id, stage_data in config['stages'].items():
            if not isinstance(stage_data, dict):
                raise LoaderValidationError(f"Stage '{stage_id}' must be a dictionary")

            converted_stage = _convert_stage_config(stage_id, stage_data)
            converted_stages[stage_id] = converted_stage

        converted['stages'] = converted_stages

    # Validate final structure matches ProcessDefinition only if we have all required fields
    if all(field in converted for field in ['name', 'stages', 'initial_stage', 'final_stage']):
        _validate_process_definition(converted)

    return converted  # type: ignore


def _validate_process_structure(config: dict[str, Any]) -> None:
    """Validate basic process structure requirements."""
    required_fields = ['name', 'stages', 'initial_stage', 'final_stage']

    for field in required_fields:
        if field not in config:
            raise LoaderValidationError(f"Required field '{field}' is missing from process definition")

    if not isinstance(config['name'], str) or not config['name'].strip():
        raise LoaderValidationError("Process 'name' must be a non-empty string")

    if not isinstance(config['initial_stage'], str) or not config['initial_stage'].strip():
        raise LoaderValidationError("Process 'initial_stage' must be a non-empty string")

    if not isinstance(config['final_stage'], str) or not config['final_stage'].strip():
        raise LoaderValidationError("Process 'final_stage' must be a non-empty string")


def _convert_stage_config(stage_id: str, stage_data: dict[str, Any]) -> StageDefinition:
    """Convert and validate stage configuration."""
    converted_stage = dict(stage_data)

    # Add name field
    if 'name' not in converted_stage:
        converted_stage['name'] = stage_id

    # Validate and convert gates
    if 'gates' in converted_stage:
        gates_data = converted_stage['gates']
        converted_stage['gates'] = _convert_gates_config(stage_id, gates_data)
    else:
        converted_stage['gates'] = []

    # Add default fields with proper types
    if 'description' not in converted_stage:
        converted_stage['description'] = ''
    if 'expected_actions' not in converted_stage:
        converted_stage['expected_actions'] = []
    if 'expected_properties' not in converted_stage:
        converted_stage['expected_properties'] = None
    if 'is_final' not in converted_stage:
        converted_stage['is_final'] = False

    # Validate expected_actions if present and properly structured
    if converted_stage['expected_actions']:
        # Check if all items are dictionaries (proper ActionDefinition format)
        if all(isinstance(action, dict) for action in converted_stage['expected_actions']):
            _validate_expected_actions(converted_stage['expected_actions'], stage_id)
        # Otherwise, assume it's legacy format (list of strings) and allow it

    # Validate expected_properties if present
    if converted_stage['expected_properties'] is not None:
        _validate_expected_properties(converted_stage['expected_properties'], stage_id)

    return converted_stage  # type: ignore


def _convert_gates_config(stage_id: str, gates_data: Any) -> list[GateDefinition]:
    """Convert and validate gates configuration."""
    gates_list: list[GateDefinition] = []

    if isinstance(gates_data, dict):
        # Convert dict format to list format
        for gate_name, gate_config in gates_data.items():
            if not isinstance(gate_config, dict):
                raise LoaderValidationError(f"Gate '{gate_name}' in stage '{stage_id}' must be a dictionary")

            gate_def = dict(gate_config)
            gate_def['name'] = gate_name
            gate_def['parent_stage'] = stage_id

            # Add description if missing
            if 'description' not in gate_def:
                gate_def['description'] = ''

            # Validate and convert locks
            if 'locks' not in gate_def:
                raise LoaderValidationError(f"Gate '{gate_name}' in stage '{stage_id}' must have 'locks' field")

            gate_def['locks'] = _convert_locks_config(gate_def['locks'], gate_name, stage_id)
            _validate_gate_definition(gate_def, stage_id)
            gates_list.append(gate_def)  # type: ignore

    elif isinstance(gates_data, list):
        # Already a list, validate each gate
        for i, gate_config in enumerate(gates_data):
            if not isinstance(gate_config, dict):
                raise LoaderValidationError(f"Gate {i} in stage '{stage_id}' must be a dictionary")

            gate_def = dict(gate_config)
            if 'parent_stage' not in gate_def:
                gate_def['parent_stage'] = stage_id
            if 'description' not in gate_def:
                gate_def['description'] = ''

            if 'name' not in gate_def:
                raise LoaderValidationError(f"Gate {i} in stage '{stage_id}' must have a 'name' field")

            # Validate and convert locks
            if 'locks' not in gate_def:
                raise LoaderValidationError(f"Gate '{gate_def['name']}' in stage '{stage_id}' must have 'locks' field")

            gate_def['locks'] = _convert_locks_config(gate_def['locks'], gate_def['name'], stage_id)
            _validate_gate_definition(gate_def, stage_id)
            gates_list.append(gate_def)  # type: ignore
    else:
        raise LoaderValidationError(f"Gates in stage '{stage_id}' must be a dictionary or list")

    return gates_list


def _convert_locks_config(locks_data: Any, gate_name: str, stage_id: str) -> list[LockDefinition]:
    """Convert and validate locks configuration."""
    if not isinstance(locks_data, list):
        raise LoaderValidationError(f"Locks in gate '{gate_name}' (stage '{stage_id}') must be a list")

    converted_locks: list[LockDefinition] = []

    for i, lock_config in enumerate(locks_data):
        if not isinstance(lock_config, dict):
            raise LoaderValidationError(f"Lock {i} in gate '{gate_name}' (stage '{stage_id}') must be a dictionary")

        validated_lock = _validate_lock_definition(lock_config, i, gate_name, stage_id)
        converted_locks.append(validated_lock)

    return converted_locks


def _validate_lock_definition(lock_config: dict[str, Any], lock_index: int, gate_name: str, stage_id: str) -> LockDefinition:
    """Validate a single lock definition."""
    location = f"lock {lock_index} in gate '{gate_name}' (stage '{stage_id}')"

    # Check for shorthand format
    if 'exists' in lock_config or 'is_true' in lock_config or 'is_false' in lock_config:
        # Validate shorthand format
        shorthand_keys = {'exists', 'is_true', 'is_false'}
        provided_keys = set(lock_config.keys()) & shorthand_keys

        if len(provided_keys) != 1:
            raise LoaderValidationError(f"Shorthand lock at {location} must have exactly one of: {shorthand_keys}")

        return lock_config  # type: ignore

    # Validate full format
    if 'type' not in lock_config:
        raise LoaderValidationError(f"Lock at {location} must have 'type' field")

    if 'property_path' not in lock_config:
        raise LoaderValidationError(f"Lock at {location} must have 'property_path' field")

    # Validate lock type
    lock_type_str = lock_config['type']
    try:
        if isinstance(lock_type_str, str):
            # Convert string to LockType enum to validate it
            LockType(lock_type_str)
        else:
            raise LoaderValidationError(f"Lock type at {location} must be a string")
    except ValueError as e:
        valid_types = [t.value for t in LockType]
        raise LoaderValidationError(f"Invalid lock type '{lock_type_str}' at {location}. Valid types: {valid_types}") from e

    # Validate property_path
    if not isinstance(lock_config['property_path'], str) or not lock_config['property_path'].strip():
        raise LoaderValidationError(f"Lock property_path at {location} must be a non-empty string")

    return lock_config  # type: ignore


def _validate_gate_definition(gate_def: dict[str, Any], stage_id: str) -> None:
    """Validate gate definition structure."""
    required_fields = ['name', 'target_stage', 'parent_stage', 'locks']

    for field in required_fields:
        if field not in gate_def:
            raise LoaderValidationError(f"Gate '{gate_def.get('name', 'unnamed')}' in stage '{stage_id}' missing required field '{field}'")

    if not isinstance(gate_def['name'], str) or not gate_def['name'].strip():
        raise LoaderValidationError(f"Gate name in stage '{stage_id}' must be a non-empty string")

    if not isinstance(gate_def['target_stage'], str) or not gate_def['target_stage'].strip():
        raise LoaderValidationError(f"Gate '{gate_def['name']}' target_stage must be a non-empty string")


def _validate_expected_actions(actions: Any, stage_id: str) -> None:
    """Validate expected_actions structure."""
    if not isinstance(actions, list):
        raise LoaderValidationError(f"expected_actions in stage '{stage_id}' must be a list")

    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise LoaderValidationError(f"Action {i} in stage '{stage_id}' must be a dictionary")

        if 'description' not in action:
            raise LoaderValidationError(f"Action {i} in stage '{stage_id}' must have 'description' field")

        if 'related_properties' not in action:
            raise LoaderValidationError(f"Action {i} in stage '{stage_id}' must have 'related_properties' field")

        if not isinstance(action['related_properties'], list):
            raise LoaderValidationError(f"Action {i} 'related_properties' in stage '{stage_id}' must be a list")


def _validate_expected_properties(properties: Any, stage_id: str) -> None:
    """Validate expected_properties structure."""
    if not isinstance(properties, dict):
        raise LoaderValidationError(f"expected_properties in stage '{stage_id}' must be a dictionary")

    for prop_name, prop_def in properties.items():
        if prop_def is not None and not isinstance(prop_def, dict):
            raise LoaderValidationError(f"Property '{prop_name}' definition in stage '{stage_id}' must be a dictionary or None")

        if isinstance(prop_def, dict):
            if 'type' in prop_def and prop_def['type'] is not None and not isinstance(prop_def['type'], str):
                raise LoaderValidationError(f"Property '{prop_name}' type in stage '{stage_id}' must be a string or None")


def _validate_process_definition(converted: dict[str, Any]) -> None:
    """Final validation that the converted config matches ProcessDefinition structure."""
    required_fields = ['name', 'stages', 'initial_stage', 'final_stage']

    for field in required_fields:
        if field not in converted:
            raise LoaderValidationError(f"Final process definition missing required field '{field}'")

    # Add description if missing
    if 'description' not in converted:
        converted['description'] = ''

    # Validate stages exist for initial and final stage references
    stages = converted.get('stages', {})
    initial_stage = converted.get('initial_stage')
    final_stage = converted.get('final_stage')

    if initial_stage not in stages:
        raise LoaderValidationError(f"initial_stage '{initial_stage}' not found in stages definition")

    if final_stage not in stages:
        raise LoaderValidationError(f"final_stage '{final_stage}' not found in stages definition")

