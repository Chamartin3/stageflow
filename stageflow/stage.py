"""Stage definition and validation for StageFlow."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from .elements import Element
from .gate import Gate, GateResult
from .models import (
    Action,
    ActionDefinition,
    ActionSource,
    ActionType,
    GateDefinition,
    InferredType,
    PropertySchema,
    PropertySource,
    StageDefinition,
    StageSchema,
    StageSchemaMutations,
)


class StageStatus(StrEnum):
    """Stage evaluation status indicating required action.

    Status values are action-oriented and indicate what needs to happen next:
    - INCOMPLETE: Element is missing required properties → Provide data
    - BLOCKED: Element has data but fails validation → Resolve issues
    - READY: Element passes all validation → Transition to next stage

    The new names are more intuitive and action-oriented:
    - "incomplete" clearly indicates missing data
    - "blocked" indicates validation preventing progress
    - "ready" indicates element can move forward

    Examples:
        >>> if status == StageStatus.INCOMPLETE:
        ...     print("Missing required properties")
        >>> elif status == StageStatus.BLOCKED:
        ...     print("Validation failed")
        >>> elif status == StageStatus.READY:
        ...     print("Can transition")
    """
    INCOMPLETE = "incomplete"  # Missing required properties for this stage
    BLOCKED = "blocked"        # Has properties but fails gate validation
    READY = "ready"           # Passes all validation, can transition


@dataclass(frozen=True)
class StageEvaluationResult:
    """Result of stage evaluation against an element.

    Provides comprehensive evaluation results including:
    - status: Evaluation outcome (INCOMPLETE, BLOCKED, or READY)
    - results: Detailed gate validation results
    - actions: Single unified list of actions (configured first priority)
    - validation_messages: Auto-generated messages from validation failures

    Actions follow a "configured first" priority:
    - If stage has expected_actions in YAML, ONLY those are returned (source=configured)
    - Otherwise, actions are computed from the evaluation status (source=computed)

    Action types vary by status:
    - INCOMPLETE: PROVIDE_DATA actions for missing required properties (always computed)
    - BLOCKED: EXECUTE_ACTION (configured) OR RESOLVE_VALIDATION (computed if no configured)
    - READY: TRANSITION action to the next stage (always computed)

    Fields:
        status: Stage evaluation status (INCOMPLETE/BLOCKED/READY)
        results: Map of gate_name → GateResult (detailed validation results)
        actions: Single unified list of Action (configured first priority)
        validation_messages: Generated messages from failed validations

    Examples:
        >>> # INCOMPLETE status (missing properties - always computed)
        >>> StageEvaluationResult(
        ...     status=StageStatus.INCOMPLETE,
        ...     results={},
        ...     actions=[
        ...         Action(
        ...             action_type=ActionType.PROVIDE_DATA,
        ...             source=ActionSource.COMPUTED,
        ...             description="Provide required property 'email'",
        ...             related_properties=[],
        ...             target_properties=["email"],
        ...         )
        ...     ],
        ...     validation_messages=[...]
        ... )

        >>> # BLOCKED status with configured expected_actions
        >>> StageEvaluationResult(
        ...     status=StageStatus.BLOCKED,
        ...     results={"verify_email": GateResult(success=False, ...)},
        ...     actions=[
        ...         Action(
        ...             action_type=ActionType.EXECUTE_ACTION,
        ...             source=ActionSource.CONFIGURED,
        ...             description="Contact support for verification",
        ...             related_properties=["support_ticket"],
        ...             target_properties=["verified"],
        ...             name="contact_support"
        ...         )
        ...     ],
        ...     validation_messages=[...]
        ... )

        >>> # BLOCKED status without configured actions (computed from gates)
        >>> StageEvaluationResult(
        ...     status=StageStatus.BLOCKED,
        ...     results={"verify_email": GateResult(success=False, ...)},
        ...     actions=[
        ...         Action(
        ...             action_type=ActionType.RESOLVE_VALIDATION,
        ...             source=ActionSource.COMPUTED,
        ...             description="Email must be verified",
        ...             related_properties=[],
        ...             target_properties=["verified"],
        ...             gate_name="verify_email"
        ...         )
        ...     ],
        ...     validation_messages=[...]
        ... )

        >>> # READY status (can transition - always computed)
        >>> StageEvaluationResult(
        ...     status=StageStatus.READY,
        ...     results={"verify_email": GateResult(success=True)},
        ...     actions=[
        ...         Action(
        ...             action_type=ActionType.TRANSITION,
        ...             source=ActionSource.COMPUTED,
        ...             description="Ready to transition to 'active'",
        ...             related_properties=[],
        ...             target_properties=[],
        ...             target_stage="active",
        ...             gate_name="verify_email"
        ...         )
        ...     ],
        ...     validation_messages=[...]
        ... )
    """
    status: StageStatus
    results: dict[str, GateResult]       # Gate validation results
    actions: list[Action]                # Single unified actions list (configured first)
    validation_messages: list[str]       # Generated from gate failures




# StageObjectPropertyDefinition, ExpectedObjectSchmema, and StageDefinition
# are now imported from .models above


class Stage:
    """
    Individual validation stage with schema and gates.

    Stages represent discrete validation points in a process, each with
    their own schema requirements and composed gate validation logic.
    """

    name: str
    gates: tuple[Gate, ...]
    stage_actions: list[ActionDefinition]

    def __init__(
        self,
        id: str,
        config: StageDefinition,
    ):
        """
        Initialize Stage with configuration.

        Args:
            id: Unique identifier for the stage
            config: Stage configuration dictionary
        """
        self._id = id
        # Stage name can come from config (if specified) or defaults to the id
        self.name = config.get("name", id)
        self.description = config.get("description", "")

        # Define gates and required properties from those gates
        # Gates can be either a dict (with gate names as keys) or a list
        gates_config = config.get("gates", [])
        if isinstance(gates_config, dict):
            # Convert dict format to list format, adding gate name
            gates_list = [
                {**gate_def, "name": gate_name}
                for gate_name, gate_def in gates_config.items()
            ]
        else:
            gates_list = gates_config

        gates_definition: list[GateDefinition] = [
            cast(
                GateDefinition,
                {
                    **gate_def,
                    "parent_stage": self._id,
                },
            )
            for gate_def in gates_list
        ]
        self.is_final = config.get("is_final", False)
        # Allow stages without gates if they are final or if they are terminal states
        # (We'll validate terminal states at the process level where we have full context)
        if not gates_definition and not self.is_final:
            # This validation will be moved to process level where we can check
            # if this stage is referenced as a target by other gates
            pass
        self.gates = tuple(Gate(definition) for definition in gates_definition)
        self._evaluated_paths = [
            path for gate in self.gates for path in gate.required_paths
        ]

        # Parse new fields property using Pydantic models
        from stageflow.models import PropertiesParser

        fields_spec = config.get("fields", [])
        if fields_spec:
            self._properties = PropertiesParser.parse(fields_spec)
        else:
            self._properties = {}

        # Note: Schema validation disabled to allow gates to add new properties
        # (schema transformation feature). Gate properties can exist outside fields.
        # self._validate_schema(self._properties)

        # Validate action definitions
        actions = config.get("expected_actions", [])
        self._validate_actions(actions)
        self.stage_actions = actions

        # Gate target validation moved to ProcessConsistencyChecker

    @property
    def posible_transitions(self) -> list[str]:
        """Get all possible target stages from this stage's gates."""
        return list({gate.target_stage for gate in self.gates})

    def _validate_schema(self, properties: dict[str, Any]) -> None:
        """Validate that all evaluated paths exist in the fields definition."""
        from stageflow.models import DictProperty, Property

        # Only validate if properties are provided - allow stages without properties
        if not properties:
            return

        for prop_path in self._evaluated_paths:
            parts = prop_path.split(".")
            current = properties

            for i, part in enumerate(parts):
                if part not in current:
                    raise ValueError(
                        f"Gate property '{prop_path}' is not defined in stage '{self.name}' fields"
                    )

                prop = current[part]
                if not isinstance(prop, Property):
                    raise ValueError(
                        f"Invalid property definition for '{part}' in stage '{self.name}'"
                    )

                # If not the last part, must be a DictProperty with nested properties
                if i < len(parts) - 1:
                    if not isinstance(prop, DictProperty) or not prop.properties:
                        raise ValueError(
                            f"Cannot navigate into non-dict property '{part}' in path '{prop_path}'"
                        )
                    current = prop.properties

    def _validate_actions(self, actions: list[ActionDefinition]) -> None:
        """Verify that actions are valid and properly structured.

        Validates:
        - Required 'description' field is present
        - Optional 'name' field is a string if present
        - Optional 'instructions' field is a list of strings if present
        - Action target_properties are evaluated by gates (strict validation)
        - Action related_properties are validated against fields (warning only)
        - Emits warning for duplicate action names
        """
        import warnings

        action_names: set[str] = set()

        # Get all field property names for related_properties validation
        field_names = set(self._properties.keys()) if self._properties else set()

        for idx, action in enumerate(actions):
            # Validate required description field
            if "description" not in action or not action["description"]:
                raise ValueError(
                    f"Action at index {idx} in stage '{self.name}' is missing required 'description' field"
                )

            # Validate optional name field
            if "name" in action:
                name = action["name"]
                if not isinstance(name, str) or not name:
                    raise ValueError(
                        f"Action at index {idx} in stage '{self.name}' has invalid 'name' field: must be non-empty string"
                    )
                # Check for duplicate names (warning, not error)
                if name in action_names:
                    warnings.warn(
                        f"Duplicate action name '{name}' in stage '{self.name}'. "
                        f"Action names should be unique within a stage.",
                        UserWarning,
                        stacklevel=3,
                    )
                action_names.add(name)

            # Validate optional instructions field
            if "instructions" in action:
                instructions = action["instructions"]
                if not isinstance(instructions, list):
                    raise ValueError(
                        f"Action at index {idx} in stage '{self.name}' has invalid 'instructions' field: must be a list"
                    )
                if not all(isinstance(inst, str) for inst in instructions):
                    raise ValueError(
                        f"Action at index {idx} in stage '{self.name}' has invalid 'instructions' field: all items must be strings"
                    )
                # Warn if too many instructions
                if len(instructions) > 10:
                    warnings.warn(
                        f"Action at index {idx} in stage '{self.name}' has {len(instructions)} instructions. "
                        f"Consider keeping instruction lists concise (3-7 items recommended).",
                        UserWarning,
                        stacklevel=3,
                    )

            # Validate related_properties (warning only - these inform the action)
            related_properties = action.get("related_properties", [])
            for prop in related_properties:
                # Check if property exists in fields (using root property name for nested paths)
                root_prop = prop.split(".")[0]
                if root_prop not in field_names and prop not in self._evaluated_paths:
                    warnings.warn(
                        f"Action related_property '{prop}' in stage '{self.name}' is not defined in fields. "
                        f"Consider adding it to the stage fields definition.",
                        UserWarning,
                        stacklevel=3,
                    )

            # Validate target_properties (strict - must be evaluated by gates)
            target_properties = action.get("target_properties", [])
            for prop in target_properties:
                if prop not in self._evaluated_paths:
                    raise ValueError(
                        f"Action target_property '{prop}' is not evaluated by any gate in stage '{self.name}'"
                    )

    def _validate_gate_targets(self) -> None:
        """Validate that no two gates target the same stage."""
        target_stages = []
        gate_names = []

        for gate in self.gates:
            if hasattr(gate, "target_stage") and gate.target_stage:
                if gate.target_stage in target_stages:
                    # Find which gates have the same target
                    duplicate_gates = [
                        gate_names[i]
                        for i, target in enumerate(target_stages)
                        if target == gate.target_stage
                    ]
                    duplicate_gates.append(gate.name)

                    raise ValueError(
                        f"Stage '{self.name}' has multiple gates targeting the same stage '{gate.target_stage}': "
                        f"{', '.join(duplicate_gates)}. Consider combining these gates into a single gate with multiple locks."
                    )

                target_stages.append(gate.target_stage)
                gate_names.append(gate.name)

    def _get_missing_properties(self, element: Element) -> dict[str, Any]:
        """Check for required properties that are missing from the element."""
        from stageflow.models import Property

        missing = {}

        def check_properties(props: dict[str, Property], prefix: str = ""):
            """Recursively check nested properties."""
            from stageflow.models import DictProperty

            for name, prop in props.items():
                full_path = f"{prefix}.{name}" if prefix else name

                # Only check required properties
                if prop.required and not element.has_property(full_path):
                    missing[full_path] = prop.default

                # Recursively check nested dict properties
                if isinstance(prop, DictProperty) and prop.properties:
                    check_properties(prop.properties, full_path)

        check_properties(self._properties)
        return missing

    def _build_actions(
        self,
        status: StageStatus,
        missing_properties: dict[str, Any] | None = None,
        gate_evaluation_results: dict[str, GateResult] | None = None,
        passing_gate: "Gate | None" = None,
        passing_gate_result: GateResult | None = None,
    ) -> list[Action]:
        """Build actions based on evaluation status with "configured first" priority.

        Priority logic:
        - INCOMPLETE: Always compute PROVIDE_DATA actions (no configured option)
        - BLOCKED: If stage has expected_actions, use ONLY those (configured).
                   Otherwise, compute RESOLVE_VALIDATION from failed gates.
        - READY: Always compute TRANSITION action (no configured option)

        Args:
            status: The evaluation status (INCOMPLETE, BLOCKED, or READY)
            missing_properties: Dict of property_path → default_value (for INCOMPLETE)
            gate_evaluation_results: Dict of gate_name → GateResult (for BLOCKED)
            passing_gate: The gate that passed (for READY)
            passing_gate_result: The successful gate result (for READY)

        Returns:
            List of Action appropriate for the given status
        """
        actions: list[Action] = []

        if status == StageStatus.INCOMPLETE and missing_properties:
            # INCOMPLETE: Always compute PROVIDE_DATA actions
            for prop_path, default_value in missing_properties.items():
                action: Action = {
                    "action_type": ActionType.PROVIDE_DATA,
                    "source": ActionSource.COMPUTED,
                    "description": f"Provide required property '{prop_path}'",
                    "related_properties": [],
                    "target_properties": [prop_path],
                }
                if default_value is not None:
                    action["default_value"] = default_value
                actions.append(action)

        elif status == StageStatus.BLOCKED and gate_evaluation_results:
            # BLOCKED: "Configured first" priority
            if self.stage_actions:
                # Stage has configured expected_actions - use ONLY those
                for action_def in self.stage_actions:
                    action: Action = {
                        "action_type": ActionType.EXECUTE_ACTION,
                        "source": ActionSource.CONFIGURED,
                        "description": action_def.get("description", ""),
                        "related_properties": action_def.get("related_properties", []),
                        "target_properties": action_def.get("target_properties", []),
                    }
                    # Include optional fields from configuration
                    if "name" in action_def:
                        action["name"] = action_def["name"]
                    if "instructions" in action_def:
                        action["instructions"] = action_def["instructions"]
                    actions.append(action)
            else:
                # No configured actions - compute from failed gates
                for gate in self.gates:
                    gate_result = gate_evaluation_results.get(gate.name)
                    if gate_result and not gate_result.success:
                        for lock_result in gate_result.failed:
                            action: Action = {
                                "action_type": ActionType.RESOLVE_VALIDATION,
                                "source": ActionSource.COMPUTED,
                                "description": lock_result.error_message
                                or f"Resolve validation for '{lock_result.property_path}'",
                                "related_properties": [],
                                "target_properties": [lock_result.property_path],
                                "gate_name": gate.name,
                            }
                            actions.append(action)

        elif status == StageStatus.READY and passing_gate and passing_gate_result:
            # READY: Always compute TRANSITION action
            validated_properties = [
                lock_result.property_path
                for lock_result in passing_gate_result.passed
            ]
            action: Action = {
                "action_type": ActionType.TRANSITION,
                "source": ActionSource.COMPUTED,
                "description": f"Ready to transition to '{passing_gate.target_stage}'",
                "related_properties": validated_properties,
                "target_properties": [],
                "target_stage": passing_gate.target_stage,
                "gate_name": passing_gate.name,
            }
            actions.append(action)

        return actions

    def evaluate(self, element: Element) -> StageEvaluationResult:
        """
        Evaluate element against this stage's requirements.

        Args:
            element: Element to evaluate

        Returns:
            StageEvaluationResult containing evaluation outcome and details
        """
        missing_properties = self._get_missing_properties(element)
        schema_valid = len(missing_properties) == 0
        if not schema_valid:
            validation_messages = [
                f"Missing required property '{prop}' (suggested default: {default})"
                for prop, default in missing_properties.items()
            ]

            return StageEvaluationResult(
                status=StageStatus.INCOMPLETE,
                results={},
                actions=self._build_actions(
                    status=StageStatus.INCOMPLETE,
                    missing_properties=missing_properties,
                ),
                validation_messages=validation_messages,
            )

        gate_evaluation_results = {}
        for gate in self.gates:
            gate_result = gate.evaluate(element)
            if gate_result.success:
                transition_message = f"Ready to transition to '{gate.target_stage}' via gate '{gate.name}'"

                return StageEvaluationResult(
                    status=StageStatus.READY,
                    results={gate.name: gate_result},
                    actions=self._build_actions(
                        status=StageStatus.READY,
                        passing_gate=gate,
                        passing_gate_result=gate_result,
                    ),
                    validation_messages=[transition_message],
                )
            gate_evaluation_results[gate.name] = gate_result

        # Collect validation messages from failed gates
        validation_messages = []
        for gate in self.gates:
            gate_result = gate_evaluation_results.get(gate.name)
            if gate_result and not gate_result.success:
                # Get contextualized messages for this gate
                contextualized_msgs = gate_result.get_contextualized_messages(
                    gate_name=gate.name, target_stage=gate.target_stage
                )
                validation_messages.extend(contextualized_msgs)

        return StageEvaluationResult(
            status=StageStatus.BLOCKED,
            results=gate_evaluation_results,
            actions=self._build_actions(
                status=StageStatus.BLOCKED,
                gate_evaluation_results=gate_evaluation_results,
            ),
            validation_messages=validation_messages,
        )

    def get_schema(self) -> dict[str, Any]:
        """Extract schema definition for this stage (backward compatible).

        Returns:
            Dictionary representation of field definitions.
            Converts Pydantic Property models back to dict format.
        """
        from stageflow.models import DictProperty, Property

        def property_to_dict(prop: Property) -> dict[str, Any]:
            """Convert a Property model to dict format."""
            # Handle both PropertyType enum and string values
            type_val = prop.type.value if hasattr(prop.type, 'value') else prop.type
            result = {
                "type": type_val,
                "required": prop.required,
            }

            if prop.default is not None:
                result["default"] = prop.default

            if prop.description:
                result["description"] = prop.description

            # Add type-specific fields
            if isinstance(prop, DictProperty) and prop.properties:
                result["properties"] = {
                    name: property_to_dict(p) for name, p in prop.properties.items()
                }

            return result

        return {name: property_to_dict(prop) for name, prop in self._properties.items()}

    def get_initial_schema(self) -> StageSchema:
        """Get schema for stage entry (fields only)."""
        return StageSchema(
            properties=self._fields_to_property_schemas(),
            stage_id=self._id,
            stage_name=self.name
        )

    def get_final_schemas(self) -> dict[str, StageSchema]:
        """Get final schema for each gate (primary method).

        Returns:
            {gate_name: StageSchema}
        """
        return {gate.name: self._build_final_schema(gate) for gate in self.gates}

    def get_final_schema(self, gate_name: str) -> StageSchema:
        """Get final schema for a specific gate.

        Args:
            gate_name: Required - each gate has distinct schema

        Raises:
            ValueError: If gate_name not found
        """
        schemas = self.get_final_schemas()
        if gate_name not in schemas:
            available = list(schemas.keys())
            raise ValueError(f"Gate '{gate_name}' not found. Available: {available}")
        return schemas[gate_name]

    def _fields_to_property_schemas(self) -> dict[str, PropertySchema]:
        """Convert stage fields to PropertySchema dict."""
        from stageflow.models import Property

        result: dict[str, PropertySchema] = {}
        for name, prop in self._properties.items():
            if not isinstance(prop, Property):
                continue
            type_val = prop.type.value if hasattr(prop.type, 'value') else prop.type
            # Map property type to InferredType
            type_mapping = {
                "string": InferredType.STRING,
                "int": InferredType.INTEGER,
                "number": InferredType.NUMBER,
                "bool": InferredType.BOOLEAN,
                "list": InferredType.ARRAY,
                "dict": InferredType.OBJECT,
            }
            inferred = type_mapping.get(type_val, InferredType.ANY)
            schema: PropertySchema = {
                "type": inferred,
                "required": prop.required,
                "source": PropertySource.FIELD,
            }
            if prop.default is not None:
                schema["default"] = prop.default
            if prop.description:
                schema["description"] = prop.description
            result[name] = schema
        return result

    def _build_final_schema(self, gate: Gate) -> StageSchema:
        """Build final schema for a specific gate.

        Merges: initial (fields) + action target_properties + gate lock props
        """
        # 1. Start with initial schema properties
        properties: dict[str, PropertySchema] = dict(self.get_initial_schema()["properties"])

        # 2. Add target_properties from stage_actions (where results are captured)
        for action_def in self.stage_actions:
            target_props = action_def.get("target_properties", [])
            for prop_path in target_props:
                if prop_path not in properties:
                    properties[prop_path] = PropertySchema(
                        type=InferredType.ANY,
                        source=PropertySource.ACTION
                    )

        # 3. Add gate lock properties
        for extracted in gate.get_properties():
            if extracted["path"] not in properties:
                properties[extracted["path"]] = PropertySchema(
                    type=extracted["inferred_type"],
                    source=PropertySource.GATE_LOCK
                )

        return StageSchema(
            properties=properties,
            stage_id=self._id,
            stage_name=self.name
        )

    # Serialization
    def to_dict(self) -> StageDefinition:
        """Serialize stage to dictionary."""
        from stageflow.models import DictProperty

        # Convert Property models to simple field definitions
        def serialize_fields(props: dict[str, Any]) -> dict[str, Any]:
            """Convert Property models to serializable format."""
            result = {}
            for name, prop in props.items():
                if isinstance(prop, DictProperty) and prop.properties:
                    # For nested dict properties, include nested structure
                    result[name] = serialize_fields(prop.properties)
                else:
                    # For simple properties, just include the type
                    type_val = prop.type.value if hasattr(prop.type, 'value') else prop.type
                    result[name] = type_val
            return result

        result: StageDefinition = {
            "name": self.name,
            "description": self.description,
            "gates": [gate.to_dict() for gate in self.gates],
            "expected_actions": self.stage_actions,
            "fields": serialize_fields(self._properties) if self._properties else {},
            "is_final": self.is_final,
        }
        return result

    def to_schema_mutations(self, is_transition_target: bool = False) -> StageSchemaMutations:
        """Convert stage to StageSchemaMutations for analysis.

        Args:
            is_transition_target: Whether this stage is targeted by any gate

        Returns:
            StageSchemaMutations instance for this stage
        """
        return StageSchemaMutations(
            stage_id=self._id,
            is_final=self.is_final,
            initial_schema=self.get_initial_schema(),
            final_schemas=self.get_final_schemas(),
            gates=tuple(g.to_dict() for g in self.gates),
            is_transition_target=is_transition_target,
        )
