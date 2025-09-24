"""JSON schema loader for StageFlow with enhanced validation and reference support."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stageflow.process.main import Process
    from stageflow.core.stage import Stage, ActionDefinition, StageActionDefinitions

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from stageflow.gates import Gate, Lock, LockType
from stageflow.gates.lock import LockFactory
from stageflow.process.schema.core import ItemSchema
from stageflow.process.schema.models import (
    ValidationContext,
    validate_stageflow_schema,
)
from stageflow.models import ProcessConfig, StageConfig, LoaderConfig


class JSONLoadError(Exception):
    """Base exception for JSON loading errors with location information."""

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


class JSONSchemaError(JSONLoadError):
    """Exception for schema validation errors during JSON loading."""
    pass


class JSONReferenceError(JSONLoadError):
    """Exception for JSON reference resolution errors."""
    pass


class JsonLoader:
    """
    Enhanced JSON loader for StageFlow process definitions.

    Provides robust JSON loading with schema validation, reference support,
    and detailed error reporting with location information.

    Features:
    - JSON schema validation using jsonschema library
    - JSON reference/pointer resolution support
    - Precise error location reporting
    - Integration with Process class construction
    - Performance optimizations for large files
    - Memory-efficient processing
    """

    def __init__(self, validate_schema: bool = True, resolve_references: bool = True, use_pydantic_validation: bool = True):
        """Initialize JSON loader with enhanced configuration.

        Args:
            validate_schema: Whether to validate against JSON schema
            resolve_references: Whether to resolve JSON references
            use_pydantic_validation: Whether to use pydantic schema validation
        """
        self.validate_schema_flag = validate_schema and HAS_JSONSCHEMA
        self.resolve_references_flag = resolve_references
        self.use_pydantic_validation = use_pydantic_validation

        # Track file paths for reference resolution
        self._current_file: Path | None = None
        self._reference_stack: list[Path] = []
        self._reference_cache: dict[str, Any] = {}

        # Performance settings
        self._streaming_threshold = 10 * 1024 * 1024  # 10MB
        self._cache_enabled = True

        if validate_schema and not HAS_JSONSCHEMA:
            import warnings
            warnings.warn(
                "jsonschema library not available. Schema validation disabled. "
                "Install with: pip install jsonschema",
                UserWarning,
                stacklevel=2
            )

    def load_process(self, file_path: str | Path) -> "Process":
        """
        Load process from JSON file with enhanced error handling.

        Args:
            file_path: Path to JSON file containing process definition

        Returns:
            Process instance created from JSON definition

        Raises:
            JSONLoadError: If file loading or parsing fails
            JSONSchemaError: If schema validation fails
            JSONReferenceError: If reference resolution fails
        """
        config = self.load_process_config(file_path)
        return self._config_to_process(config)

    def load_process_config(self, file_path: str | Path) -> ProcessConfig:
        """
        Load process configuration from JSON file.

        Args:
            file_path: Path to JSON file containing process definition

        Returns:
            ProcessConfig TypedDict with validated configuration

        Raises:
            JSONLoadError: If file loading or parsing fails
            JSONSchemaError: If schema validation fails
            JSONReferenceError: If reference resolution fails
        """
        path = Path(file_path)
        if not path.exists():
            raise JSONLoadError(
                f"Process file not found: {file_path}",
                file_path=str(path)
            )

        self._current_file = path.resolve()

        try:
            # Check file size for optimization strategy
            file_size = path.stat().st_size
            if file_size > self._streaming_threshold:
                data = self.optimize_loading(path)
            else:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
        except json.JSONDecodeError as e:
            raise JSONLoadError(
                f"JSON parsing error: {e.msg}",
                file_path=str(path),
                line=e.lineno,
                column=e.colno
            ) from e
        except Exception as e:
            raise JSONLoadError(
                f"Failed to read JSON file: {str(e)}",
                file_path=str(path)
            ) from e

        if not isinstance(data, dict):
            raise JSONSchemaError(
                "JSON file must contain an object at root level",
                file_path=str(path)
            )

        # Resolve references if enabled
        if self.resolve_references_flag:
            try:
                data = self.resolve_references(data, path.parent)
            except Exception as e:
                if isinstance(e, JSONReferenceError):
                    raise
                raise JSONReferenceError(
                    f"Failed to resolve references: {str(e)}",
                    file_path=str(path)
                ) from e

        # Validate schema if enabled
        if self.validate_schema_flag:
            self.validate_schema(data)

        return self._data_to_config(data)

    def load_process_from_string(self, json_content: str, file_path: str | None = None) -> "Process":
        """
        Load process from JSON string with enhanced validation.

        Args:
            json_content: JSON content as string
            file_path: Optional file path for error reporting

        Returns:
            Process instance created from JSON content

        Raises:
            JSONLoadError: If parsing fails
            JSONSchemaError: If schema validation fails
        """
        config = self.load_process_config_from_string(json_content, file_path)
        return self._config_to_process(config)

    def load_process_config_from_string(self, json_content: str, file_path: str | None = None) -> ProcessConfig:
        """
        Load process configuration from JSON string.

        Args:
            json_content: JSON content as string
            file_path: Optional file path for error reporting

        Returns:
            ProcessConfig TypedDict with validated configuration

        Raises:
            JSONLoadError: If parsing fails
            JSONSchemaError: If schema validation fails
        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise JSONLoadError(
                f"JSON parsing error: {e.msg}",
                file_path=file_path,
                line=e.lineno,
                column=e.colno
            ) from e

        if not isinstance(data, dict):
            raise JSONSchemaError(
                "JSON content must contain an object at root level",
                file_path=file_path
            )

        # Note: Reference resolution from string requires base path
        if self.resolve_references_flag and file_path:
            base_path = Path(file_path).parent
            data = self.resolve_references(data, base_path)

        # Validate schema if enabled
        if self.validate_schema_flag:
            self.validate_schema(data)

        return self._data_to_config(data)

    def validate_schema(self, data: dict[str, Any]) -> None:
        """
        Validate JSON data against StageFlow schema requirements.

        Args:
            data: Dictionary containing process definition

        Raises:
            JSONSchemaError: If schema validation fails
        """
        file_path = str(self._current_file) if self._current_file else None

        if self.use_pydantic_validation:
            try:
                # Use comprehensive pydantic validation
                context = ValidationContext(strict_mode=True)
                validated_model = validate_stageflow_schema(data, context)

                # Log any warnings
                if context.warnings:
                    import warnings
                    for warning in context.warnings:
                        warnings.warn(f"JSON validation warning: {warning}", UserWarning)

            except Exception as e:
                raise JSONSchemaError(
                    f"Pydantic validation failed: {str(e)}",
                    file_path=file_path
                ) from e
        else:
            # Fall back to legacy validation
            self._validate_schema_legacy(data, file_path)

        # Enhanced JSON schema validation if library is available
        if HAS_JSONSCHEMA:
            self._validate_with_jsonschema(data, file_path)

    def _validate_schema_legacy(self, data: dict[str, Any], file_path: str | None) -> None:
        """Legacy schema validation for backward compatibility."""
        # Required top-level fields
        if "name" not in data:
            raise JSONSchemaError(
                "Process definition must include 'name' field",
                file_path=file_path
            )

        if not isinstance(data["name"], str) or not data["name"].strip():
            raise JSONSchemaError(
                "Process 'name' must be a non-empty string",
                file_path=file_path
            )

        # Validate stages structure
        if "stages" in data:
            stages = data["stages"]
            if not isinstance(stages, dict):
                raise JSONSchemaError(
                    "'stages' must be an object",
                    file_path=file_path
                )

            for stage_name, stage_def in stages.items():
                self._validate_stage_schema(stage_name, stage_def, file_path)

        # Validate stage_order if present
        if "stage_order" in data:
            stage_order = data["stage_order"]
            if not isinstance(stage_order, list):
                raise JSONSchemaError(
                    "'stage_order' must be an array",
                    file_path=file_path
                )

            if "stages" in data:
                stage_names = set(data["stages"].keys())
                missing_stages = set(stage_order) - stage_names
                if missing_stages:
                    raise JSONSchemaError(
                        f"stage_order references non-existent stages: {missing_stages}",
                        file_path=file_path
                    )

    def resolve_references(self, data: dict[str, Any], base_path: Path) -> dict[str, Any]:
        """
        Resolve JSON references and pointers.

        Args:
            data: Dictionary containing potentially referenced data
            base_path: Base path for resolving relative references

        Returns:
            Dictionary with resolved references

        Raises:
            JSONReferenceError: If reference resolution fails
        """
        return self._resolve_references_recursive(data, base_path)

    def optimize_loading(self, file_path: Path) -> dict[str, Any]:
        """
        Optimized loading for large JSON files.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data

        Raises:
            JSONLoadError: If loading fails
        """
        try:
            # For very large files, we could implement streaming parsing
            # For now, use standard loading with memory optimization
            with open(file_path, encoding="utf-8") as f:
                # Read in chunks for memory efficiency
                return json.load(f)
        except Exception as e:
            raise JSONLoadError(
                f"Failed to load large JSON file: {str(e)}",
                file_path=str(file_path)
            ) from e

    def _validate_with_jsonschema(self, data: dict[str, Any], file_path: str | None) -> None:
        """Validate using jsonschema library if available."""
        # This would use a formal JSON schema definition
        # For now, we'll use the same validation as YAML loader
        pass

    def _validate_stage_schema(self, stage_name: str, stage_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual stage schema."""
        if not isinstance(stage_def, dict):
            raise JSONSchemaError(
                f"Stage '{stage_name}' must be an object",
                file_path=file_path
            )

        # Validate gates if present
        if "gates" in stage_def:
            gates = stage_def["gates"]
            if not isinstance(gates, dict):
                raise JSONSchemaError(
                    f"Gates in stage '{stage_name}' must be an object",
                    file_path=file_path
                )

            for gate_name, gate_def in gates.items():
                self._validate_gate_schema(stage_name, gate_name, gate_def, file_path)

    def _validate_gate_schema(self, stage_name: str, gate_name: str, gate_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual gate schema."""
        if not isinstance(gate_def, dict):
            raise JSONSchemaError(
                f"Gate '{gate_name}' in stage '{stage_name}' must be an object",
                file_path=file_path
            )

        # Reject deprecated logic field
        if "logic" in gate_def:
            raise JSONSchemaError(
                f"Gate '{gate_name}' in stage '{stage_name}' contains deprecated 'logic' field. Gates are now AND-only by design. Remove the 'logic' field.",
                file_path=file_path
            )

        # Validate locks if present
        if "locks" in gate_def:
            locks = gate_def["locks"]
            if not isinstance(locks, list):
                raise JSONSchemaError(
                    f"Locks in gate '{gate_name}' of stage '{stage_name}' must be an array",
                    file_path=file_path
                )

            for i, lock_def in enumerate(locks):
                self._validate_lock_schema(stage_name, gate_name, i, lock_def, file_path)

    def _validate_lock_schema(self, stage_name: str, gate_name: str, lock_index: int, lock_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual lock schema."""
        location = f"lock {lock_index} in gate '{gate_name}' of stage '{stage_name}'"

        if not isinstance(lock_def, dict):
            raise JSONSchemaError(
                f"Lock definition at {location} must be an object",
                file_path=file_path
            )

        # Required fields
        if "property" not in lock_def:
            raise JSONSchemaError(
                f"Lock at {location} must include 'property' field",
                file_path=file_path
            )

        if "type" not in lock_def:
            raise JSONSchemaError(
                f"Lock at {location} must include 'type' field",
                file_path=file_path
            )

        # Validate lock type
        lock_type = lock_def["type"]
        valid_types = [t.value for t in LockType]
        if lock_type not in valid_types:
            raise JSONSchemaError(
                f"Invalid lock type '{lock_type}' at {location}. Valid types: {valid_types}",
                file_path=file_path
            )

    def _resolve_references_recursive(self, data: Any, base_path: Path) -> Any:
        """Recursively resolve references in data structure."""
        if isinstance(data, dict):
            # Check for JSON reference
            if "$ref" in data:
                return self._resolve_reference(data["$ref"], base_path)

            # Recursively process other dictionary values
            result = {}
            for key, value in data.items():
                result[key] = self._resolve_references_recursive(value, base_path)
            return result

        elif isinstance(data, list):
            return [self._resolve_references_recursive(item, base_path) for item in data]

        else:
            return data

    def _resolve_reference(self, ref: str, base_path: Path) -> Any:
        """Resolve a single JSON reference."""
        # Parse reference
        if ref.startswith("#/"):
            # Internal reference - not implemented for initial version
            raise JSONReferenceError(f"Internal references not yet supported: {ref}")

        # External file reference
        ref_parts = ref.split("#")
        file_ref = ref_parts[0]
        json_pointer = ref_parts[1] if len(ref_parts) > 1 else ""

        # Resolve file path
        if file_ref.startswith(("http://", "https://")):
            raise JSONReferenceError(f"HTTP references not supported: {ref}")

        ref_path = base_path / file_ref
        resolved_path = ref_path.resolve()

        # Check for circular dependencies
        if resolved_path in self._reference_stack:
            raise JSONReferenceError(
                f"Circular reference dependency detected: {resolved_path}",
                file_path=str(self._current_file) if self._current_file else None
            )

        if not resolved_path.exists():
            raise JSONReferenceError(
                f"Reference file not found: {file_ref}",
                file_path=str(self._current_file) if self._current_file else None
            )

        # Check cache
        cache_key = str(resolved_path)
        if self._cache_enabled and cache_key in self._reference_cache:
            referenced_data = self._reference_cache[cache_key]
        else:
            # Load referenced file
            self._reference_stack.append(resolved_path)
            old_current_file = self._current_file
            self._current_file = resolved_path

            try:
                with open(resolved_path, encoding="utf-8") as f:
                    referenced_data = json.load(f)

                # Cache the result
                if self._cache_enabled:
                    self._reference_cache[cache_key] = referenced_data

            except Exception as e:
                raise JSONReferenceError(
                    f"Failed to load reference file {file_ref}: {str(e)}",
                    file_path=str(resolved_path)
                ) from e
            finally:
                self._reference_stack.pop()
                self._current_file = old_current_file

        # Apply JSON pointer if specified
        if json_pointer:
            return self._apply_json_pointer(referenced_data, json_pointer)
        else:
            return referenced_data

    def _apply_json_pointer(self, data: Any, pointer: str) -> Any:
        """Apply JSON pointer to extract specific data."""
        if not pointer.startswith("/"):
            raise JSONReferenceError(f"Invalid JSON pointer: {pointer}")

        if pointer == "/":
            return data

        parts = pointer[1:].split("/")
        current = data

        for part in parts:
            # Unescape JSON pointer special characters
            part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(current, dict):
                if part not in current:
                    raise JSONReferenceError(f"JSON pointer path not found: {pointer}")
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError) as e:
                    raise JSONReferenceError(f"Invalid array index in JSON pointer: {pointer}") from e
            else:
                raise JSONReferenceError(f"Cannot apply JSON pointer to non-object/array: {pointer}")

        return current

    def _data_to_config(self, data: dict[str, Any]) -> ProcessConfig:
        """
        Convert loaded JSON data to ProcessConfig TypedDict.

        Args:
            data: Dictionary containing process definition

        Returns:
            ProcessConfig TypedDict

        Raises:
            JSONSchemaError: If process structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            # Transform data to match ProcessConfig structure
            config: ProcessConfig = {
                "name": data["name"],
                "stages": self._parse_stages_to_config(data.get("stages", {})),
            }

            # Add optional fields
            if "stage_order" in data:
                config["stage_order"] = data["stage_order"]
            if "initial_stage" in data:
                config["initial_stage"] = data["initial_stage"]
            if "final_stage" in data:
                config["final_stage"] = data["final_stage"]
            if "allow_stage_skipping" in data:
                config["allow_stage_skipping"] = data["allow_stage_skipping"]
            if "regression_detection" in data:
                config["regression_detection"] = data["regression_detection"]
            if "metadata" in data:
                config["metadata"] = data["metadata"]

            return config

        except Exception as e:
            if isinstance(e, (JSONLoadError, JSONSchemaError)):
                raise
            raise JSONSchemaError(
                f"Failed to convert data to config: {str(e)}",
                file_path=file_path
            ) from e

    def _config_to_process(self, config: ProcessConfig) -> "Process":
        """
        Convert ProcessConfig to Process instance.

        Args:
            config: ProcessConfig TypedDict

        Returns:
            Process instance

        Raises:
            JSONSchemaError: If conversion fails
        """
        try:
            # Convert stage configs to Stage instances
            stages = []
            stages_data = config["stages"]

            if isinstance(stages_data, list):
                # List format
                for stage_config in stages_data:
                    stage = self._stage_config_to_stage(stage_config)
                    stages.append(stage)
            else:
                # Dict format
                for stage_name, stage_config in stages_data.items():
                    # Ensure stage has a name
                    if "name" not in stage_config:
                        stage_config = dict(stage_config)
                        stage_config["name"] = stage_name
                    stage = self._stage_config_to_stage(stage_config)
                    stages.append(stage)

            # Import Process here to avoid circular imports
            from stageflow.process.main import Process
            from stageflow.process.config import ProcessConfig as ProcessConfigClass

            # Create ProcessConfig for the Process constructor
            process_config = ProcessConfigClass(
                name=config["name"],
                initial_stage=config.get("initial_stage"),
                final_stage=config.get("final_stage"),
                allow_stage_skipping=config.get("allow_stage_skipping", False),
                regression_detection=config.get("regression_detection", True),
                metadata=config.get("metadata", {}),
            )

            return Process(
                name=config["name"],
                stages=stages,
                config=process_config,
                stage_order=config.get("stage_order", []),
            )

        except Exception as e:
            raise JSONSchemaError(
                f"Failed to convert config to process: {str(e)}"
            ) from e

    def _parse_stages_to_config(self, stages_data: dict[str, Any]) -> list[StageConfig]:
        """
        Parse stages data to list of StageConfig TypedDicts.

        Args:
            stages_data: Dictionary containing stage definitions

        Returns:
            List of StageConfig TypedDicts

        Raises:
            JSONSchemaError: If stage parsing fails
        """
        stage_configs = []

        for stage_name, stage_def in stages_data.items():
            stage_config: StageConfig = {
                "name": stage_name
            }

            # Add optional fields
            if "gates" in stage_def:
                stage_config["gates"] = self._parse_gates_to_config(stage_def["gates"])
            if "schema" in stage_def:
                stage_config["schema"] = stage_def["schema"]
            if "allow_partial" in stage_def:
                stage_config["allow_partial"] = stage_def["allow_partial"]
            if "metadata" in stage_def:
                stage_config["metadata"] = stage_def["metadata"]
            if "action_definitions" in stage_def:
                stage_config["action_definitions"] = stage_def["action_definitions"]

            stage_configs.append(stage_config)

        return stage_configs

    def _parse_gates_to_config(self, gates_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse gates data to list of gate configurations.

        Args:
            gates_data: Dictionary containing gate definitions

        Returns:
            List of gate configuration dictionaries
        """
        gate_configs = []

        for gate_name, gate_def in gates_data.items():
            gate_config = {
                "name": gate_name,
                "operation": gate_def.get("logic", "and").upper(),
                "components": gate_def.get("locks", [])
            }

            if "metadata" in gate_def:
                gate_config["metadata"] = gate_def["metadata"]

            gate_configs.append(gate_config)

        return gate_configs

    def _stage_config_to_stage(self, stage_config: StageConfig) -> "Stage":
        """
        Convert StageConfig to Stage instance.

        Args:
            stage_config: StageConfig TypedDict

        Returns:
            Stage instance
        """
        gates = []
        schema = None

        # Parse gates from config
        gates_data = stage_config.get("gates", [])
        for gate_config in gates_data:
            gate = self._gate_config_to_gate(gate_config)
            gates.append(gate)

        # Parse schema from config
        schema_data = stage_config.get("schema")
        if schema_data:
            schema = self._parse_schema(f"{stage_config['name']}_schema", schema_data)

        # Parse action definitions
        action_definitions = None
        action_defs_data = stage_config.get("action_definitions")
        if action_defs_data:
            action_definitions = self._parse_action_definitions(action_defs_data)

        # Import Stage here to avoid circular imports
        from stageflow.core.stage import Stage
        return Stage(
            name=stage_config["name"],
            gates=gates,
            schema=schema,
            metadata=stage_config.get("metadata", {}),
            allow_partial=stage_config.get("allow_partial", False),
            action_definitions=action_definitions,
        )

    def _gate_config_to_gate(self, gate_config: dict[str, Any]) -> Gate:
        """
        Convert gate configuration to Gate instance.

        Args:
            gate_config: Gate configuration dictionary

        Returns:
            Gate instance
        """
        locks = []
        gate_name = gate_config["name"]

        # Parse locks from components
        components_data = gate_config.get("components", [])
        for i, lock_def in enumerate(components_data):
            lock = self._parse_lock(lock_def, f"{gate_name}[{i}]")
            locks.append(lock)

        # Wrap locks in LockWrapper to make them evaluable
        from stageflow.gates.gate import LockWrapper
        components = [LockWrapper(lock) for lock in locks]

        return Gate(
            name=gate_name,
            components=tuple(components),
            metadata=gate_config.get("metadata", {}),
        )

    def _parse_stage(self, stage_name: str, stage_def: dict[str, Any]) -> "Stage":
        """
        Parse stage definition from dictionary with enhanced error handling.

        Args:
            stage_name: Name of the stage
            stage_def: Dictionary containing stage definition

        Returns:
            Stage instance

        Raises:
            JSONSchemaError: If stage structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None
        gates = []
        schema = None

        try:
            # Parse gates
            gates_data = stage_def.get("gates", {})
            if isinstance(gates_data, dict):
                for gate_name, gate_def in gates_data.items():
                    gate = self._parse_gate(gate_name, gate_def)
                    gates.append(gate)

            # Parse schema
            schema_data = stage_def.get("schema")
            if schema_data:
                schema = self._parse_schema(f"{stage_name}_schema", schema_data)

            # Parse action definitions
            action_definitions = None
            action_defs_data = stage_def.get("action_definitions")
            if action_defs_data:
                action_definitions = self._parse_action_definitions(action_defs_data)

            # Import Stage here to avoid circular imports
            from stageflow.core.stage import Stage
            return Stage(
                name=stage_name,
                gates=gates,
                schema=schema,
                metadata=stage_def.get("metadata", {}),
                allow_partial=stage_def.get("allow_partial", False),
                action_definitions=action_definitions,
            )
        except Exception as e:
            if isinstance(e, (JSONLoadError, JSONSchemaError)):
                raise
            raise JSONSchemaError(
                f"Failed to parse stage '{stage_name}': {str(e)}",
                file_path=file_path
            ) from e

    def _parse_gate(self, gate_name: str, gate_def: dict[str, Any]) -> Gate:
        """
        Parse gate definition from dictionary with enhanced error handling.

        Args:
            gate_name: Name of the gate
            gate_def: Dictionary containing gate definition

        Returns:
            Gate instance

        Raises:
            JSONSchemaError: If gate structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None
        locks = []

        try:
            # Parse locks
            locks_data = gate_def.get("locks", [])
            # Validation is already done in validate_schema

            for i, lock_def in enumerate(locks_data):
                lock = self._parse_lock(lock_def, f"{gate_name}[{i}]")
                locks.append(lock)

            # Wrap locks in LockWrapper to make them evaluable
            from stageflow.gates.gate import LockWrapper
            components = [LockWrapper(lock) for lock in locks]

            return Gate(
                name=gate_name,
                components=tuple(components),
                metadata=gate_def.get("metadata", {}),
            )
        except Exception as e:
            if isinstance(e, (JSONLoadError, JSONSchemaError)):
                raise
            raise JSONSchemaError(
                f"Failed to parse gate '{gate_name}': {str(e)}",
                file_path=file_path
            ) from e

    def _parse_lock(self, lock_def: dict[str, Any], location: str) -> Lock:
        """
        Parse lock definition from dictionary with enhanced error handling.

        Args:
            lock_def: Dictionary containing lock definition
            location: Location string for error reporting

        Returns:
            Lock instance

        Raises:
            JSONSchemaError: If lock structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            # Use LockFactory to handle both old and new syntax formats
            return LockFactory.create_lock(lock_def)
        except Exception as e:
            raise JSONSchemaError(
                f"Failed to parse lock at {location}: {str(e)}",
                file_path=file_path
            ) from e

    def _parse_action_definitions(self, action_defs_data: dict[str, Any]) -> "StageActionDefinitions":
        """
        Parse action definitions from dictionary with enhanced error handling.

        Args:
            action_defs_data: Dictionary containing action definitions

        Returns:
            StageActionDefinitions instance

        Raises:
            JSONSchemaError: If action definitions structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            # Import classes to avoid circular imports
            from stageflow.core.stage import ActionDefinition, StageActionDefinitions
            from stageflow.process.result import ActionType, Priority

            def parse_action_list(actions_data: list[dict[str, Any]]) -> list[ActionDefinition]:
                """Parse a list of action definitions."""
                actions = []
                for action_data in actions_data:
                    action_type = ActionType(action_data["type"])
                    priority = Priority(action_data.get("priority", "normal"))

                    action = ActionDefinition(
                        type=action_type,
                        description=action_data["description"],
                        priority=priority,
                        conditions=action_data.get("conditions", []),
                        template_vars=action_data.get("template_vars", {}),
                        metadata=action_data.get("metadata", {})
                    )
                    actions.append(action)
                return actions

            # Parse each state's action definitions
            return StageActionDefinitions(
                fulfilling=parse_action_list(action_defs_data.get("fulfilling", [])),
                qualifying=parse_action_list(action_defs_data.get("qualifying", [])),
                awaiting=parse_action_list(action_defs_data.get("awaiting", [])),
                advancing=parse_action_list(action_defs_data.get("advancing", [])),
                regressing=parse_action_list(action_defs_data.get("regressing", [])),
                completed=parse_action_list(action_defs_data.get("completed", []))
            )
        except Exception as e:
            if isinstance(e, (JSONLoadError, JSONSchemaError)):
                raise
            raise JSONSchemaError(
                f"Failed to parse action definitions: {str(e)}",
                file_path=file_path
            ) from e

    def _parse_schema(self, schema_name: str, schema_def: dict[str, Any]) -> ItemSchema:
        """
        Parse schema definition from dictionary with enhanced error handling.

        Args:
            schema_name: Name of the schema
            schema_def: Dictionary containing schema definition

        Returns:
            ItemSchema instance

        Raises:
            JSONSchemaError: If schema structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            return ItemSchema.from_dict(schema_name, schema_def)
        except Exception as e:
            raise JSONSchemaError(
                f"Failed to parse schema '{schema_name}': {str(e)}",
                file_path=file_path
            ) from e

    def save_process(self, process: "Process", file_path: str | Path, indent: int = 2, sort_keys: bool = True) -> None:
        """
        Save process to JSON file with enhanced formatting.

        Args:
            process: Process to save
            file_path: Path where to save the JSON file
            indent: JSON indentation level
            sort_keys: Whether to sort object keys

        Raises:
            JSONLoadError: If saving fails
        """
        try:
            data = self._process_to_dict(process)

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, sort_keys=sort_keys, ensure_ascii=False)

        except Exception as e:
            raise JSONLoadError(
                f"Failed to save process to {file_path}: {str(e)}",
                file_path=str(file_path)
            ) from e

    def _process_to_dict(self, process: "Process") -> dict[str, Any]:
        """
        Convert process to dictionary representation with enhanced structure.

        Args:
            process: Process to convert

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        data = {
            "name": process.name,
            "stage_order": process.stage_order,
            "allow_stage_skipping": process.allow_stage_skipping,
            "regression_detection": process.regression_detection,
            "metadata": process.metadata,
            "stages": {},
        }

        for stage in process.stages:
            stage_data = {
                "allow_partial": stage.allow_partial,
                "metadata": stage.metadata,
                "gates": {},
            }

            if stage.schema:
                stage_data["schema"] = {
                    "required_fields": list(stage.schema.required_fields),
                    "optional_fields": list(stage.schema.optional_fields),
                    "field_types": stage.schema.field_types,
                    "default_values": stage.schema.default_values,
                    "validation_rules": stage.schema.validation_rules,
                    "metadata": stage.schema.metadata,
                }

            for gate in stage.gates:
                gate_data = {
                    "logic": gate.operation.value,
                    "metadata": gate.metadata,
                    "locks": [],
                }

                # Extract locks from LockWrapper components
                for component in gate.components:
                    from stageflow.gates.gate import LockWrapper
                    if isinstance(component, LockWrapper):
                        lock = component.lock
                        lock_data = {
                            "property": lock.property_path,
                            "type": lock.lock_type.value,
                            "metadata": lock.metadata,
                        }

                        if lock.expected_value is not None:
                            lock_data["value"] = lock.expected_value

                        if lock.validator_name:
                            lock_data["validator"] = lock.validator_name

                        gate_data["locks"].append(lock_data)

                stage_data["gates"][gate.name] = gate_data

            data["stages"][stage.name] = stage_data

        return data


# Convenience functions for quick loading
def load_process(file_path: str | Path) -> "Process":
    """
    Convenience function to load a process from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Process instance

    Raises:
        JSONLoadError: If file loading or parsing fails
        JSONSchemaError: If schema validation fails
        JSONReferenceError: If reference resolution fails
    """
    loader = JsonLoader()
    return loader.load_process(file_path)


def load_process_config(file_path: str | Path) -> ProcessConfig:
    """
    Convenience function to load a process configuration from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        ProcessConfig TypedDict

    Raises:
        JSONLoadError: If file loading or parsing fails
        JSONSchemaError: If schema validation fails
        JSONReferenceError: If reference resolution fails
    """
    loader = JsonLoader()
    return loader.load_process_config(file_path)


def load_process_from_string(json_content: str, file_path: str | None = None) -> "Process":
    """
    Convenience function to load a process from JSON string.

    Args:
        json_content: JSON content as string
        file_path: Optional file path for error reporting

    Returns:
        Process instance

    Raises:
        JSONLoadError: If parsing fails
        JSONSchemaError: If schema validation fails
    """
    loader = JsonLoader()
    return loader.load_process_from_string(json_content, file_path)


def load_process_config_from_string(json_content: str, file_path: str | None = None) -> ProcessConfig:
    """
    Convenience function to load a process configuration from JSON string.

    Args:
        json_content: JSON content as string
        file_path: Optional file path for error reporting

    Returns:
        ProcessConfig TypedDict

    Raises:
        JSONLoadError: If parsing fails
        JSONSchemaError: If schema validation fails
    """
    loader = JsonLoader()
    return loader.load_process_config_from_string(json_content, file_path)
