"""Core Process class for StageFlow multi-stage validation orchestration."""

from typing import cast

from stageflow.models import (
    Action,
    ActionSource,
    ActionType,
    ConsistencyIssue,
    ExpectedObjectSchmema,
    ProcessDefinition,
    ProcessElementEvaluationResult,
    ProcessGraph,
    ProcessIssueTypes,
    RegressionDetails,
    RegressionPolicy,
    StageDefinition,
    StageObjectPropertyDefinition,
    StageSchemaMutations,
)

from .elements import Element
from .stage import Stage, StageEvaluationResult, StageStatus


class PathSearch:
    transitions: list[tuple[str, str]]
    visited: set[str]
    target: str

    def __init__(self, transitions: list[tuple[str, str]], target: str):
        self.transitions = transitions
        self.visited = set()
        self.target = target

    def get_path(
        self, current: str, foward: bool = True, visited: set[str] | None = None
    ) -> set[str] | None:
        visited = set(visited) if visited else set()
        visited.add(current)
        if current == self.target:
            return visited
        posible_paths = (
            [
                to_stage
                for from_stage, to_stage in self.transitions
                if from_stage == current and to_stage not in visited
            ]
            if foward
            else [
                from_stage
                for from_stage, to_stage in self.transitions
                if to_stage == current and from_stage not in visited
            ]
        )
        if not posible_paths:
            return None  # Dead end

        for path in posible_paths:
            result = self.get_path(path, foward, visited)
            if result:
                return result
        return None





class Process:
    """
    Multi-stage workflow orchestration for element validation.

    Processes define the complete validation pipeline, managing stage
    """

    # Issue types that make the process invalid/unusable
    BLOCKING_ISSUE_TYPES: frozenset[ProcessIssueTypes] = frozenset({
        ProcessIssueTypes.MISSING_STAGE,
        ProcessIssueTypes.INFINITE_CYCLE,
        ProcessIssueTypes.UNREACHABLE_STAGE,
        ProcessIssueTypes.FINAL_STAGE_HAS_GATES,
        ProcessIssueTypes.DUPLICATE_GATE_SCHEMAS,
        ProcessIssueTypes.LOGICAL_CONFLICT,
    })

    _transition_map: list[tuple[str, str]]
    _issues: list[ConsistencyIssue]
    initial_stage: Stage
    final_stage: Stage
    stage_index: set[str]

    def __init__(
        self,
        config: ProcessDefinition,
    ):
        """
        Initialize Process with configuration.

        Args:
            config: Process configuration dictionary
        """
        self.config = config  # Store original config for consistency checker
        self.name = config["name"]
        self.description = config.get("description", "")
        self.stage_prop = config.get("stage_prop", None)

        # Validate regression policy if provided
        regression_policy = config.get("regression_policy", "warn")
        try:
            RegressionPolicy(regression_policy)
        except ValueError as err:
            raise ValueError(
                f"Invalid regression_policy '{regression_policy}'. "
                f"Must be one of: {', '.join([p.value for p in RegressionPolicy])}"
            ) from err
        self.regression_policy = regression_policy

        stages_definition = config.get("stages", {})
        initial_stage = config.get("initial_stage", "")
        final_stage = config.get("final_stage", "")
        self._set_stages(stages_definition, initial_stage, final_stage)
        self._issues = self._run_analysis()

    def _set_stages(
        self, stage_definition: dict[str, StageDefinition], initial: str, final: str
    ) -> None:
        """Validate stages configurations."""
        if not stage_definition or len(stage_definition) < 2:
            raise ValueError("Process must have at least two stages")

        index = stage_definition.keys()
        if not initial or initial not in index:
            raise ValueError(
                f"Process must have a valid initial stage ('{initial}' not found)"
            )
        if not final or final not in index:
            raise ValueError(
                f"Process must have a valid final stage ('{final}' not found)"
            )

        if len(set(index)) != len(index):
            raise ValueError("Process stages must have unique names")
        self._transition_map = []
        self.stages = []
        self._stage_index = set()
        for name in index:
            stage_config = stage_definition[name]
            if not isinstance(stage_config, dict):
                # Handle stages that are None or not dict (e.g., empty YAML entries)
                stage_config = cast(StageDefinition, {})
            is_final = name == final
            stage_config["is_final"] = is_final
            self._add_stage(name, stage_config)
        begin = self.get_stage(initial)
        end = self.get_stage(final)
        if not begin or not end:
            raise ValueError("Initial or final stage not found in stages")
        self.final_stage = end
        self.initial_stage = begin

        # Validate that stages without gates are either final or terminal (referenced by other gates)
        self._validate_terminal_stages()

    def _add_stage(self, id: str, config: StageDefinition) -> None:
        """Add a new stage to the process."""
        stage = Stage(id=id, config=config)
        self.stages.append(stage)
        if id in self._stage_index:
            raise ValueError(f"Duplicate stage id '{id}' in process")
        self._stage_index.add(id)
        for target in stage.posible_transitions:
            self._transition_map.append((id, target))

    def _validate_terminal_stages(self) -> None:
        """Validate that stages without gates are either final or referenced as targets."""
        # Terminal stage validation is now handled by the consistency checker
        # This method is kept for backward compatibility but does nothing
        pass

    def _run_analysis(self) -> list[ConsistencyIssue]:
        """Run process analysis and return issues."""
        from stageflow.analysis import ProcessAnalyzer

        graph = self.to_graph()
        mutations = self._extract_stage_mutations()
        analyzer = ProcessAnalyzer(graph, mutations)
        return analyzer.get_issues()

    def _extract_stage_mutations(self) -> list[StageSchemaMutations]:
        """Extract schema mutations for each stage."""
        targets = {to_id for _, to_id in self._transition_map}
        return [
            stage.to_schema_mutations(is_transition_target=stage._id in targets)
            for stage in self.stages
        ]

    @property
    def issues(self) -> list[ConsistencyIssue]:
        """Get consistency issues in the process."""
        return self._issues

    @property
    def is_valid(self) -> bool:
        """Check if process has no blocking issues."""
        return not any(
            issue.issue_type in self.BLOCKING_ISSUE_TYPES
            for issue in self._issues
        )

    def reanalyze(self) -> list[ConsistencyIssue]:
        """Re-run analysis after mutations and return issues.

        Call this after modifying the process (add_stage, remove_stage, etc.)
        to update the consistency issues.

        Returns:
            Updated list of consistency issues
        """
        self._issues = self._run_analysis()
        return self._issues

    # =========================================================================
    # Path Finding Methods (public API for analyzers)
    # =========================================================================

    def has_path(self, from_stage_id: str, to_stage_id: str, exclude: set[str] | None = None) -> bool:
        """Check if there's a path from one stage to another.

        Args:
            from_stage_id: Starting stage ID
            to_stage_id: Target stage ID
            exclude: Optional set of stage IDs to exclude from path search

        Returns:
            True if path exists, False otherwise
        """
        if from_stage_id == to_stage_id:
            return True

        exclude = exclude or set()
        if from_stage_id in exclude:
            return False

        new_exclude = exclude | {from_stage_id}
        targets = self.get_stage_targets(from_stage_id)

        for target in targets:
            if self.has_path(target, to_stage_id, new_exclude):
                return True
        return False

    def get_stage_targets(self, stage_id: str) -> list[str]:
        """Get direct transition targets from a stage.

        Args:
            stage_id: Stage to get targets for

        Returns:
            List of target stage IDs
        """
        return [to_id for from_id, to_id in self._transition_map if from_id == stage_id]

    def _get_path_to_final(self, stage: Stage) -> list[Stage]:
        """Get path from given stage to final stage."""
        search = PathSearch(self._transition_map, self.final_stage._id)
        path_ids = search.get_path(stage._id) or []
        stages_path = [self.get_stage(stage_id) for stage_id in path_ids]
        return [s for s in stages_path if s]

    def _get_previous_stages(self, current_stage: Stage) -> list[Stage]:
        """Get a path of previous stages leading to the current stage."""
        search = PathSearch(self._transition_map, self.initial_stage._id)
        previous_ids = search.get_path(current_stage._id, foward=False) or []
        # Exclude the current stage itself from previous stages
        stages = [self.get_stage(stage_id) for stage_id in previous_ids if stage_id != current_stage._id]
        return [stage for stage in stages if stage]

    def _check_regression(
        self,
        element: Element,
        current_stage: Stage,
        policy: "RegressionPolicy"
    ) -> "RegressionDetails":
        """
        Check if element has regressed from previous stages.

        Re-evaluates all previous stages in the path and reports which
        stages no longer pass validation.

        Args:
            element: Element being evaluated
            current_stage: Current stage in process
            policy: Regression policy being applied

        Returns:
            RegressionDetails with comprehensive regression information
        """
        previous_stages = self._get_previous_stages(current_stage)

        if not previous_stages:
            # No previous stages, no regression possible
            return RegressionDetails(
                detected=False,
                policy=policy.value,
                failed_stages=[],
                failed_statuses={}
            )

        # Re-evaluate all previous stages
        failed_stages = []
        failed_statuses = {}
        missing_properties = {}
        failed_gates = {}

        for stage in previous_stages:
            result = stage.evaluate(element)

            if result.status != StageStatus.READY:
                failed_stages.append(stage._id)
                failed_statuses[stage._id] = result.status.value

                # Collect details based on status
                if result.status == StageStatus.INCOMPLETE:
                    # Extract missing properties from validation messages
                    missing = self._extract_missing_properties(result)
                    if missing:
                        missing_properties[stage._id] = missing

                elif result.status == StageStatus.BLOCKED:
                    # Extract failed gate names
                    gates = [name for name, res in result.results.items() if not res.success]
                    if gates:
                        failed_gates[stage._id] = gates

        regression_detected = len(failed_stages) > 0

        details = RegressionDetails(
            detected=regression_detected,
            policy=policy.value,
            failed_stages=failed_stages,
            failed_statuses=failed_statuses
        )

        # Add optional fields if present
        if missing_properties:
            details["missing_properties"] = missing_properties
        if failed_gates:
            details["failed_gates"] = failed_gates

        return details

    def _extract_missing_properties(self, result: StageEvaluationResult) -> list[str]:
        """Extract missing property names from INCOMPLETE result."""
        import re
        missing = []
        for msg in result.validation_messages:
            # Parse "Missing required property 'email' ..."
            if "Missing required property" in msg:
                match = re.search(r"'([^']+)'", msg)
                if match:
                    missing.append(match.group(1))
        return missing

    def _format_regression_messages(self, details: RegressionDetails) -> list[str]:
        """Format regression details into user-friendly messages."""
        messages = []

        for stage_id in details["failed_stages"]:
            status = details["failed_statuses"].get(stage_id, "unknown")

            if status == "incomplete":
                props = details.get("missing_properties", {}).get(stage_id, [])
                if props:
                    messages.append(
                        f"Stage '{stage_id}' is missing properties: {', '.join(props)}"
                    )
                else:
                    messages.append(f"Stage '{stage_id}' is incomplete")

            elif status == "blocked":
                gates = details.get("failed_gates", {}).get(stage_id, [])
                if gates:
                    messages.append(
                        f"Stage '{stage_id}' has failed gates: {', '.join(gates)}"
                    )
                else:
                    messages.append(f"Stage '{stage_id}' validation failed")

        return messages

    def _find_route(self, from_stage_id: str, to_stage_id: str) -> list[str] | None:
        """Find a route from one stage to another."""
        search = PathSearch(self._transition_map, to_stage_id)
        route = search.get_path(from_stage_id)
        if not route:
            route = search.get_path(to_stage_id, foward=False)
        return list(route) if route else None

    # Utility methods
    def get_stage(self, stage_id: str) -> Stage | None:
        """Retrieve stage by id."""
        for stage in self.stages:
            if stage._id == stage_id:
                return stage
        return None

    def get_sorted_stages(self) -> list[str]:
        """Get stages in topological order for visualization."""
        visited = set()
        stage_order = []

        def collect_stages(stage_id: str):
            if stage_id in visited or not stage_id:
                return
            visited.add(stage_id)
            stage_order.append(stage_id)

            stage = self.get_stage(stage_id)
            if stage:
                for gate in stage.gates:
                    if hasattr(gate, "target_stage") and gate.target_stage:
                        collect_stages(gate.target_stage)

        # Start from initial stage
        if self.initial_stage:
            collect_stages(self.initial_stage._id)

        # Add remaining stages
        for stage in self.stages:
            if stage._id not in visited:
                stage_order.append(stage._id)

        return stage_order

    def _inject_stage_prop_into_actions(
        self, stage_result: StageEvaluationResult
    ) -> StageEvaluationResult:
        """Inject stage_prop into transition actions if configured.

        When a process has stage_prop configured, transition actions should
        include that property as the first related_property since that's
        what the user needs to update to perform the transition.

        Args:
            stage_result: Original stage evaluation result

        Returns:
            Updated StageEvaluationResult with stage_prop injected
        """
        if not self.stage_prop:
            return stage_result

        if stage_result.status != StageStatus.READY:
            return stage_result

        # Inject stage_prop into transition actions
        updated_actions: list[Action] = []
        for action in stage_result.actions:
            if action["action_type"] == ActionType.TRANSITION:
                # Create new action with stage_prop as first property
                related_props = action["related_properties"]
                if self.stage_prop not in related_props:
                    related_props = [self.stage_prop] + list(related_props)
                else:
                    # Move stage_prop to front if already present
                    related_props = [self.stage_prop] + [
                        p for p in related_props if p != self.stage_prop
                    ]

                # Create updated action with all fields (all required now)
                updated_action: Action = {
                    "action_id": action["action_id"],
                    "name": action["name"],
                    "action_type": action["action_type"],
                    "source": action["source"],
                    "description": action["description"],
                    "instructions": action["instructions"],
                    "related_properties": related_props,
                    "target_properties": action["target_properties"],
                    "related_gates": action["related_gates"],
                    "target_stage": action["target_stage"],
                    "default_value": action["default_value"],
                }
                updated_actions.append(updated_action)
            else:
                updated_actions.append(action)

        return StageEvaluationResult(
            status=stage_result.status,
            results=stage_result.results,
            actions=updated_actions,
            validation_messages=stage_result.validation_messages,
        )

    def evaluate(
        self, element: Element, current_stage_name: str | None = None
    ) -> ProcessElementEvaluationResult:
        """
        Evaluate element in process context.

        Performs two levels of validation:
        1. Stage-level: Can element satisfy current stage? (INCOMPLETE/BLOCKED/READY)
        2. Process-level: Does element still satisfy previous stages? (regression)

        Args:
            element: Element to evaluate
            current_stage_name: Optional explicit stage name

        Returns:
            ProcessElementEvaluationResult with stage result and regression details
        """
        if not self.is_valid:
            raise ValueError(
                "Cannot evaluate element in an inconsistent process configuration"
            )

        # Determine current stage
        stage_name = self._extract_current_stage(element, current_stage_name)
        current_stage = self.get_stage(stage_name)

        if not current_stage:
            raise ValueError(f"Stage '{stage_name}' not found in process")

        # Evaluate current stage
        current_stage_result = current_stage.evaluate(element)

        # Inject stage_prop into transition actions if configured
        current_stage_result = self._inject_stage_prop_into_actions(current_stage_result)

        # Get regression policy
        try:
            policy = RegressionPolicy(self.regression_policy)
        except ValueError:
            # Invalid policy, default to WARN
            policy = RegressionPolicy.WARN

        # Check regression if not ignored
        if policy == RegressionPolicy.IGNORE:
            regression_details = RegressionDetails(
                detected=False,
                policy=policy.value,
                failed_stages=[],
                failed_statuses={}
            )
        else:
            regression_details = self._check_regression(
                element, current_stage, policy
            )

            # If policy is BLOCK and regression detected, override status
            if policy == RegressionPolicy.BLOCK and regression_details["detected"]:
                if current_stage_result.status == StageStatus.READY:
                    # Override to BLOCKED - build appropriate actions
                    blocked_actions: list[Action] = [
                        {
                            "action_type": ActionType.RESOLVE_VALIDATION,
                            "source": ActionSource.COMPUTED,
                            "description": "Resolve regression issues in previous stages",
                            "related_properties": regression_details["failed_stages"],
                            "target_properties": [],
                        }
                    ]
                    current_stage_result = StageEvaluationResult(
                        status=StageStatus.BLOCKED,
                        results=current_stage_result.results,
                        actions=blocked_actions,
                        validation_messages=[
                            "Cannot transition: previous stages have data quality issues",
                            *self._format_regression_messages(regression_details)
                        ]
                    )

        return ProcessElementEvaluationResult(
            stage=current_stage._id,
            stage_result=current_stage_result,  # type: ignore[typeddict-item]
            regression_details=regression_details
        )

    # Mutation methods
    def add_stage(self, id: str, config: StageDefinition) -> None:
        """Add a new stage to the process."""
        self._add_stage(id, config)
        # Update config dict to include new stage for consistency checking
        if "stages" not in self.config:
            self.config["stages"] = {}
        self.config["stages"][id] = config
        self._issues = self._run_analysis()

    def remove_stage(self, stage_name: str) -> None:
        """Remove a stage from the process."""
        stage = self.get_stage(stage_name)
        if not stage:
            raise ValueError(f"Stage '{stage_name}' not found in process")
        if stage.is_final or stage.name == self.initial_stage.name:
            raise ValueError("Cannot remove initial or final stage from process")
        self.stages.remove(stage)
        self._stage_index.remove(stage._id)
        self._transition_map = [
            (from_stage, to_stage)
            for from_stage, to_stage in self._transition_map
            if from_stage != stage._id and to_stage != stage._id
        ]
        self._issues = self._run_analysis()

    def add_transition(self, from_stage: str, to_stage: str) -> None:
        """Add a transition between two stages."""
        self._transition_map.append((from_stage, to_stage))
        self._issues = self._run_analysis()

    def get_schema(
        self, stage_name: str, partial: bool = True
    ) -> ExpectedObjectSchmema:
        """Get schema definition for specified stage.

        Args:
            stage_name: Name of the stage to get schema for
            partial: True for stage-only schema, False for cumulative schema

        Returns:
            Dictionary containing property schema definitions

        Raises:
            ValueError: If stage_name is not found in process
        """
        stage = self.get_stage(stage_name)
        if not stage:
            raise ValueError(f"Stage '{stage_name}' not found in process '{self.name}'")

        if partial:
            return stage.get_schema()

        # Full mode: accumulate properties from all previous stages
        accumulated_properties: dict[str, StageObjectPropertyDefinition | None] = {}
        previous_stages = self._get_previous_stages(stage)

        # Include properties from all previous stages and the current stage
        for prev_stage in previous_stages:
            stage_schema = prev_stage.get_schema()
            if stage_schema:
                accumulated_properties.update(stage_schema)

        # Include current stage properties
        current_schema = stage.get_schema()
        if current_schema:
            accumulated_properties.update(current_schema)

        return accumulated_properties

    # Element evaluation methods
    def _extract_current_stage(
        self, element: Element, stage_override: str | None = None
    ) -> str:
        """
        Determine the current stage for evaluation.

        Precedence order:
        1. Explicit override (stage_override parameter)
        2. Auto-extraction from element (if stage_prop configured)
        3. Default to initial_stage

        Args:
            element: Element being evaluated
            stage_override: Explicit stage override (from CLI -s flag or API call)

        Returns:
            Stage name to use for evaluation

        Raises:
            ValueError: If extracted stage is invalid or doesn't exist
        """
        # Priority 1: Explicit override
        if stage_override is not None:
            return stage_override

        # Priority 2: Auto-extraction from element
        if self.stage_prop:
            try:
                # Use Element's get_property method (same logic as locks)
                extracted_value = element.get_property(self.stage_prop)

                # Validate extracted value
                if extracted_value is None:
                    raise ValueError(
                        f"Stage property '{self.stage_prop}' not found in element"
                    )

                if not isinstance(extracted_value, str):
                    raise ValueError(
                        f"Stage property '{self.stage_prop}' must be a string, "
                        f"got {type(extracted_value).__name__}: {extracted_value}"
                    )

                # Validate stage exists in process
                if not self.get_stage(extracted_value):
                    available_stages = ", ".join(sorted(self._stage_index))
                    raise ValueError(
                        f"Stage '{extracted_value}' extracted from property "
                        f"'{self.stage_prop}' is not a valid stage. "
                        f"Available stages: {available_stages}"
                    )

                return extracted_value

            except Exception as e:
                # Enhance error message with context
                if isinstance(e, ValueError):
                    raise
                raise ValueError(
                    f"Failed to extract stage from property '{self.stage_prop}': {e}"
                ) from e

        # Priority 3: Default to initial_stage
        return self.initial_stage._id

    def evaluate_batch(
        self, elements: list[Element]
    ) -> list[ProcessElementEvaluationResult]:
        """Evaluate multiple elements in batch."""
        return [self.evaluate(element) for element in elements]

    # Serialization methods
    def to_dict(self) -> ProcessDefinition:
        """Serialize process to dictionary."""
        result: dict = {
            "name": self.name,
            "description": self.description,
            "stages": {stage._id: stage.to_dict() for stage in self.stages},
            "initial_stage": self.initial_stage._id,
            "final_stage": self.final_stage._id,
        }

        # Include stage_prop if configured
        if self.stage_prop:
            result["stage_prop"] = self.stage_prop

        return result  # type: ignore

    def to_graph(self) -> ProcessGraph:
        """Convert process to ProcessGraph for analysis.

        Returns:
            ProcessGraph instance representing process topology
        """
        return ProcessGraph(
            edges=tuple(self._transition_map),
            initial_id=self.initial_stage._id,
            final_id=self.final_stage._id,
            stage_ids=frozenset(s._id for s in self.stages),
            stages_with_gates=frozenset(s._id for s in self.stages if s.gates),
        )
