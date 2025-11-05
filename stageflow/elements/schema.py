"""JSON Schema generator from StageFlow process definitions."""

import json
from collections import deque
from typing import Any

from ruamel.yaml import YAML

from stageflow.models import StageObjectPropertyDefinition
from stageflow.process import Process


class RequiredFieldAnalyzer:
    """Analyze locks to determine required fields based on EXISTS locks."""

    def analyze_stage(self, stage) -> set[str]:
        """Find all properties with EXISTS locks in stage gates.

        Args:
            stage: Stage object to analyze

        Returns:
            Set of property paths that have EXISTS locks
        """
        required = set()

        for gate in stage.gates:
            lock_dicts = [lock.to_dict() for lock in gate.locks]
            required.update(self._find_exists_locks(lock_dicts))

        return required

    def _find_exists_locks(self, locks: list) -> set[str]:
        """Find all property paths in EXISTS locks (recursive).

        Args:
            locks: List of lock definitions

        Returns:
            Set of property paths marked as required by EXISTS locks
        """
        required = set()

        for lock in locks:
            if not isinstance(lock, dict):
                continue

            # Direct EXISTS shorthand: {exists: "property_path"}
            if "exists" in lock:
                prop = lock["exists"]
                if isinstance(prop, str):
                    required.add(self._clean_property_path(prop))

            # EXISTS type: {type: "EXISTS", property_path: "..."}
            lock_type = lock.get("type")
            if self._is_lock_type(lock_type, "EXISTS"):
                prop = lock.get("property_path")
                if isinstance(prop, str):
                    required.add(self._clean_property_path(prop))

            # Recursive for CONDITIONAL locks
            if self._is_lock_type(lock_type, "CONDITIONAL"):
                required.update(self._find_exists_locks(lock.get("if", [])))
                required.update(self._find_exists_locks(lock.get("then", [])))
                required.update(self._find_exists_locks(lock.get("else", [])))

            # Recursive for OR_LOGIC locks
            if self._is_lock_type(lock_type, "OR_LOGIC"):
                for condition in lock.get("conditions", []):
                    required.update(self._find_exists_locks(condition.get("locks", [])))

        return required

    def _is_lock_type(self, lock_type, expected: str) -> bool:
        """Check if lock type matches expected value (handles both str and enum)."""
        if isinstance(lock_type, str):
            return lock_type.upper() == expected.upper()
        elif hasattr(lock_type, "value"):
            # Handle enum types
            return lock_type.value.upper() == expected.upper()
        return False

    def _clean_property_path(self, path: str) -> str:
        """Clean property path (remove length() wrapper if present).

        Args:
            path: Property path that may be wrapped in length()

        Returns:
            Cleaned property path
        """
        if path.startswith("length(") and path.endswith(")"):
            return path[7:-1]
        return path


class SchemaGenerator:
    """Generate JSON Schemas from StageFlow process definitions.

    Uses Stage.get_schema() as the single source of truth for stage properties.
    """

    def __init__(self, process: Process):
        """Initialize generator with a process.

        Args:
            process: Process object to generate schemas from
        """
        self.process = process
        self.analyzer = RequiredFieldAnalyzer()

    def generate_cumulative_schema(self, target_stage: str) -> dict[str, Any]:
        """Generate cumulative schema from initial stage to target stage.

        Merges schemas from all stages along the path from initial to target.
        Later stages override earlier stages for duplicate properties.

        Args:
            target_stage: Target stage name

        Returns:
            JSON Schema as dictionary

        Raises:
            ValueError: If target_stage doesn't exist or isn't reachable
        """
        # Get path from initial to target stage
        stage_path = self._get_stage_path(target_stage)

        if not stage_path:
            raise ValueError(f"No path found from initial stage to '{target_stage}'")

        # Merge schemas from all stages in path using Stage.get_schema()
        merged_properties = self._merge_stage_schemas(stage_path)

        # Analyze required fields from all stages in path
        required_fields = self._analyze_required_fields(stage_path)

        # Convert to JSON Schema format
        return self._to_json_schema(
            merged_properties,
            required_fields,
            title=f"{self.process.name} - {target_stage} (Cumulative)",
            stage_name=target_stage,
        )

    def generate_stage_schema(self, target_stage: str) -> dict[str, Any]:
        """Generate schema for specific stage only.

        Uses Stage.get_schema() to get the stage's expected_properties.

        Args:
            target_stage: Target stage name

        Returns:
            JSON Schema as dictionary

        Raises:
            ValueError: If target_stage doesn't exist
        """
        stage = self._get_stage(target_stage)

        # Get schema directly from Stage.get_schema()
        stage_schema = stage.get_schema()
        properties = stage_schema or {}

        # Analyze required fields
        required_fields = self.analyzer.analyze_stage(stage)

        return self._to_json_schema(
            properties,
            required_fields,
            title=f"{self.process.name} - {target_stage} (Stage-Specific)",
            stage_name=target_stage,
        )

    def _get_stage_path(self, target_stage: str) -> list[str]:
        """Get ordered list of stage IDs from initial to target using BFS.

        Args:
            target_stage: Target stage name or ID

        Returns:
            List of stage IDs representing the path from initial to target.
            Empty list if no path exists.
        """
        target_stage_obj = self._get_stage(target_stage)

        # Build path using BFS from initial stage
        initial_stage_id = self.process.initial_stage._id
        target_stage_id = target_stage_obj._id

        if initial_stage_id == target_stage_id:
            return [initial_stage_id]

        # BFS to find shortest path
        queue = deque([(initial_stage_id, [initial_stage_id])])
        visited = {initial_stage_id}

        while queue:
            current_id, path = queue.popleft()

            # Find all outgoing gates from current stage
            current_stage = self._get_stage_by_id(current_id)

            for gate in current_stage.gates:
                next_stage_id = gate.target_stage

                if next_stage_id == target_stage_id:
                    return path + [next_stage_id]

                if next_stage_id not in visited:
                    visited.add(next_stage_id)
                    queue.append((next_stage_id, path + [next_stage_id]))

        # No path found
        return []

    def _get_stage(self, stage_name: str):
        """Get stage object by name or ID.

        Args:
            stage_name: Stage name or ID to find

        Returns:
            Stage object

        Raises:
            ValueError: If stage not found
        """
        for stage in self.process.stages:
            if stage.name == stage_name or stage._id == stage_name:
                return stage

        available_stages = [s.name for s in self.process.stages]
        raise ValueError(
            f"Stage '{stage_name}' not found in process. "
            f"Available stages: {available_stages}"
        )

    def _get_stage_by_id(self, stage_id: str):
        """Get stage object by ID only.

        Args:
            stage_id: Stage ID to find

        Returns:
            Stage object

        Raises:
            ValueError: If stage not found
        """
        for stage in self.process.stages:
            if stage._id == stage_id:
                return stage
        raise ValueError(f"Stage ID '{stage_id}' not found")

    def _merge_stage_schemas(
        self, stage_ids: list[str]
    ) -> dict[str, StageObjectPropertyDefinition]:
        """Merge schemas from multiple stages using Stage.get_schema().

        Args:
            stage_ids: List of stage IDs to merge schemas from

        Returns:
            Merged dictionary of properties. Later stages override earlier ones.
        """
        merged = {}

        for stage_id in stage_ids:
            stage = self._get_stage_by_id(stage_id)

            # Use Stage.get_schema() as source of truth
            stage_schema = stage.get_schema()

            if stage_schema:
                # Later stages override earlier stages
                merged.update(stage_schema)

        return merged

    def _analyze_required_fields(self, stage_ids: list[str]) -> set[str]:
        """Analyze required fields from multiple stages based on EXISTS locks.

        Args:
            stage_ids: List of stage IDs to analyze

        Returns:
            Set of property paths that are required
        """
        required = set()

        for stage_id in stage_ids:
            stage = self._get_stage_by_id(stage_id)
            required.update(self.analyzer.analyze_stage(stage))

        return required

    def _to_json_schema(
        self,
        properties: dict[str, StageObjectPropertyDefinition],
        required_fields: set[str],
        title: str,
        stage_name: str,
    ) -> dict[str, Any]:
        """Convert StageFlow properties to JSON Schema format.

        Args:
            properties: Dictionary of property definitions from Stage.get_schema()
            required_fields: Set of required property names (from EXISTS analysis)
            title: Schema title
            stage_name: Stage name for description

        Returns:
            JSON Schema dictionary (Draft-07 compliant)
        """
        schema: dict[str, Any] = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": title,
            "description": f"Schema for stage: {stage_name}",
            "type": "object",
        }

        # Convert expected_properties to JSON Schema properties recursively
        # Pass required_fields to handle nested required fields
        json_properties = self._convert_properties_to_json_schema(
            properties, required_fields
        )

        # Add additional required fields that might not be in expected_properties
        for field_path in required_fields:
            if "." not in field_path and "[" not in field_path:
                # Simple field not in properties
                if field_path not in json_properties:
                    json_properties[field_path] = {"type": "string"}

        schema["properties"] = json_properties

        # Determine required fields at root level
        root_required = self._get_root_required_fields(required_fields)
        if root_required:
            schema["required"] = sorted(root_required)

        return schema

    def _convert_properties_to_json_schema(
        self, props: dict[str, Any], required_fields: set[str] = None, prefix: str = ""
    ) -> dict[str, Any]:
        """Recursively convert StageFlow expected_properties to JSON Schema format.

        Args:
            props: Expected properties dict (may be nested)
            required_fields: Set of required field paths (with dots)
            prefix: Current path prefix for nested properties

        Returns:
            JSON Schema properties dict
        """
        if not props:
            return {}

        if required_fields is None:
            required_fields = set()

        result = {}
        nested_required = []

        for prop_name, prop_def in props.items():
            current_path = f"{prefix}.{prop_name}" if prefix else prop_name

            if prop_def is None:
                # No definition, use string type
                result[prop_name] = {"type": "string"}
            elif isinstance(prop_def, dict):
                # Check if this is a type definition or nested object
                if "type" in prop_def and isinstance(prop_def["type"], str):
                    # This is a leaf property with type
                    json_prop = {"type": self._map_type(prop_def["type"])}
                    if "default" in prop_def:
                        json_prop["default"] = prop_def["default"]
                    result[prop_name] = json_prop
                else:
                    # This is a nested object - recurse
                    nested_props = self._convert_properties_to_json_schema(
                        prop_def, required_fields, current_path
                    )
                    obj_schema = {
                        "type": "object",
                        "properties": nested_props,
                    }

                    # Check if any nested properties are required
                    nested_req = self._get_required_for_path(
                        required_fields, current_path
                    )
                    if nested_req:
                        obj_schema["required"] = sorted(nested_req)

                    result[prop_name] = obj_schema
            else:
                # Unexpected format, use string
                result[prop_name] = {"type": "string"}

            # Check if this property is required at this level
            if current_path in required_fields:
                nested_required.append(prop_name)

        return result

    def _get_required_for_path(
        self, required_fields: set[str], parent_path: str
    ) -> set[str]:
        """Get required field names for properties nested under a parent path.

        Args:
            required_fields: Set of all required field paths
            parent_path: Parent path (e.g., "payment_method")

        Returns:
            Set of property names required under this parent
            (e.g., {"type", "card_number"} for "payment_method")
        """
        required = set()
        prefix = f"{parent_path}."

        for field_path in required_fields:
            if field_path.startswith(prefix):
                # Extract the immediate child property name
                remainder = field_path[len(prefix):]
                # Get first segment (before any dots or brackets)
                if "." in remainder:
                    child_name = remainder.split(".")[0]
                elif "[" in remainder:
                    child_name = remainder.split("[")[0]
                else:
                    child_name = remainder

                required.add(child_name)

        return required

    def _get_root_required_fields(self, required_fields: set[str]) -> set[str]:
        """Extract root-level required fields from dotted paths.

        Args:
            required_fields: Set of required field paths (may include dots)

        Returns:
            Set of root-level field names
        """
        root_fields = set()
        for field_path in required_fields:
            # Extract root field (before first dot or bracket)
            if "." in field_path:
                root_field = field_path.split(".")[0]
            elif "[" in field_path:
                root_field = field_path.split("[")[0]
            else:
                root_field = field_path

            root_fields.add(root_field)

        return root_fields

    def _insert_nested_property(
        self,
        properties: dict[str, Any],
        required: list[str],
        prop_path: str,
        prop_schema: dict[str, Any],
        is_required: bool,
    ) -> None:
        """Insert a property into nested structure, creating intermediate objects.

        Handles dot notation (e.g., "address.city") and array indexing (e.g., "items[0].id").

        Args:
            properties: Properties dictionary to insert into
            required: Required fields list for root level
            prop_path: Property path (may contain dots and array indices)
            prop_schema: JSON Schema for the property
            is_required: Whether this property is required
        """
        # Parse the property path
        parts = self._parse_property_path(prop_path)

        if not parts:
            return

        # For simple properties (no dots), just add directly
        if len(parts) == 1:
            prop_name, _ = parts[0]
            properties[prop_name] = prop_schema
            if is_required and prop_name not in required:
                required.append(prop_name)
            return

        # Navigate/create nested structure for complex paths
        current_props = properties
        current_required = required

        for i, part in enumerate(parts[:-1]):
            prop_name, is_array = part

            # Ensure property exists as a proper JSON Schema object/array
            if prop_name not in current_props:
                # Create object or array schema
                if is_array:
                    current_props[prop_name] = {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }
                    }
                else:
                    current_props[prop_name] = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }
            else:
                # Property exists - ensure it has proper JSON Schema structure
                existing = current_props[prop_name]
                if "properties" not in existing:
                    # Convert to proper JSON Schema object if needed
                    if is_array:
                        current_props[prop_name] = {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            }
                        }
                    else:
                        current_props[prop_name] = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

            # Mark as required at this level if needed
            if i == 0 and is_required and prop_name not in current_required:
                current_required.append(prop_name)

            # Navigate deeper
            prop_obj = current_props[prop_name]
            if is_array:
                # For arrays, work with items schema
                current_props = prop_obj["items"]["properties"]
                current_required = prop_obj["items"]["required"]
            else:
                # For objects, work with properties
                current_props = prop_obj["properties"]
                current_required = prop_obj["required"]

        # Insert the final property
        final_name, _ = parts[-1]
        current_props[final_name] = prop_schema

        # Mark final property as required if needed
        if is_required and final_name not in current_required:
            current_required.append(final_name)

    def _parse_property_path(self, path: str) -> list[tuple[str, bool]]:
        """Parse property path into parts, handling dots and array indices.

        Examples:
            "email" -> [("email", False)]
            "address.city" -> [("address", False), ("city", False)]
            "items[0].id" -> [("items", True), ("id", False)]
            "config.mappings[0].source" -> [("config", False), ("mappings", True), ("source", False)]

        Args:
            path: Property path string

        Returns:
            List of (property_name, is_array) tuples
        """
        import re

        parts = []
        segments = path.split(".")

        for segment in segments:
            # Check if segment has array indexing
            match = re.match(r"^([^\[]+)(\[\d+\])?$", segment)
            if match:
                prop_name = match.group(1)
                has_index = match.group(2) is not None
                parts.append((prop_name, has_index))
            else:
                # Fallback for unexpected format
                parts.append((segment, False))

        return parts

    def _map_type(self, stageflow_type: str) -> str:
        """Map StageFlow type names to JSON Schema types.

        Args:
            stageflow_type: Type string from StageFlow expected_properties

        Returns:
            JSON Schema type string
        """
        type_mapping = {
            "str": "string",
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "array": "array",
            "dict": "object",
            "object": "object",
        }
        return type_mapping.get(stageflow_type.lower(), "string")

    def to_yaml(self, schema: dict[str, Any]) -> str:
        """Convert schema dictionary to YAML string.

        Args:
            schema: JSON Schema dictionary

        Returns:
            YAML formatted string
        """
        yaml_instance = YAML(typ="safe", pure=True)
        yaml_instance.preserve_quotes = True
        yaml_instance.indent(mapping=2, sequence=4, offset=2)

        from io import StringIO

        string_stream = StringIO()
        yaml_instance.dump(schema, string_stream)
        return string_stream.getvalue()

    def to_json(self, schema: dict[str, Any]) -> str:
        """Convert schema dictionary to JSON string.

        Args:
            schema: JSON Schema dictionary

        Returns:
            JSON formatted string with indentation
        """
        return json.dumps(schema, indent=2)
