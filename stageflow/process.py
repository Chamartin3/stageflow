"""Core Process class for StageFlow multi-stage validation orchestration."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict

from .element import Element
from .stage import Stage, StageDefinition, StageEvaluationResult, StageStatus


class ProcessDefinition(TypedDict):
    """TypedDict for process definition."""

    name: str
    description: str
    stages: dict[str,StageDefinition]
    initial_stage: str
    final_stage: str


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
            self,
            current: str,
            foward:bool=True,
            visited: set[str] | None = None
            ) -> set[str] | None:

        visited = set(visited) if visited else set()
        visited.add(current)
        if current == self.target:
            return visited
        posible_paths = [
            to_stage for from_stage, to_stage in self.transitions
            if from_stage == current and to_stage not in visited
        ] if foward else [
            from_stage for from_stage, to_stage in self.transitions
            if to_stage == current and from_stage not in visited
        ]
        if not posible_paths:
            return None # Dead end

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
            final_stage: Stage
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

    def _get_path_to_final(self, stage:Stage) -> list[Stage]:
        """Get path from given stage to final stage."""
        if not self.final_stage:
            return []
        search = PathSearch(self.transitions, self.final_stage.name)
        path_names = list(search.get_path(stage.name) or set())
        return self.get_stages_from_names(path_names)

    def get_stages_from_names(self, names: list[str]) -> list[Stage]:
        """Retrieve stages by their names."""
        return [stage for stage in self.stages if stage.name in names]

    def _find_route(self, from_stage: str, to_stage: str) -> list[str] | None:
        """Find a route from one stage to another."""
        search = PathSearch(self.transitions, to_stage)
        route = search.get_path(from_stage)
        if not route:
            route = search.get_path(to_stage, foward=False)
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
                    stages=[stage.name]
                )
                self.issues.append(issue)

    def _check_unreachable_stages(self) -> None:
        """Identify stages that cannot be reached from the initial stage."""
        for stage in self.stages:
            path = self._find_route(self.initial_stage.name, stage.name)
            if not path:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.UNREACHABLE_STAGE,
                    description=f"Stage '{stage.name}' is unreachable from initial stage '{self.initial_stage.name}'",
                    stages=[stage.name]
                )
                self.issues.append(issue)

    def _check_invalid_transitions(self) -> None:
        """Identify transitions to non-existent stages."""
        stage_names = {stage.name for stage in self.stages}
        for from_stage, to_stage in self.transitions:
            if from_stage not in stage_names or to_stage not in stage_names:
                issue = ConsistencyIssue(
                    issue_type=ProcessIssueTypes.INVALID_TRANSITION,
                    description=f"Transition from '{from_stage}' to '{to_stage}' involves non-existent stage(s)",
                    stages=[from_stage, to_stage]
                )
                self.issues.append(issue)



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

        stages_definition = config.get("stages", {})
        initial_stage = config.get("initial_stage", "")
        final_stage = config.get("final_stage", "")
        self._set_stages(stages_definition, initial_stage, final_stage)
        self.checker = self._get_consistency_checker()

    def _set_stages(self, stage_definition:dict[str,StageDefinition], initial:str, final:str) -> None:
        """Validate stages configurations."""
        if not stage_definition or len(stage_definition) < 2:
            raise ValueError("Process must have at least two stages")

        index = stage_definition.keys()
        if not initial or initial not in index:
            raise ValueError(f"Process must have a valid initial stage ('{initial}' not found)")
        if not final or final not in index:
            raise ValueError(f"Process must have a valid final stage ('{final}' not found)")

        if len(set(index)) != len(index):
            raise ValueError("Process stages must have unique names")
        self._transition_map = []
        self.stages = []
        self._stage_index = set()
        for name in index:
            stage_config = stage_definition[name]
            is_final = name == final
            stage_config['is_final'] = is_final
            self._add_stage(name, stage_config)
        begin = self.get_stage(initial)
        end = self.get_stage(final)
        if not begin or not end:
            raise ValueError("Initial or final stage not found in stages")
        self.final_stage = end
        self.initial_stage = begin

    def _add_stage(self, id: str, config: StageDefinition) -> None:
        """Add a new stage to the process."""
        stage = Stage(id=id, config=config)
        self.stages.append(stage)
        if id in self._stage_index:
            raise ValueError(f"Duplicate stage id '{id}' in process")
        self.stage_index.add(id)
        for target in stage.posible_transitions:
            self._transition_map.append((id, target))

    def _get_consistency_checker(self) -> ProcessConsistencyChecker:
        """Get a consistency checker for the process."""
        return ProcessConsistencyChecker(
            stages=self.stages,
            transitions=self._transition_map,
            initial_stage=self.initial_stage,
            final_stage=self.final_stage
        )

    # Path finding methods
    def _get_path_to_final(self, stage:Stage) -> list[Stage]:
        """Get path from given stage to final stage."""
        search = PathSearch(self._transition_map, self.final_stage.name)
        path_names = search.get_path(stage.name) or []
        stages_path = [self.get_stage(name ) for name in path_names]
        return [s for s in stages_path if s]

    def _get_previous_stages(self, current_stage: Stage) -> list[Stage]:
        """Get a path of previous stages leading to the current stage."""
        search = PathSearch(self._transition_map, self.initial_stage.name)
        previous_names = search.get_path(current_stage.name, foward=False) or []
        stages =  [self.get_stage(name) for name in previous_names]
        return [stage for stage in stages if stage]

    def _find_route(self, from_stage: str, to_stage: str) -> list[str] | None:
        """Find a route from one stage to another."""
        search = PathSearch(self._transition_map, to_stage)
        route = search.get_path(from_stage)
        if not route:
            route = search.get_path(to_stage, foward=False)
        return list(route) if route else None

    # Utility methods
    def get_stage(self, stage_name: str) -> Stage | None:
        """Retrieve stage by name."""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None

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
        self.stage_index.remove(stage.name)
        self._transition_map = [
            (from_stage, to_stage) for from_stage, to_stage in self._transition_map
            if from_stage != stage.name and to_stage != stage.name
        ]
        self.checker = self._get_consistency_checker()

    def add_transition(self, from_stage: str, to_stage: str) -> None:
        """Add a transition between two stages."""
        self._transition_map.append((from_stage, to_stage))
        self.checker = self._get_consistency_checker()

    # Element evaluation methods
    def evaluate(self, element: Element, current_stage_name: str | None = None) -> ProcessElementEvaluationResult:
        """
         Determine the if the element is ready to transition from the current stage.
        """
        if self.checker.valid is False:
            raise ValueError("Cannot evaluate element in an inconsistent process configuration")

        current_stage = self.get_stage(current_stage_name or "") or self.initial_stage
        previous_stages = self._get_previous_stages(current_stage)

        current_stage_result = current_stage.evaluate(element)

        previous_stage_results: list[StageEvaluationResult] = [
            stage.evaluate(element) for stage in previous_stages
        ]
        previus_stage_fails = [ res
            for res  in previous_stage_results
            if res.status != StageStatus.READY_FOR_TRANSITION
        ]
        regresion = len(previus_stage_fails) > 0
        return ProcessElementEvaluationResult(
            stage=current_stage.name,
            stage_result=current_stage_result,
            regression=regresion
        )

    def evaluate_batch(self, elements: list[Element]) -> list[ProcessElementEvaluationResult]:
        """Evaluate multiple elements in batch."""
        return [self.evaluate(element) for element in elements]

    # Serialization methods
    def to_dict(self) -> ProcessDefinition:
        """Serialize process to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "stages": {stage.name: stage.to_dict() for stage in self.stages},
            "initial_stage": self.initial_stage.name,
            "final_stage": self.final_stage.name,
        }
