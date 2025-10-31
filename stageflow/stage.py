"""Stage definition and validation for StageFlow."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, NotRequired, Required, TypedDict

from .element import Element
from .gate import Gate, GateDefinition, GateResult


class TemplateParameter(TypedDict, total=False):
    """Parameter definition for template.

    Fields:
        name: Parameter identifier
        required: Whether this parameter is mandatory
        description: What this parameter represents
        placeholder: Example/placeholder value
    """

    name: str  # Required: Parameter identifier
    required: bool  # Required: Whether mandatory
    description: str  # Required: Parameter description
    placeholder: NotRequired[str]  # Optional: Placeholder value


class TemplateSectionDef(TypedDict, total=False):
    """Content section definition in template.

    Fields:
        id: Section identifier
        title: Section heading text
        level: Heading level (1-6)
        content: Default/placeholder content
        subsections: Nested subsections (recursive)
    """

    id: str  # Required: Section identifier
    title: str  # Required: Section heading
    level: int  # Required: Heading level (1-6)
    content: NotRequired[str]  # Optional: Default content
    subsections: NotRequired[list["TemplateSectionDef"]]  # Optional: Nested sections


class StageTemplate(TypedDict, total=False):
    """Stage template definition.

    Fields:
        name: Unique template identifier
        description: What this template is for
        parameters: Parameter definitions
        frontmatter: Default frontmatter values
        sections: Default section structures
    """

    name: Required[str]  # Required: Template identifier
    description: Required[str]  # Required: Template purpose
    parameters: NotRequired[list[TemplateParameter]]  # Optional: Parameters
    frontmatter: NotRequired[dict[str, Any]]  # Optional: Default frontmatter
    sections: NotRequired[list[TemplateSectionDef]]  # Optional: Default sections


class ActionDefinition(TypedDict):
    """TypedDict for action definition with enhanced structure.

    Fields:
        description: Brief summary of what the action accomplishes (required)
        name: Optional unique identifier for the action within the stage
        instructions: Optional list of guidelines for completing the action
        related_properties: Optional list of property paths involved in this action
        template: Optional reference to a template by name
    """

    description: str  # Required: Brief summary
    name: NotRequired[str]  # Optional: Action identifier
    instructions: NotRequired[list[str]]  # Optional: List of guidelines
    related_properties: NotRequired[list[str]]  # Optional: Related property paths
    template: NotRequired[str]  # Optional: Template reference


class ActionType(StrEnum):
    UPDATE = "update"  # The opject needs to update properties to meet gate requirements
    TRANSITION = "transition"  # The object is ready to transition
    EXCECUTE = "execute"  # An external action is required to meet gate requirements


@dataclass(frozen=True)
class Action:
    """Action that can be taken to help an element progress through stages."""

    description: str
    related_properties: list[str]
    action_type: ActionType
    target_stage: str | None = None


class StageStatus(StrEnum):
    INVALID_SCHEMA = "invalid_schema"  # The element is missing required properties for this stage | scoping
    READY_FOR_TRANSITION = "ready"  # A gate has passed and the element can transition to the next stage | done
    ACTION_REQUIRED = "action_required"  # The element has not met gate requirements and requires action | in progress


@dataclass(frozen=True)
class StageEvaluationResult:
    """Result of stage evaluation against an element."""

    status: StageStatus
    gate_results: dict[str, GateResult]
    sugested_action: list[Action]


class StageObjectPropertyDefinition(TypedDict):
    type: str | None
    default: Any | None


ExpectedObjectSchmema = dict[str, StageObjectPropertyDefinition | None] | None


class StageDefinition(TypedDict, total=False):
    """TypedDict for stage definition."""

    name: Required[str]  # Required
    description: Required[str]  # Required
    gates: Required[list[GateDefinition]]  # Required
    expected_actions: Required[list[ActionDefinition]]  # Required
    expected_properties: Required[ExpectedObjectSchmema]  # Required
    is_final: Required[bool]  # Required
    templates: NotRequired[list[StageTemplate]]  # Optional: Stage templates


class Stage:
    """
    Individual validation stage with schema and gates.

    Stages represent discrete validation points in a process, each with
    their own schema requirements and composed gate validation logic.
    """

    name: str
    gates: tuple[Gate, ...]
    stage_actions: list[ActionDefinition]
    templates: list[StageTemplate]

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
        self.name = config["name"]
        self.description = config.get("description", "")

        # Define gates and required properties from those gates
        gates_definition: list[GateDefinition] = [
            {
                **gate_def,
                "parent_stage": self._id,
            }
            for gate_def in config.get("gates", [])
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

        # define object schema for rquiered properties
        expected_properties = config.get("expected_properties", {})
        self._validate_schema(expected_properties)
        self._base_schema = expected_properties

        # Validate and store templates
        templates = config.get("templates", [])
        self._validate_templates(templates)
        self.templates = templates

        # Validate action definitions (must come after templates validation)
        actions = config.get("expected_actions", [])
        self._validate_actions(actions)
        self.stage_actions = actions

        # Gate target validation moved to ProcessConsistencyChecker

    @property
    def posible_transitions(self) -> list[str]:
        """Get all possible target stages from this stage's gates."""
        return list({gate.target_stage for gate in self.gates})

    def _validate_schema(self, shape: ExpectedObjectSchmema) -> None:
        """Validate that all evaluated paths exist in the expected properties schema."""
        # Only validate if schema is provided - allow stages without schemas
        if not shape:
            return

        for prop_path in self._evaluated_paths:
            nested = shape
            for part in prop_path.split("."):
                if nested is None or part not in nested:
                    raise ValueError(
                        f"Gate property '{prop_path}' is not defined in stage '{self.name}' schema"
                    )
                nested = nested[part]

    def _validate_templates(self, templates: list[StageTemplate]) -> None:
        """Validate template definitions.

        Validates:
        - Required fields (name, description)
        - Parameter structure and uniqueness
        - Section structure and uniqueness
        - Section level validity (1-6)
        - Warns if too many templates (>5)
        """
        import warnings

        # Warn if too many templates
        if len(templates) > 5:
            warnings.warn(
                f"Stage '{self.name}' has {len(templates)} templates. "
                f"Consider keeping template count reasonable (2-5 recommended).",
                UserWarning,
                stacklevel=3,
            )

        template_names: set[str] = set()

        for idx, template in enumerate(templates):
            # Validate required fields
            if "name" not in template or not template["name"]:
                raise ValueError(
                    f"Template at index {idx} in stage '{self.name}' is missing required 'name' field"
                )
            if "description" not in template or not template["description"]:
                raise ValueError(
                    f"Template at index {idx} in stage '{self.name}' is missing required 'description' field"
                )

            # Check for duplicate template names
            template_name = template["name"]
            if template_name in template_names:
                raise ValueError(
                    f"Duplicate template name '{template_name}' in stage '{self.name}'. "
                    f"Template names must be unique within a stage."
                )
            template_names.add(template_name)

            # Validate parameters if present
            if "parameters" in template:
                param_names: set[str] = set()
                for param_idx, param in enumerate(template["parameters"]):
                    if "name" not in param or not param["name"]:
                        raise ValueError(
                            f"Parameter at index {param_idx} in template '{template_name}' "
                            f"of stage '{self.name}' is missing required 'name' field"
                        )
                    if "required" not in param:
                        raise ValueError(
                            f"Parameter '{param['name']}' in template '{template_name}' "
                            f"of stage '{self.name}' is missing required 'required' field"
                        )
                    if "description" not in param or not param["description"]:
                        raise ValueError(
                            f"Parameter '{param['name']}' in template '{template_name}' "
                            f"of stage '{self.name}' is missing required 'description' field"
                        )

                    # Check for duplicate parameter names
                    param_name = param["name"]
                    if param_name in param_names:
                        raise ValueError(
                            f"Duplicate parameter name '{param_name}' in template '{template_name}' "
                            f"of stage '{self.name}'"
                        )
                    param_names.add(param_name)

            # Validate sections if present
            if "sections" in template:
                self._validate_template_sections(
                    template["sections"], template_name, template_name
                )

            # Validate frontmatter alignment with expected_properties (warning only)
            if "frontmatter" in template and self._base_schema:
                for prop_path in self._base_schema:
                    if prop_path.startswith("frontmatter."):
                        prop_name = prop_path.split(".", 1)[1]
                        if prop_name not in template["frontmatter"]:
                            warnings.warn(
                                f"Template '{template_name}' in stage '{self.name}' "
                                f"is missing expected frontmatter property '{prop_name}'",
                                UserWarning,
                                stacklevel=3,
                            )

    def _validate_template_sections(
        self,
        sections: list[TemplateSectionDef],
        template_name: str,
        section_path: str,
    ) -> None:
        """Recursively validate template section structure.

        Args:
            sections: List of section definitions to validate
            template_name: Name of the template being validated
            section_path: Current path in section hierarchy (for error messages)
        """
        section_ids: set[str] = set()

        for idx, section in enumerate(sections):
            # Validate required fields
            if "id" not in section or not section["id"]:
                raise ValueError(
                    f"Section at index {idx} in template '{template_name}' "
                    f"of stage '{self.name}' (path: {section_path}) is missing required 'id' field"
                )
            if "title" not in section or not section["title"]:
                raise ValueError(
                    f"Section '{section.get('id', idx)}' in template '{template_name}' "
                    f"of stage '{self.name}' (path: {section_path}) is missing required 'title' field"
                )
            if "level" not in section:
                raise ValueError(
                    f"Section '{section['id']}' in template '{template_name}' "
                    f"of stage '{self.name}' (path: {section_path}) is missing required 'level' field"
                )

            # Validate level range
            level = section["level"]
            if not isinstance(level, int) or level < 1 or level > 6:
                raise ValueError(
                    f"Section '{section['id']}' in template '{template_name}' "
                    f"of stage '{self.name}' (path: {section_path}) has invalid level {level}. "
                    f"Level must be an integer between 1 and 6."
                )

            # Check for duplicate section IDs
            section_id = section["id"]
            if section_id in section_ids:
                raise ValueError(
                    f"Duplicate section ID '{section_id}' in template '{template_name}' "
                    f"of stage '{self.name}' (path: {section_path})"
                )
            section_ids.add(section_id)

            # Recursively validate subsections if present
            if "subsections" in section and section["subsections"]:
                new_path = f"{section_path}.{section_id}"
                self._validate_template_sections(
                    section["subsections"], template_name, new_path
                )

    def _validate_actions(self, actions: list[ActionDefinition]) -> None:
        """Verify that actions are valid and properly structured.

        Validates:
        - Required 'description' field is present
        - Optional 'name' field is a string if present
        - Optional 'instructions' field is a list of strings if present
        - Optional 'template' field references an existing template
        - Action related properties are evaluated by gates
        - Emits warning for duplicate action names
        """
        import warnings

        action_names: set[str] = set()
        template_names = {t["name"] for t in self.templates}

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

            # Validate optional template field
            if "template" in action:
                template_ref = action["template"]
                if not isinstance(template_ref, str) or not template_ref:
                    raise ValueError(
                        f"Action at index {idx} in stage '{self.name}' has invalid 'template' field: must be non-empty string"
                    )
                # Validate template reference exists
                if template_ref not in template_names:
                    raise ValueError(
                        f"Action at index {idx} in stage '{self.name}' references unknown template '{template_ref}'. "
                        f"Available templates: {', '.join(sorted(template_names)) if template_names else 'none'}"
                    )

            # Validate related properties
            properties = action.get("related_properties", [])
            for prop in properties:
                if prop not in self._evaluated_paths:
                    raise ValueError(
                        f"Action property '{prop}' is not evaluated by any gate in stage '{self.name}'"
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
        """Contains the requies propesties."""
        missing = {}
        for prop_path, definition in (self._base_schema or {}).items():
            if not element.has_property(prop_path):
                suggested = definition.get("default") if definition else None
                missing[prop_path] = suggested
        return missing

    def evaluate(self, element: Element) -> StageEvaluationResult:
        """
        Evaluate element against this stage's requirements.

        Args:
            element: Element to evaluate

        Returns:
            StageResult containing evaluation outcome and details
        """
        missing_properties = self._get_missing_properties(element)
        schema_valid = len(missing_properties) == 0
        if not schema_valid:
            actions = [
                Action(
                    description=f"Add missing property '{prop}' with suggested default '{default}'",
                    related_properties=[prop],
                    action_type=ActionType.UPDATE,
                )
                for prop, default in missing_properties.items()
            ]

            return StageEvaluationResult(
                status=StageStatus.INVALID_SCHEMA,
                gate_results={},
                sugested_action=actions,
            )
        gate_evaluation_results = {}
        for gate in self.gates:
            gate_result = gate.evaluate(element)
            if gate_result.success:
                transition_action = Action(
                    description=f"Element is ready to transition to {gate.target_stage} via gate '{gate.name}'",
                    related_properties=[],
                    action_type=ActionType.TRANSITION,
                    target_stage=gate.target_stage,
                )
                return StageEvaluationResult(
                    status=StageStatus.READY_FOR_TRANSITION,
                    gate_results={gate.name: gate_result},
                    sugested_action=[transition_action],
                )
            gate_evaluation_results[gate.name] = gate_result

        gate_actions = []
        for action_def in self.stage_actions:
            action = Action(
                description=action_def["description"],
                related_properties=action_def.get("related_properties", []),
                action_type=ActionType.EXCECUTE,
            )
            gate_actions.append(action)

        # Add contextualized gate failure messages grouped by gate
        for gate in self.gates:
            gate_result = gate_evaluation_results.get(gate.name)
            if gate_result and not gate_result.success:
                # Get contextualized messages for this gate
                contextualized_msgs = gate_result.get_contextualized_messages(
                    gate_name=gate.name, target_stage=gate.target_stage
                )
                # Add each message as an action
                for message in contextualized_msgs:
                    gate_actions.append(
                        Action(
                            description=message,
                            related_properties=[],
                            action_type=ActionType.EXCECUTE,
                        )
                    )
        return StageEvaluationResult(
            status=StageStatus.ACTION_REQUIRED,
            gate_results=gate_evaluation_results,
            sugested_action=gate_actions,
        )

    def get_schema(self) -> ExpectedObjectSchmema:
        """Extract schema definition for this stage.

        Returns:
            ExpectedObjectSchmema with existing StageFlow type definitions.
            Schema includes type information from expected_properties.
        """
        import copy

        return copy.deepcopy(self._base_schema)

    # Serialization
    def to_dict(self) -> StageDefinition:
        """Serialize stage to dictionary."""
        result: StageDefinition = {
            "name": self.name,
            "description": self.description,
            "gates": [gate.to_dict() for gate in self.gates],
            "expected_actions": self.stage_actions,
            "expected_properties": self._base_schema,
            "is_final": self.is_final,
        }
        if self.templates:
            result["templates"] = self.templates
        return result
