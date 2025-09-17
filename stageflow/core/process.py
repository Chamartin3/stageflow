"""Process orchestration for StageFlow."""

from dataclasses import dataclass, field
from typing import Any

from stageflow.core.element import Element
from stageflow.core.result import StatusResult
from stageflow.core.stage import Stage, StageResult


@dataclass(frozen=True)
class Process:
    """
    Multi-stage workflow orchestration for element validation.

    Processes define the complete validation pipeline, managing stage
    transitions and implementing the 7-state evaluation flow.
    """

    name: str
    stages: list[Stage] = field(default_factory=list)
    stage_order: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    allow_stage_skipping: bool = False
    regression_detection: bool = True

    def __post_init__(self):
        """Validate process configuration after initialization."""
        if not self.name:
            raise ValueError("Process must have a name")

        if not self.stages:
            raise ValueError("Process must contain at least one stage")

        # Validate stage names match stage_order
        stage_names = {stage.name for stage in self.stages}
        if self.stage_order:
            order_names = set(self.stage_order)
            if stage_names != order_names:
                missing = stage_names - order_names
                extra = order_names - stage_names
                raise ValueError(f"Stage order mismatch. Missing: {missing}, Extra: {extra}")
        else:
            # Auto-generate stage order from stages list
            object.__setattr__(self, "stage_order", [stage.name for stage in self.stages])

        # Validate no duplicate stage names
        if len(stage_names) != len(self.stages):
            duplicates = []
            seen = set()
            for stage in self.stages:
                if stage.name in seen:
                    duplicates.append(stage.name)
                seen.add(stage.name)
            raise ValueError(f"Duplicate stage names: {duplicates}")

    def evaluate(self, element: Element, current_stage_name: str | None = None) -> StatusResult:
        """
        Evaluate element against process using 7-state flow.

        Args:
            element: Element to evaluate
            current_stage_name: Known current stage (for optimization)

        Returns:
            StatusResult with evaluation outcome
        """
        try:
            # Phase 1: Scoping - determine current stage
            if current_stage_name:
                current_stage = self.get_stage(current_stage_name)
                if not current_stage:
                    return StatusResult.scoping(
                        actions=[f"Invalid current stage: {current_stage_name}"],
                        errors=[f"Stage '{current_stage_name}' not found in process"],
                    )
            else:
                current_stage, scope_result = self._scope_element(element)
                if scope_result:
                    return scope_result

            # Phase 2: Evaluation - assess current stage
            if current_stage:
                stage_result = current_stage.evaluate(element)
                return self._determine_state_from_result(element, current_stage, stage_result)
            else:
                # Element doesn't match any stage - scoping issue
                return StatusResult.scoping(
                    actions=["Element does not match any stage in process"],
                    errors=["Unable to determine appropriate stage for element"],
                )

        except Exception as e:
            return StatusResult.scoping(
                actions=["Process evaluation failed"],
                errors=[f"Evaluation error: {str(e)}"],
            )

    def _scope_element(self, element: Element) -> tuple[Stage | None, StatusResult | None]:
        """
        Determine which stage the element currently belongs to.

        Args:
            element: Element to scope

        Returns:
            Tuple of (current_stage, scoping_result)
            If scoping_result is not None, evaluation should return it immediately
        """
        compatible_stages = []

        # Find stages where element has minimum required properties
        for stage in self.stages:
            if stage.is_compatible_with_element(element):
                compatible_stages.append(stage)

        if not compatible_stages:
            return None, StatusResult.scoping(
                actions=["Ensure element has required properties for at least one stage"],
                errors=["Element lacks required properties for any stage"],
            )

        if len(compatible_stages) == 1:
            return compatible_stages[0], None

        # Multiple compatible stages - use stage order and completion
        best_stage = None
        best_completion = -1.0

        for stage in compatible_stages:
            completion = stage.get_completion_percentage(element)
            stage_index = self.stage_order.index(stage.name)

            # Prefer later stages with higher completion
            score = completion + (stage_index * 0.01)  # Small bonus for later stages

            if score > best_completion:
                best_completion = score
                best_stage = stage

        return best_stage, None

    def _determine_state_from_result(
        self, element: Element, current_stage: Stage, stage_result: StageResult
    ) -> StatusResult:
        """
        Determine evaluation state based on stage result.

        Args:
            element: Element being evaluated
            current_stage: Current stage
            stage_result: Result of stage evaluation

        Returns:
            StatusResult with appropriate state
        """
        current_stage_name = current_stage.name

        # Check for errors first
        if stage_result.has_failures and not current_stage.allow_partial:
            # Element is not meeting stage requirements
            return StatusResult.fulfilling(
                current_stage=current_stage_name,
                actions=stage_result.actions,
                metadata={"completion": current_stage.get_completion_percentage(element)},
                errors=stage_result.schema_errors,
            )

        # Stage requirements are met - check for advancement
        if stage_result.overall_passed:
            next_stage = self._get_next_stage(current_stage_name)

            if not next_stage:
                # No next stage - process is complete
                return StatusResult.completed(
                    metadata={"final_stage": current_stage_name},
                )

            # Check if element can advance to next stage
            if next_stage.is_compatible_with_element(element):
                return StatusResult.advancing(
                    current_stage=current_stage_name,
                    proposed_stage=next_stage.name,
                    metadata={"advancement_ready": True},
                )
            else:
                # Element qualifies for current stage but can't advance yet
                return StatusResult.qualifying(
                    current_stage=current_stage_name,
                    metadata={"next_stage": next_stage.name, "advancement_blocked": True},
                )

        # Partial completion - element is working toward stage completion
        if current_stage.allow_partial and any(result.passed for result in stage_result.gate_results.values()):
            # Some gates passed - awaiting further progress
            return StatusResult.awaiting(
                current_stage=current_stage_name,
                actions=stage_result.actions,
                metadata={"partial_completion": True},
            )

        # Default to fulfilling state
        return StatusResult.fulfilling(
            current_stage=current_stage_name,
            actions=stage_result.actions,
            metadata={"completion": current_stage.get_completion_percentage(element)},
        )

    def get_stage(self, stage_name: str) -> Stage | None:
        """
        Get stage by name.

        Args:
            stage_name: Name of stage to retrieve

        Returns:
            Stage instance or None if not found
        """
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None

    def _get_next_stage(self, current_stage_name: str) -> Stage | None:
        """
        Get the next stage in the process order.

        Args:
            current_stage_name: Name of current stage

        Returns:
            Next stage or None if current is last
        """
        try:
            current_index = self.stage_order.index(current_stage_name)
            if current_index < len(self.stage_order) - 1:
                next_stage_name = self.stage_order[current_index + 1]
                return self.get_stage(next_stage_name)
        except ValueError:
            pass  # Stage not found in order
        return None

    def _get_previous_stage(self, current_stage_name: str) -> Stage | None:
        """
        Get the previous stage in the process order.

        Args:
            current_stage_name: Name of current stage

        Returns:
            Previous stage or None if current is first
        """
        try:
            current_index = self.stage_order.index(current_stage_name)
            if current_index > 0:
                prev_stage_name = self.stage_order[current_index - 1]
                return self.get_stage(prev_stage_name)
        except ValueError:
            pass  # Stage not found in order
        return None

    def get_all_required_properties(self) -> set[str]:
        """
        Get all properties required by any stage in process.

        Returns:
            Set of all property paths required across process
        """
        properties = set()
        for stage in self.stages:
            properties.update(stage.get_required_properties())
        return properties

    def validate_structure(self) -> list[str]:
        """
        Validate process structure for common issues.

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for unreachable stages
        if len(self.stages) > 1:
            # Simple check - ensure all stages after first can be reached
            for i, stage_name in enumerate(self.stage_order[1:], 1):
                prev_stage_name = self.stage_order[i - 1]
                prev_stage = self.get_stage(prev_stage_name)
                current_stage = self.get_stage(stage_name)

                if prev_stage and current_stage:
                    # Check if there's some property overlap for progression
                    prev_props = prev_stage.get_required_properties()
                    curr_props = current_stage.get_required_properties()
                    if not prev_props & curr_props:
                        issues.append(f"Stage '{stage_name}' may be unreachable from '{prev_stage_name}' - no shared properties")

        # Check for dead-end stages (stages that can't advance)
        for stage in self.stages[:-1]:  # Exclude last stage
            next_stage = self._get_next_stage(stage.name)
            if next_stage:
                # Ensure there's some way to progress
                stage_props = stage.get_required_properties()
                next_props = next_stage.get_required_properties()
                if stage_props.isdisjoint(next_props):
                    issues.append(f"Stage '{stage.name}' may create dead-end - no property continuity to '{next_stage.name}'")

        return issues

    def get_process_summary(self) -> str:
        """
        Get human-readable summary of process structure.

        Returns:
            Summary describing process composition
        """
        stage_count = len(self.stages)
        stage_names = " → ".join(self.stage_order)

        return f"Process '{self.name}' with {stage_count} stage(s): {stage_names}"
