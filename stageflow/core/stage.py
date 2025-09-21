"""Stage definition and validation for StageFlow."""

from dataclasses import dataclass, field
from typing import Any

from stageflow.core.element import Element
from stageflow.gates import Gate, GateResult
from stageflow.process.result import Action, ActionType, Priority
from stageflow.process.schema.core import ItemSchema


@dataclass(frozen=True)
class ActionDefinition:
    """
    Declarative action definition for stage states.

    Defines what actions should be generated when the stage
    is in a specific evaluation state.
    """

    type: ActionType
    description: str
    priority: Priority = Priority.NORMAL
    conditions: list[str] = field(default_factory=list)
    template_vars: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolve_action(self, element: Element, context: dict[str, Any] | None = None) -> Action:
        """
        Resolve this action definition into a concrete Action.

        Args:
            element: The element being evaluated
            context: Additional context for template resolution

        Returns:
            Resolved Action instance
        """
        resolved_description = self._resolve_template(self.description, element, context or {})
        resolved_conditions = [self._resolve_template(cond, element, context or {}) for cond in self.conditions]
        resolved_metadata = {
            key: self._resolve_template(str(value), element, context or {}) if isinstance(value, str) else value
            for key, value in self.metadata.items()
        }

        return Action(
            type=self.type,
            description=resolved_description,
            priority=self.priority,
            conditions=resolved_conditions,
            metadata=resolved_metadata
        )

    def _resolve_template(self, template: str, element: Element, context: dict[str, Any]) -> str:
        """
        Resolve template variables in a string.

        Args:
            template: Template string with variables like {field_name}
            element: Element for property resolution
            context: Additional context variables

        Returns:
            Resolved string
        """
        # Create variable mapping
        variables = {}

        # Add template variables
        for var_name, property_path in self.template_vars.items():
            try:
                value = element.get_property(property_path)
                variables[var_name] = str(value) if value is not None else ""
            except Exception:
                variables[var_name] = ""

        # Add context variables
        variables.update(context)

        # Simple template resolution (can be enhanced with proper templating engine)
        try:
            return template.format(**variables)
        except (KeyError, ValueError):
            return template


@dataclass(frozen=True)
class StageActionDefinitions:
    """
    Collection of action definitions for different stage evaluation states.
    """

    fulfilling: list[ActionDefinition] = field(default_factory=list)
    qualifying: list[ActionDefinition] = field(default_factory=list)
    awaiting: list[ActionDefinition] = field(default_factory=list)
    advancing: list[ActionDefinition] = field(default_factory=list)
    regressing: list[ActionDefinition] = field(default_factory=list)
    completed: list[ActionDefinition] = field(default_factory=list)

    def get_actions_for_state(self, state: str) -> list[ActionDefinition]:
        """Get action definitions for a specific evaluation state."""
        state_map = {
            "fulfilling": self.fulfilling,
            "qualifying": self.qualifying,
            "awaiting": self.awaiting,
            "advancing": self.advancing,
            "regressing": self.regressing,
            "completed": self.completed,
        }
        return state_map.get(state, [])


@dataclass(frozen=True)
class StageResult:
    """Result of stage evaluation against an element."""

    stage_name: str
    schema_valid: bool
    schema_errors: list[str]
    gate_results: dict[str, GateResult]
    overall_passed: bool
    actions: list[str]
    metadata: dict[str, Any]

    @property
    def has_failures(self) -> bool:
        """Check if stage evaluation has any failures."""
        return not self.overall_passed or not self.schema_valid

    @property
    def passed_gates(self) -> list[str]:
        """Get names of gates that passed."""
        return [name for name, result in self.gate_results.items() if result.passed]

    @property
    def failed_gates(self) -> list[str]:
        """Get names of gates that failed."""
        return [name for name, result in self.gate_results.items() if not result.passed]


@dataclass(frozen=True)
class Stage:
    """
    Individual validation stage with schema and gates.

    Stages represent discrete validation points in a process, each with
    their own schema requirements and composed gate validation logic.
    """

    name: str
    gates: list[Gate] = field(default_factory=list)
    schema: ItemSchema | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    allow_partial: bool = False  # Whether partial gate fulfillment is acceptable
    action_definitions: StageActionDefinitions = field(default_factory=StageActionDefinitions)

    def __post_init__(self):
        """Validate stage configuration after initialization."""
        if not self.name:
            raise ValueError("Stage must have a name")

        # Validate no duplicate gate names
        gate_names = [gate.name for gate in self.gates]
        if len(gate_names) != len(set(gate_names)):
            duplicates = {name for name in gate_names if gate_names.count(name) > 1}
            raise ValueError(f"Stage '{self.name}' has duplicate gate names: {duplicates}")

        # Validate gate compatibility
        for i, gate1 in enumerate(self.gates):
            for gate2 in self.gates[i + 1 :]:
                if not gate1.is_compatible_with(gate2):
                    raise ValueError(f"Incompatible gates in stage '{self.name}': {gate1.name}, {gate2.name}")

    def evaluate(self, element: Element) -> StageResult:
        """
        Evaluate element against this stage's requirements.

        Args:
            element: Element to evaluate

        Returns:
            StageResult containing evaluation outcome and details
        """
        # Validate against schema first
        schema_errors = []
        schema_valid = True
        if self.schema:
            schema_errors = self.schema.validate_element(element)
            schema_valid = len(schema_errors) == 0

        # Evaluate each gate
        gate_results = {}
        all_actions = []

        for gate in self.gates:
            gate_result = gate.evaluate(element)
            gate_results[gate.name] = gate_result
            all_actions.extend(gate_result.actions)

        # Determine overall pass/fail
        overall_passed = self._determine_overall_result(gate_results, schema_valid)

        return StageResult(
            stage_name=self.name,
            schema_valid=schema_valid,
            schema_errors=schema_errors,
            gate_results=gate_results,
            overall_passed=overall_passed,
            actions=all_actions,
            metadata=self.metadata.copy(),
        )

    def _determine_overall_result(self, gate_results: dict[str, GateResult], schema_valid: bool) -> bool:
        """
        Determine overall stage result based on gate results and schema validation.

        Args:
            gate_results: Results from gate evaluations
            schema_valid: Whether schema validation passed

        Returns:
            True if stage passes overall, False otherwise
        """
        if not schema_valid:
            return False

        if not gate_results:
            return True  # No gates means stage passes if schema is valid

        if self.allow_partial:
            # At least one gate must pass for partial fulfillment
            return any(result.passed for result in gate_results.values())
        else:
            # All gates must pass for full fulfillment
            return all(result.passed for result in gate_results.values())

    def get_required_properties(self) -> set[str]:
        """
        Get all properties required by this stage.

        Returns:
            Set of property paths required by gates and schema
        """
        properties = set()

        # Add properties from gates
        for gate in self.gates:
            properties.update(gate.get_property_paths())

        # Add properties from schema
        if self.schema:
            properties.update(self.schema.get_all_fields())

        return properties

    def has_gate(self, gate_name: str) -> bool:
        """
        Check if stage contains a specific gate.

        Args:
            gate_name: Name of gate to check

        Returns:
            True if gate exists in stage
        """
        return any(gate.name == gate_name for gate in self.gates)

    def get_gate(self, gate_name: str) -> Gate | None:
        """
        Get gate by name.

        Args:
            gate_name: Name of gate to retrieve

        Returns:
            Gate instance or None if not found
        """
        for gate in self.gates:
            if gate.name == gate_name:
                return gate
        return None

    def is_compatible_with_element(self, element: Element) -> bool:
        """
        Check if element has minimum properties to evaluate this stage.

        Args:
            element: Element to check

        Returns:
            True if element can be evaluated against this stage
        """
        if self.schema:
            # Check required fields from schema
            for field_path in self.schema.required_fields:
                if not element.has_property(field_path):
                    return False

        return True

    def get_completion_percentage(self, element: Element) -> float:
        """
        Calculate completion percentage for this stage.

        Args:
            element: Element to evaluate

        Returns:
            Percentage (0.0 to 1.0) of stage completion
        """
        if not self.gates:
            # No gates means completion is based on schema only
            if self.schema:
                errors = self.schema.validate_element(element)
                return 1.0 if len(errors) == 0 else 0.0
            return 1.0

        stage_result = self.evaluate(element)
        passed_gates = len(stage_result.passed_gates)
        total_gates = len(self.gates)

        gate_percentage = passed_gates / total_gates if total_gates > 0 else 1.0
        schema_percentage = 1.0 if stage_result.schema_valid else 0.0

        # Weight schema and gates equally
        return (gate_percentage + schema_percentage) / 2.0

    def get_summary(self) -> str:
        """
        Get human-readable summary of stage requirements.

        Returns:
            Summary string describing stage composition
        """
        gate_count = len(self.gates)
        schema_desc = f" with schema '{self.schema.name}'" if self.schema else ""
        partial_desc = " (partial fulfillment allowed)" if self.allow_partial else ""

        if gate_count == 0:
            return f"Stage '{self.name}'{schema_desc} with no gates{partial_desc}"

        return f"Stage '{self.name}' with {gate_count} gate(s){schema_desc}{partial_desc}"

    def resolve_actions_for_state(self, state: str, element: Element, context: dict[str, Any] | None = None) -> list[Action]:
        """
        Resolve declarative action definitions for a specific evaluation state.

        Args:
            state: The evaluation state (fulfilling, qualifying, etc.)
            element: The element being evaluated
            context: Additional context for template resolution

        Returns:
            List of resolved Action instances
        """
        action_definitions = self.action_definitions.get_actions_for_state(state)
        return [action_def.resolve_action(element, context) for action_def in action_definitions]

    def has_action_definitions_for_state(self, state: str) -> bool:
        """Check if this stage has action definitions for a specific state."""
        return len(self.action_definitions.get_actions_for_state(state)) > 0
