"""Core Process class for StageFlow multi-stage validation orchestration."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import NotRequired, TypedDict

from .element import Element
from .gate import Gate
from .lock import BaseLock, SimpleLock
from .stage import (
    ExpectedObjectSchmema,
    Stage,
    StageDefinition,
    StageEvaluationResult,
    StageObjectPropertyDefinition,
    StageStatus,
)


class ProcessDefinition(TypedDict):
    """TypedDict for process definition."""

    name: str
    description: str
    stages: dict[str, StageDefinition]
    initial_stage: str
    final_stage: str
    stage_prop: NotRequired[
        str
    ]  # Optional: property path to extract current stage from element


class ProcessElementEvaluationResult(TypedDict):
    """TypedDict for process element evaluation result."""

    stage: str
    stage_result: StageEvaluationResult
    regression: bool


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


class ProcessIssueTypes(StrEnum):
    """Enumeration of process consistency issues types."""

    MISSING_STAGE = "missing_stage"
    INVALID_TRANSITION = "invalid_transition"
    DEAD_END_STAGE = "dead_end_stage"
    UNREACHABLE_STAGE = "unreachable_stage"
    ORPHANED_STAGE = "orphaned_stage"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    LOGICAL_CONFLICT = "logical_conflict"
    MULTIPLE_GATES_SAME_TARGET = "multiple_gates_same_target"
    SELF_REFERENCING_GATE = "self_referencing_gate"


@dataclass(frozen=True)
class ConsistencyIssue:
    issue_type: ProcessIssueTypes
    description: str
    stages: list[str] = field(default_factory=list)


class ProcessConsistencyChecker:
    """Check process configuration for consistency issues."""

    issues: list[ConsistencyIssue]

    def __init__(
        self,
        stages: list[Stage],
        transitions: list[tuple[str, str]],
        initial_stage: Stage,
        final_stage: Stage,
    ):
        self.stages = stages
        self.transitions = transitions
        self.initial_stage = initial_stage
        self.final_stage = final_stage
        self.issues = []
        self.run_checks()

    @property
    def valid(self) -> bool:
        """Indicate if the process is consistent."""
        return len(self.issues) == 0

    def run_checks(self):
        """Perform consistency checks on the process."""
        self._check_dead_end_stages()
        self._check_unreachable_stages()
        self._check_orphaned_stages()
        self._check_self_referencing_gates()
        self._check_circular_dependencies()
        self._check_logical_conflicts()
        self._check_multiple_gates_same_target()

    def _get_path_to_final(self, stage: Stage) -> list[Stage]:
        """Get path from given stage to final stage."""
        if not self.final_stage:
            return []
        search = PathSearch(self.transitions, self.final_stage._id)
        path_ids = list(search.get_path(stage._id) or set())
        return self.get_stages_from_ids(path_ids)

    def get_stages_from_ids(self, ids: list[str]) -> list[Stage]:
        """Retrieve stages by their IDs."""
        return [stage for stage in self.stages if stage._id in ids]

    def _find_route(self, from_stage_id: str, to_stage_id: str) -> list[str] | None:
        """Find a route from one stage to another."""
        search = PathSearch(self.transitions, to_stage_id)
        route = search.get_path(from_stage_id)
        if not route:
            route = search.get_path(to_stage_id, foward=False)
        return list(route) if route else None

    def _check_dead_end_stages(self) -> None:
        """Identify non-final stages that cannot reach the final stage."""
        for stage in self.stages:
            if stage.is_final:
                continue
            path = self._get_path_to_final(stage)

            if not path:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.DEAD_END_STAGE,
                    description=f"Stage '{stage.name}' cannot reach final stage '{self.final_stage.name}'",
                    stages=[stage.name],
                )
                self.issues.append(issue)

    def _check_unreachable_stages(self) -> None:
        """Identify stages that cannot be reached from the initial stage."""
        for stage in self.stages:
            path = self._find_route(self.initial_stage._id, stage._id)
            if not path:
                # Allow unreachable stages if they can reach the final stage
                can_reach_final = bool(self._get_path_to_final(stage))
                if not can_reach_final:
                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.UNREACHABLE_STAGE,
                        description=f"Stage '{stage.name}' is unreachable from initial stage '{self.initial_stage.name}'",
                        stages=[stage.name],
                    )
                    self.issues.append(issue)

    def _check_invalid_transitions(self) -> None:
        """Identify transitions to non-existent stages."""
        stage_ids = {stage._id for stage in self.stages}
        for from_stage, to_stage in self.transitions:
            if from_stage not in stage_ids or to_stage not in stage_ids:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.INVALID_TRANSITION,
                    description=f"Transition from '{from_stage}' to '{to_stage}' involves non-existent stage(s)",
                    stages=[from_stage, to_stage],
                )
                self.issues.append(issue)

    def _check_orphaned_stages(self) -> None:
        """Identify stages that have no gates and are not referenced by other stages."""
        # Get all stages that are referenced as targets by other gates
        target_stages = {target for _, target in self.transitions}

        for stage in self.stages:
            # Skip stages that have gates or are marked as final
            if len(stage.gates) > 0 or stage.is_final:
                continue

            # If a stage has no gates and is not final, it should be referenced as a target
            if stage._id not in target_stages:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.ORPHANED_STAGE,
                    description=f"Stage '{stage.name}' has no gates, is not marked as final, and is not referenced by any other stage",
                    stages=[stage.name],
                )
                self.issues.append(issue)

    def _check_self_referencing_gates(self) -> None:
        """Identify gates that reference their own stage (self-loops)."""
        for stage in self.stages:
            for gate in stage.gates:
                if hasattr(gate, "target_stage") and gate.target_stage == stage._id:
                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.SELF_REFERENCING_GATE,
                        description=f"Gate '{gate.name}' in stage '{stage.name}' references the same stage, creating a self-loop. This can lead to infinite loops and should be avoided",
                        stages=[stage.name],
                    )
                    self.issues.append(issue)

    def _check_circular_dependencies(self) -> None:
        """Identify circular dependencies in stage transitions."""
        visited = set()
        rec_stack = set()

        def has_cycle(stage_id: str) -> bool:
            visited.add(stage_id)
            rec_stack.add(stage_id)

            # Get all outgoing transitions from this stage
            outgoing = [
                target for source, target in self.transitions if source == stage_id
            ]

            for neighbor in outgoing:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.CIRCULAR_DEPENDENCY,
                        description="Circular dependency detected: stages can transition in a cycle without reaching the final stage",
                        stages=list(rec_stack),
                    )
                    self.issues.append(issue)
                    return True

            rec_stack.remove(stage_id)
            return False

        # Check each stage for cycles
        for stage in self.stages:
            if stage._id not in visited:
                has_cycle(stage._id)

    def _check_logical_conflicts(self) -> None:
        """Identify logical conflicts within gate conditions."""
        for stage in self.stages:
            for gate in stage.gates:
                if gate.locks:
                    self._check_gate_logic_conflicts(stage, gate)

    def _check_gate_logic_conflicts(self, stage: Stage, gate: Gate) -> None:
        """Check for logical conflicts within a single gate's locks."""
        # Group locks by property path
        locks_by_property: dict[str, list[BaseLock]] = {}
        for lock in gate.locks:
            prop_path = lock.property_path
            if prop_path not in locks_by_property:
                locks_by_property[prop_path] = []
            locks_by_property[prop_path].append(lock)

        # Check each property for conflicts
        for prop_path, locks in locks_by_property.items():
            conflicts = self._detect_property_conflicts(prop_path, locks)
            if conflicts:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.LOGICAL_CONFLICT,
                    description=f"Gate '{gate.name}' in stage '{stage.name}' has conflicting conditions for property '{prop_path}': {conflicts}",
                    stages=[stage.name],
                )
                self.issues.append(issue)

    def _detect_property_conflicts(self, prop_path: str, locks: list[BaseLock]) -> str:
        """Detect logical conflicts between locks on the same property."""
        from stageflow.lock import LockType

        conflicts = []

        # Filter to only SimpleLocks (ConditionalLocks don't have expected_value)
        simple_locks = [lock for lock in locks if isinstance(lock, SimpleLock)]

        # Check for EQUALS conflicts (multiple different values)
        equals_locks = [lock for lock in simple_locks if lock.lock_type == LockType.EQUALS]
        if len(equals_locks) > 1:
            values = [lock.expected_value for lock in equals_locks]
            unique_values = set(values)
            if len(unique_values) > 1:
                conflicts.append(
                    f"multiple EQUALS conditions ({', '.join(map(str, unique_values))})"
                )

        # Check for numeric range conflicts
        gt_locks = [lock for lock in simple_locks if lock.lock_type == LockType.GREATER_THAN]
        lt_locks = [lock for lock in simple_locks if lock.lock_type == LockType.LESS_THAN]

        # Check EQUALS vs GREATER_THAN conflicts
        for equals_lock in equals_locks:
            if isinstance(equals_lock.expected_value, (int, float)):
                equals_val = equals_lock.expected_value
                for gt_lock in gt_locks:
                    if isinstance(gt_lock.expected_value, (int, float)):
                        if equals_val <= gt_lock.expected_value:
                            conflicts.append(
                                f"EQUALS {equals_val} conflicts with GREATER_THAN {gt_lock.expected_value}"
                            )

        # Check EQUALS vs LESS_THAN conflicts
        for equals_lock in equals_locks:
            if isinstance(equals_lock.expected_value, (int, float)):
                equals_val = equals_lock.expected_value
                for lt_lock in lt_locks:
                    if isinstance(lt_lock.expected_value, (int, float)):
                        if equals_val >= lt_lock.expected_value:
                            conflicts.append(
                                f"EQUALS {equals_val} conflicts with LESS_THAN {lt_lock.expected_value}"
                            )

        # Check GREATER_THAN vs LESS_THAN conflicts
        for gt_lock in gt_locks:
            if isinstance(gt_lock.expected_value, (int, float)):
                for lt_lock in lt_locks:
                    if isinstance(lt_lock.expected_value, (int, float)):
                        if gt_lock.expected_value >= lt_lock.expected_value:
                            conflicts.append(
                                f"GREATER_THAN {gt_lock.expected_value} conflicts with LESS_THAN {lt_lock.expected_value}"
                            )

        return "; ".join(conflicts) if conflicts else ""

    def _check_multiple_gates_same_target(self) -> None:
        """Check for multiple gates targeting the same stage within each stage."""
        for stage in self.stages:
            target_stages = []
            gate_names = []

            for gate in stage.gates:
                if hasattr(gate, "target_stage") and gate.target_stage:
                    if gate.target_stage in target_stages:
                        # Find which gates have the same target
                        duplicate_gates = [
                            gate_names[i]
                            for i, target in enumerate(target_stages)
                            if target == gate.target_stage
                        ]
                        duplicate_gates.append(gate.name)

                        issue = ConsistencyIssue(
                            issue_type=ProcessIssueTypes.MULTIPLE_GATES_SAME_TARGET,
                            description=f"Stage '{stage.name}' has multiple gates targeting the same stage '{gate.target_stage}': "
                            f"{', '.join(duplicate_gates)}. Consider combining these gates into a single gate with multiple locks.",
                        )
                        self.issues.append(issue)

                    target_stages.append(gate.target_stage)
                    gate_names.append(gate.name)


class Process:
    """
    Multi-stage workflow orchestration for element validation.

    Processes define the complete validation pipeline, managing stage
    """

    _transition_map: list[tuple[str, str]]
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
        self.name = config["name"]
        self.description = config.get("description", "")
        self.stage_prop = config.get("stage_prop", None)

        stages_definition = config.get("stages", {})
        initial_stage = config.get("initial_stage", "")
        final_stage = config.get("final_stage", "")
        self._set_stages(stages_definition, initial_stage, final_stage)
        self.checker = self._get_consistency_checker()

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

    def _get_consistency_checker(self) -> ProcessConsistencyChecker:
        """Get a consistency checker for the process."""
        return ProcessConsistencyChecker(
            stages=self.stages,
            transitions=self._transition_map,
            initial_stage=self.initial_stage,
            final_stage=self.final_stage,
        )

    # Path finding methods
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
        stages = [self.get_stage(stage_id) for stage_id in previous_ids]
        return [stage for stage in stages if stage]

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

    @property
    def consistensy_issues(self) -> list[ConsistencyIssue]:
        """Get current consistency issues in the process."""
        return self.checker.issues if self.checker else []

    # Mutation methods
    def add_stage(self, id: str, config: StageDefinition) -> None:
        """Add a new stage to the process."""
        self._add_stage(id, config)
        self.checker = self._get_consistency_checker()

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
        self.checker = self._get_consistency_checker()

    def add_transition(self, from_stage: str, to_stage: str) -> None:
        """Add a transition between two stages."""
        self._transition_map.append((from_stage, to_stage))
        self.checker = self._get_consistency_checker()

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

    def evaluate(
        self, element: Element, current_stage_name: str | None = None
    ) -> ProcessElementEvaluationResult:
        """
        Determine if the element is ready to transition from the current stage.

        The current stage is determined by precedence:
        1. Explicit current_stage_name parameter (highest priority)
        2. Auto-extraction from element using stage_prop configuration
        3. Default to initial_stage (lowest priority)

        Args:
            element: Element to evaluate
            current_stage_name: Optional explicit stage name (overrides auto-extraction)

        Returns:
            ProcessElementEvaluationResult with evaluation details

        Raises:
            ValueError: If process is inconsistent or stage extraction fails
        """
        if self.checker.valid is False:
            raise ValueError(
                "Cannot evaluate element in an inconsistent process configuration"
            )

        # Determine current stage using precedence order
        stage_name = self._extract_current_stage(element, current_stage_name)
        current_stage = self.get_stage(stage_name)

        # This should never happen due to validation in _extract_current_stage
        if not current_stage:
            raise ValueError(f"Stage '{stage_name}' not found in process")

        previous_stages = self._get_previous_stages(current_stage)

        current_stage_result = current_stage.evaluate(element)

        previous_stage_results: list[StageEvaluationResult] = [
            stage.evaluate(element) for stage in previous_stages
        ]
        previus_stage_fails = [
            res
            for res in previous_stage_results
            if res.status != StageStatus.READY_FOR_TRANSITION
        ]
        regresion = len(previus_stage_fails) > 0
        return ProcessElementEvaluationResult(
            stage=current_stage._id,
            stage_result=current_stage_result,
            regression=regresion,
        )

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
