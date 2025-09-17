"""YAML schema loader for StageFlow."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stageflow.core.gate import Gate, GateLogic
from stageflow.core.lock import Lock, LockType
from stageflow.core.process import Process
from stageflow.core.schema import ItemSchema
from stageflow.core.stage import Stage


class YamlLoader:
    """
    YAML loader for StageFlow process definitions.

    Loads and parses YAML files containing process definitions,
    converting them into StageFlow core objects.
    """

    def __init__(self):
        """Initialize YAML loader with ruamel configuration."""
        self.yaml = YAML(typ="safe")
        self.yaml.default_flow_style = False

    def load_process(self, file_path: str) -> Process:
        """
        Load process from YAML file.

        Args:
            file_path: Path to YAML file containing process definition

        Returns:
            Process instance created from YAML definition

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML structure is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Process file not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            data = self.yaml.load(f)

        if not isinstance(data, dict):
            raise ValueError("YAML file must contain a dictionary at root level")

        return self._parse_process(data)

    def load_process_from_string(self, yaml_content: str) -> Process:
        """
        Load process from YAML string.

        Args:
            yaml_content: YAML content as string

        Returns:
            Process instance created from YAML content

        Raises:
            ValueError: If YAML structure is invalid
        """
        data = self.yaml.load(yaml_content)

        if not isinstance(data, dict):
            raise ValueError("YAML content must contain a dictionary at root level")

        return self._parse_process(data)

    def _parse_process(self, data: dict[str, Any]) -> Process:
        """
        Parse process definition from dictionary.

        Args:
            data: Dictionary containing process definition

        Returns:
            Process instance
        """
        if "name" not in data:
            raise ValueError("Process definition must include 'name' field")

        name = data["name"]
        stages = []
        stage_order = data.get("stage_order", [])

        # Parse stages
        stages_data = data.get("stages", {})
        if not isinstance(stages_data, dict):
            raise ValueError("'stages' must be a dictionary")

        for stage_name, stage_def in stages_data.items():
            stage = self._parse_stage(stage_name, stage_def)
            stages.append(stage)

        # If no explicit order provided, use the order from stages dict
        if not stage_order:
            stage_order = list(stages_data.keys())

        # Validate stage order references existing stages
        stage_names = {stage.name for stage in stages}
        missing_stages = set(stage_order) - stage_names
        if missing_stages:
            raise ValueError(f"Stage order references non-existent stages: {missing_stages}")

        return Process(
            name=name,
            stages=stages,
            stage_order=stage_order,
            metadata=data.get("metadata", {}),
            allow_stage_skipping=data.get("allow_stage_skipping", False),
            regression_detection=data.get("regression_detection", True),
        )

    def _parse_stage(self, stage_name: str, stage_def: dict[str, Any]) -> Stage:
        """
        Parse stage definition from dictionary.

        Args:
            stage_name: Name of the stage
            stage_def: Dictionary containing stage definition

        Returns:
            Stage instance
        """
        gates = []
        schema = None

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

        return Stage(
            name=stage_name,
            gates=gates,
            schema=schema,
            metadata=stage_def.get("metadata", {}),
            allow_partial=stage_def.get("allow_partial", False),
        )

    def _parse_gate(self, gate_name: str, gate_def: dict[str, Any]) -> Gate:
        """
        Parse gate definition from dictionary.

        Args:
            gate_name: Name of the gate
            gate_def: Dictionary containing gate definition

        Returns:
            Gate instance
        """
        locks = []

        # Parse logic
        logic_str = gate_def.get("logic", "and").lower()
        try:
            logic = GateLogic(logic_str)
        except ValueError:
            raise ValueError(f"Invalid gate logic '{logic_str}' for gate '{gate_name}'")

        # Parse locks
        locks_data = gate_def.get("locks", [])
        if not isinstance(locks_data, list):
            raise ValueError(f"'locks' must be a list in gate '{gate_name}'")

        for i, lock_def in enumerate(locks_data):
            lock = self._parse_lock(lock_def, f"{gate_name}[{i}]")
            locks.append(lock)

        return Gate(
            name=gate_name,
            locks=locks,
            logic=logic,
            metadata=gate_def.get("metadata", {}),
        )

    def _parse_lock(self, lock_def: dict[str, Any], location: str) -> Lock:
        """
        Parse lock definition from dictionary.

        Args:
            lock_def: Dictionary containing lock definition
            location: Location string for error reporting

        Returns:
            Lock instance
        """
        if "property" not in lock_def:
            raise ValueError(f"Lock at {location} must include 'property' field")

        if "type" not in lock_def:
            raise ValueError(f"Lock at {location} must include 'type' field")

        property_path = lock_def["property"]
        type_str = lock_def["type"].lower()

        try:
            lock_type = LockType(type_str)
        except ValueError:
            raise ValueError(f"Invalid lock type '{type_str}' at {location}")

        expected_value = lock_def.get("value")
        validator_name = lock_def.get("validator")

        return Lock(
            property_path=property_path,
            lock_type=lock_type,
            expected_value=expected_value,
            validator_name=validator_name,
            metadata=lock_def.get("metadata", {}),
        )

    def _parse_schema(self, schema_name: str, schema_def: dict[str, Any]) -> ItemSchema:
        """
        Parse schema definition from dictionary.

        Args:
            schema_name: Name of the schema
            schema_def: Dictionary containing schema definition

        Returns:
            ItemSchema instance
        """
        return ItemSchema.from_dict(schema_name, schema_def)

    def save_process(self, process: Process, file_path: str):
        """
        Save process to YAML file.

        Args:
            process: Process to save
            file_path: Path where to save the YAML file
        """
        data = self._process_to_dict(process)

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            self.yaml.dump(data, f)

    def _process_to_dict(self, process: Process) -> dict[str, Any]:
        """
        Convert process to dictionary representation.

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
                    "logic": gate.logic.value,
                    "metadata": gate.metadata,
                    "locks": [],
                }

                for lock in gate.locks:
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


# Convenience function for quick loading
def load_process(file_path: str) -> Process:
    """
    Convenience function to load a process from YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Process instance
    """
    loader = YamlLoader()
    return loader.load_process(file_path)
