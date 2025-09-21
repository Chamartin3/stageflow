"""YAML schema loader for StageFlow with enhanced validation and comment preservation."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stageflow.process.main import Process
    from stageflow.core.stage import Stage

from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from stageflow.gates import Gate, GateOperation, Lock, LockType
from stageflow.process.schema.core import ItemSchema
from stageflow.process.schema.models import (
    ValidationContext,
    validate_stageflow_schema,
)
from stageflow.models import ProcessConfig, StageConfig, LoaderConfig


class YAMLLoadError(Exception):
    """Base exception for YAML loading errors with location information."""

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


class YAMLSchemaError(YAMLLoadError):
    """Exception for schema validation errors during YAML loading."""
    pass


class YAMLIncludeError(YAMLLoadError):
    """Exception for YAML include resolution errors."""
    pass


class YamlLoader:
    """
    Enhanced YAML loader for StageFlow process definitions.

    Provides robust YAML loading with comment preservation, schema validation,
    include support, and detailed error reporting with location information.

    Features:
    - Comment preservation using ruamel.yaml
    - Schema validation during loading
    - YAML include/reference support
    - Precise error location reporting
    - Integration with Process class construction
    """

    def __init__(self, preserve_quotes: bool = True, width: int = 120, use_pydantic_validation: bool = False):
        """Initialize YAML loader with enhanced ruamel configuration.

        Args:
            preserve_quotes: Whether to preserve quote styles in YAML
            width: Maximum line width for YAML output
            use_pydantic_validation: Whether to use pydantic schema validation
        """
        # Use round-trip loader to preserve comments and formatting
        self.yaml = YAML(typ="rt")
        self.yaml.default_flow_style = False
        self.yaml.preserve_quotes = preserve_quotes
        self.yaml.width = width
        self.yaml.map_indent = 2
        self.yaml.sequence_indent = 4
        self.yaml.sequence_dash_offset = 2

        # Register custom constructor for includes
        self.yaml.constructor.add_constructor('!include', self._include_constructor)

        # Track file paths for include resolution
        self._current_file: Path | None = None
        self._include_stack: list[Path] = []

        # Validation configuration
        self.use_pydantic_validation = use_pydantic_validation

    def _include_constructor(self, loader, node):
        """Constructor for !include YAML tag."""
        if self._current_file is None:
            base_path = Path.cwd()
        else:
            base_path = self._current_file.parent

        if isinstance(node, loader.ScalarNode):
            # Simple include: !include "file.yaml"
            include_path = loader.construct_scalar(node)
            return self._load_include_file(base_path / include_path)
        elif isinstance(node, loader.MappingNode):
            # Complex include: !include { file: "file.yaml", key: "section" }
            include_spec = loader.construct_mapping(node)
            include_path = base_path / include_spec["file"]
            included_data = self._load_include_file(include_path)

            if "key" in include_spec:
                key_path = include_spec["key"].split(".")
                result = included_data
                for key in key_path:
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    else:
                        raise YAMLIncludeError(
                            f"Key '{include_spec['key']}' not found in included file {include_path}",
                            file_path=str(include_path)
                        )
                return result
            else:
                return included_data
        else:
            raise YAMLIncludeError(
                "Invalid include specification",
                file_path=str(self._current_file) if self._current_file else None
            )

    def _load_include_file(self, include_path: Path) -> Any:
        """Load an included file with circular dependency check."""
        resolved_path = include_path.resolve()

        # Check for circular dependencies
        if resolved_path in self._include_stack:
            raise YAMLIncludeError(
                f"Circular include dependency detected: {resolved_path}",
                file_path=str(self._current_file) if self._current_file else None
            )

        if not resolved_path.exists():
            raise YAMLIncludeError(
                f"Include file not found: {include_path}",
                file_path=str(self._current_file) if self._current_file else None
            )

        # Load included file
        self._include_stack.append(resolved_path)
        old_current_file = self._current_file
        self._current_file = resolved_path

        try:
            with open(resolved_path, encoding="utf-8") as f:
                return self.yaml.load(f)
        except Exception as e:
            raise YAMLIncludeError(
                f"Failed to load include file {include_path}: {str(e)}",
                file_path=str(resolved_path)
            ) from e
        finally:
            self._include_stack.pop()
            self._current_file = old_current_file

    def load_process(self, file_path: str | Path) -> "Process":
        """
        Load process from YAML file with enhanced error handling.

        Args:
            file_path: Path to YAML file containing process definition

        Returns:
            Process instance created from YAML definition

        Raises:
            YAMLLoadError: If file loading or parsing fails
            YAMLSchemaError: If schema validation fails
            YAMLIncludeError: If include resolution fails
        """
        config = self.load_process_config(file_path)
        return self._config_to_process(config)

    def load_process_config(self, file_path: str | Path) -> ProcessConfig:
        """
        Load process configuration from YAML file.

        Args:
            file_path: Path to YAML file containing process definition

        Returns:
            ProcessConfig TypedDict with validated configuration

        Raises:
            YAMLLoadError: If file loading or parsing fails
            YAMLSchemaError: If schema validation fails
            YAMLIncludeError: If include resolution fails
        """
        path = Path(file_path)
        if not path.exists():
            raise YAMLLoadError(
                f"Process file not found: {file_path}",
                file_path=str(path)
            )

        self._current_file = path.resolve()

        try:
            with open(path, encoding="utf-8") as f:
                data = self.yaml.load(f)
        except (ScannerError, ParserError, ConstructorError) as e:
            line = getattr(e, 'problem_mark', None)
            line_num = line.line + 1 if line else None
            col_num = line.column + 1 if line else None

            raise YAMLLoadError(
                f"YAML parsing error: {e.problem or str(e)}",
                file_path=str(path),
                line=line_num,
                column=col_num
            ) from e
        except Exception as e:
            raise YAMLLoadError(
                f"Failed to read YAML file: {str(e)}",
                file_path=str(path)
            ) from e

        if not isinstance(data, dict):
            raise YAMLSchemaError(
                "YAML file must contain a dictionary at root level",
                file_path=str(path)
            )

        # Validate basic schema structure
        self.validate_schema(data)

        return self._data_to_config(data)

    def load_process_from_string(self, yaml_content: str, file_path: str | None = None) -> "Process":
        """
        Load process from YAML string with enhanced validation.

        Args:
            yaml_content: YAML content as string
            file_path: Optional file path for error reporting

        Returns:
            Process instance created from YAML content

        Raises:
            YAMLLoadError: If parsing fails
            YAMLSchemaError: If schema validation fails
        """
        config = self.load_process_config_from_string(yaml_content, file_path)
        return self._config_to_process(config)

    def load_process_config_from_string(self, yaml_content: str, file_path: str | None = None) -> ProcessConfig:
        """
        Load process configuration from YAML string.

        Args:
            yaml_content: YAML content as string
            file_path: Optional file path for error reporting

        Returns:
            ProcessConfig TypedDict with validated configuration

        Raises:
            YAMLLoadError: If parsing fails
            YAMLSchemaError: If schema validation fails
        """
        try:
            data = self.yaml.load(yaml_content)
        except (ScannerError, ParserError, ConstructorError) as e:
            line = getattr(e, 'problem_mark', None)
            line_num = line.line + 1 if line else None
            col_num = line.column + 1 if line else None

            raise YAMLLoadError(
                f"YAML parsing error: {e.problem or str(e)}",
                file_path=file_path,
                line=line_num,
                column=col_num
            ) from e

        if not isinstance(data, dict):
            raise YAMLSchemaError(
                "YAML content must contain a dictionary at root level",
                file_path=file_path
            )

        # Validate basic schema structure
        self.validate_schema(data)

        return self._data_to_config(data)

    def validate_schema(self, data: dict[str, Any]) -> None:
        """
        Validate YAML data against StageFlow schema requirements.

        Args:
            data: Dictionary containing process definition

        Raises:
            YAMLSchemaError: If schema validation fails
        """
        file_path = str(self._current_file) if self._current_file else None

        if self.use_pydantic_validation:
            try:
                # Transform data to match pydantic expectations
                transformed_data = self._transform_for_pydantic(data)

                # Use comprehensive pydantic validation
                context = ValidationContext(strict_mode=True)
                validated_model = validate_stageflow_schema(transformed_data, context)

                # Log any warnings
                if context.warnings:
                    import warnings
                    for warning in context.warnings:
                        warnings.warn(f"YAML validation warning: {warning}", UserWarning)

            except Exception as e:
                raise YAMLSchemaError(
                    f"Pydantic validation failed: {str(e)}",
                    file_path=file_path
                ) from e
        else:
            # Fall back to legacy validation
            self._validate_schema_legacy(data, file_path)

    def _transform_for_pydantic(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform YAML data to match pydantic model expectations.

        Converts dictionary-based stage/gate/lock definitions to list-based format.
        """
        transformed = data.copy()

        # If there's no process wrapper, wrap the data
        if "process" not in transformed:
            transformed = {"process": transformed}

        process_data = transformed["process"]

        # Transform stages from dict to list format
        if "stages" in process_data and isinstance(process_data["stages"], dict):
            stages_list = []
            for stage_name, stage_def in process_data["stages"].items():
                stage_data = stage_def.copy()
                stage_data["name"] = stage_name

                # Transform gates from dict to list format
                if "gates" in stage_data and isinstance(stage_data["gates"], dict):
                    gates_list = []
                    for gate_name, gate_def in stage_data["gates"].items():
                        gate_data = gate_def.copy()
                        gate_data["name"] = gate_name

                        # Transform gate logic to uppercase
                        if "logic" in gate_data:
                            gate_data["logic"] = gate_data["logic"].upper()

                        # Transform locks to expected format
                        if "locks" in gate_data and isinstance(gate_data["locks"], list):
                            locks_list = []
                            for i, lock_def in enumerate(gate_data["locks"]):
                                lock_data = lock_def.copy()
                                # Add name if not present
                                if "name" not in lock_data:
                                    lock_data["name"] = f"{gate_name}_lock_{i}"
                                # Map 'value' to 'benchmark' if present
                                if "value" in lock_data and "benchmark" not in lock_data:
                                    lock_data["benchmark"] = lock_data.pop("value")
                                locks_list.append(lock_data)
                            gate_data["locks"] = locks_list

                        gates_list.append(gate_data)
                    stage_data["gates"] = gates_list

                # Transform schema to add name if present
                if "schema" in stage_data and isinstance(stage_data["schema"], dict):
                    schema_data = stage_data["schema"].copy()
                    if "name" not in schema_data:
                        schema_data["name"] = f"{stage_name}_schema"

                    # Transform validation_rules from simple strings to dict format
                    if "validation_rules" in schema_data and isinstance(schema_data["validation_rules"], dict):
                        transformed_rules = {}
                        for field, rule in schema_data["validation_rules"].items():
                            if isinstance(rule, str):
                                # Convert simple string rule to dict format
                                transformed_rules[field] = {"validator": rule}
                            else:
                                transformed_rules[field] = rule
                        schema_data["validation_rules"] = transformed_rules

                    stage_data["schema"] = schema_data

                stages_list.append(stage_data)

            process_data["stages"] = stages_list

        return transformed

    def _validate_schema_legacy(self, data: dict[str, Any], file_path: str | None) -> None:
        """Legacy schema validation for backward compatibility."""
        # Required top-level fields
        if "name" not in data:
            raise YAMLSchemaError(
                "Process definition must include 'name' field",
                file_path=file_path
            )

        if not isinstance(data["name"], str) or not data["name"].strip():
            raise YAMLSchemaError(
                "Process 'name' must be a non-empty string",
                file_path=file_path
            )

        # Validate stages structure
        if "stages" in data:
            stages = data["stages"]
            if not isinstance(stages, dict):
                raise YAMLSchemaError(
                    "'stages' must be a dictionary",
                    file_path=file_path
                )

            for stage_name, stage_def in stages.items():
                self._validate_stage_schema(stage_name, stage_def, file_path)

        # Validate stage_order if present
        if "stage_order" in data:
            stage_order = data["stage_order"]
            if not isinstance(stage_order, list):
                raise YAMLSchemaError(
                    "'stage_order' must be a list",
                    file_path=file_path
                )

            if "stages" in data:
                stage_names = set(data["stages"].keys())
                missing_stages = set(stage_order) - stage_names
                if missing_stages:
                    raise YAMLSchemaError(
                        f"stage_order references non-existent stages: {missing_stages}",
                        file_path=file_path
                    )

    def _validate_stage_schema(self, stage_name: str, stage_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual stage schema."""
        if not isinstance(stage_def, dict):
            raise YAMLSchemaError(
                f"Stage '{stage_name}' must be a dictionary",
                file_path=file_path
            )

        # Validate gates if present
        if "gates" in stage_def:
            gates = stage_def["gates"]
            if not isinstance(gates, dict):
                raise YAMLSchemaError(
                    f"Gates in stage '{stage_name}' must be a dictionary",
                    file_path=file_path
                )

            for gate_name, gate_def in gates.items():
                self._validate_gate_schema(stage_name, gate_name, gate_def, file_path)

    def _validate_gate_schema(self, stage_name: str, gate_name: str, gate_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual gate schema."""
        if not isinstance(gate_def, dict):
            raise YAMLSchemaError(
                f"Gate '{gate_name}' in stage '{stage_name}' must be a dictionary",
                file_path=file_path
            )

        # Validate logic if present
        if "logic" in gate_def:
            logic = gate_def["logic"]
            if logic not in ["and", "or", "not"]:
                raise YAMLSchemaError(
                    f"Invalid gate logic '{logic}' in gate '{gate_name}' of stage '{stage_name}'. Must be 'and', 'or', or 'not'",
                    file_path=file_path
                )

        # Validate locks if present
        if "locks" in gate_def:
            locks = gate_def["locks"]
            if not isinstance(locks, list):
                raise YAMLSchemaError(
                    f"Locks in gate '{gate_name}' of stage '{stage_name}' must be a list",
                    file_path=file_path
                )

            for i, lock_def in enumerate(locks):
                self._validate_lock_schema(stage_name, gate_name, i, lock_def, file_path)

    def _validate_lock_schema(self, stage_name: str, gate_name: str, lock_index: int, lock_def: dict[str, Any], file_path: str | None) -> None:
        """Validate individual lock schema."""
        location = f"lock {lock_index} in gate '{gate_name}' of stage '{stage_name}'"

        if not isinstance(lock_def, dict):
            raise YAMLSchemaError(
                f"Lock definition at {location} must be a dictionary",
                file_path=file_path
            )

        # Required fields
        if "property" not in lock_def:
            raise YAMLSchemaError(
                f"Lock at {location} must include 'property' field",
                file_path=file_path
            )

        if "type" not in lock_def:
            raise YAMLSchemaError(
                f"Lock at {location} must include 'type' field",
                file_path=file_path
            )

        # Validate lock type
        lock_type = lock_def["type"]
        valid_types = [t.value for t in LockType]
        if lock_type not in valid_types:
            raise YAMLSchemaError(
                f"Invalid lock type '{lock_type}' at {location}. Valid types: {valid_types}",
                file_path=file_path
            )


    def _data_to_config(self, data: dict[str, Any]) -> ProcessConfig:
        """
        Convert loaded YAML data to ProcessConfig TypedDict.

        Args:
            data: Dictionary containing process definition

        Returns:
            ProcessConfig TypedDict

        Raises:
            YAMLSchemaError: If process structure is invalid
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
            if isinstance(e, (YAMLLoadError, YAMLSchemaError)):
                raise
            raise YAMLSchemaError(
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
            YAMLSchemaError: If conversion fails
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
            raise YAMLSchemaError(
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
            YAMLSchemaError: If stage parsing fails
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

        # Parse logic
        logic_str = gate_config.get("operation", "and").lower()
        try:
            logic = GateOperation(logic_str)
        except ValueError:
            raise YAMLSchemaError(
                f"Invalid gate logic '{logic_str}' for gate '{gate_name}'"
            )

        # Parse locks from components
        components_data = gate_config.get("components", [])
        for i, lock_def in enumerate(components_data):
            lock = self._parse_lock(lock_def, f"{gate_name}[{i}]")
            locks.append(lock)

        # Wrap locks in LockWrapper to make them evaluable
        from stageflow.core.gate import LockWrapper
        components = [LockWrapper(lock) for lock in locks]

        return Gate(
            name=gate_name,
            operation=logic,
            components=components,
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
            YAMLSchemaError: If stage structure is invalid
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
            if isinstance(e, (YAMLLoadError, YAMLSchemaError)):
                raise
            raise YAMLSchemaError(
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
            YAMLSchemaError: If gate structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None
        locks = []

        try:
            # Parse logic
            logic_str = gate_def.get("logic", "and").lower()
            try:
                logic = GateOperation(logic_str)
            except ValueError:
                raise YAMLSchemaError(
                    f"Invalid gate logic '{logic_str}' for gate '{gate_name}'",
                    file_path=file_path
                )

            # Parse locks
            locks_data = gate_def.get("locks", [])
            # Validation is already done in validate_schema

            for i, lock_def in enumerate(locks_data):
                lock = self._parse_lock(lock_def, f"{gate_name}[{i}]")
                locks.append(lock)

            # Wrap locks in LockWrapper to make them evaluable
            from stageflow.core.gate import LockWrapper
            components = [LockWrapper(lock) for lock in locks]

            return Gate(
                name=gate_name,
                operation=logic,
                components=components,
                metadata=gate_def.get("metadata", {}),
            )
        except Exception as e:
            if isinstance(e, (YAMLLoadError, YAMLSchemaError)):
                raise
            raise YAMLSchemaError(
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
            YAMLSchemaError: If lock structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            # Validation is already done in validate_schema
            property_path = lock_def["property"]
            type_str = lock_def["type"].lower()

            try:
                lock_type = LockType(type_str)
            except ValueError:
                raise YAMLSchemaError(
                    f"Invalid lock type '{type_str}' at {location}",
                    file_path=file_path
                )

            expected_value = lock_def.get("value")
            validator_name = lock_def.get("validator")

            return Lock(
                property_path,
                lock_type,
                expected_value,
                validator_name,
                lock_def.get("metadata", {}),
            )
        except Exception as e:
            if isinstance(e, (YAMLLoadError, YAMLSchemaError)):
                raise
            raise YAMLSchemaError(
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
            YAMLSchemaError: If action definitions structure is invalid
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
            if isinstance(e, (YAMLLoadError, YAMLSchemaError)):
                raise
            raise YAMLSchemaError(
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
            YAMLSchemaError: If schema structure is invalid
        """
        file_path = str(self._current_file) if self._current_file else None

        try:
            # Transform validation_rules before parsing
            transformed_def = schema_def.copy()
            if "validation_rules" in transformed_def and isinstance(transformed_def["validation_rules"], dict):
                transformed_rules = {}
                for field, rule in transformed_def["validation_rules"].items():
                    if isinstance(rule, str):
                        # Convert simple string rule to dict format
                        transformed_rules[field] = {"validator": rule}
                    else:
                        transformed_rules[field] = rule
                transformed_def["validation_rules"] = transformed_rules

            return ItemSchema.from_dict(schema_name, transformed_def)
        except Exception as e:
            raise YAMLSchemaError(
                f"Failed to parse schema '{schema_name}': {str(e)}",
                file_path=file_path
            ) from e

    def save_process(self, process: "Process", file_path: str | Path, preserve_formatting: bool = True) -> None:
        """
        Save process to YAML file with comment preservation.

        Args:
            process: Process to save
            file_path: Path where to save the YAML file
            preserve_formatting: Whether to preserve formatting and comments

        Raises:
            YAMLLoadError: If saving fails
        """
        try:
            data = self._process_to_dict(process)

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                if preserve_formatting:
                    # Add header comment
                    f.write(f"# StageFlow Process Definition: {process.name}\n")
                    f.write("# Generated by StageFlow YAML Loader\n\n")

                self.yaml.dump(data, f)

        except Exception as e:
            raise YAMLLoadError(
                f"Failed to save process to {file_path}: {str(e)}",
                file_path=str(file_path)
            ) from e

    def _process_to_dict(self, process: "Process") -> dict[str, Any]:
        """
        Convert process to dictionary representation with enhanced structure.

        Args:
            process: Process to convert

        Returns:
            Dictionary representation suitable for YAML serialization
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
                    from stageflow.core.gate import LockWrapper
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
    Convenience function to load a process from YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Process instance

    Raises:
        YAMLLoadError: If file loading or parsing fails
        YAMLSchemaError: If schema validation fails
        YAMLIncludeError: If include resolution fails
    """
    loader = YamlLoader()
    return loader.load_process(file_path)


def load_process_config(file_path: str | Path) -> ProcessConfig:
    """
    Convenience function to load a process configuration from YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        ProcessConfig TypedDict

    Raises:
        YAMLLoadError: If file loading or parsing fails
        YAMLSchemaError: If schema validation fails
        YAMLIncludeError: If include resolution fails
    """
    loader = YamlLoader()
    return loader.load_process_config(file_path)


def load_process_from_string(yaml_content: str, file_path: str | None = None) -> "Process":
    """
    Convenience function to load a process from YAML string.

    Args:
        yaml_content: YAML content as string
        file_path: Optional file path for error reporting

    Returns:
        Process instance

    Raises:
        YAMLLoadError: If parsing fails
        YAMLSchemaError: If schema validation fails
    """
    loader = YamlLoader()
    return loader.load_process_from_string(yaml_content, file_path)


def load_process_config_from_string(yaml_content: str, file_path: str | None = None) -> ProcessConfig:
    """
    Convenience function to load a process configuration from YAML string.

    Args:
        yaml_content: YAML content as string
        file_path: Optional file path for error reporting

    Returns:
        ProcessConfig TypedDict

    Raises:
        YAMLLoadError: If parsing fails
        YAMLSchemaError: If schema validation fails
    """
    loader = YamlLoader()
    return loader.load_process_config_from_string(yaml_content, file_path)
