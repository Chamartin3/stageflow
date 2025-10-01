"""
ProcessEvaluationPipeline for orchestrating StageFlow evaluation steps.

This module provides a clean pipeline that orchestrates the evaluation process
using the state machine and strategy components, replacing the monolithic
Process.evaluate() method.
"""

from typing import TYPE_CHECKING, Any

from stageflow.element import Element
from stageflow.process.result import (
    Action,
    ActionType,
    EvaluationState,
    Priority,
    StatusResult,
)

from .state_machine import EvaluationContext, ProcessStateMachine
from .strategies import (
    DefaultGateEvaluationStrategy,
    DefaultStageEvaluationStrategy,
    GateEvaluationStrategy,
    StageEvaluationStrategy,
)

if TYPE_CHECKING:
    from stageflow.process.main import Process


class ProcessEvaluationPipeline:
    """
    Orchestrates evaluation steps with clear separation of concerns.

    This pipeline replaces the monolithic Process.evaluate() method with
    a modular approach that separates state machine logic, stage evaluation,
    and gate evaluation into distinct, testable components.
    """

    def __init__(
        self,
        state_machine: ProcessStateMachine | None = None,
        stage_strategy: StageEvaluationStrategy | None = None,
        gate_strategy: GateEvaluationStrategy | None = None
    ):
        """
        Initialize the evaluation pipeline.

        Args:
            state_machine: State machine for evaluation flow (uses default if None)
            stage_strategy: Strategy for stage evaluation (uses default if None)
            gate_strategy: Strategy for gate evaluation (uses default if None)
        """
        self.state_machine = state_machine or ProcessStateMachine()
        self.stage_strategy = stage_strategy or DefaultStageEvaluationStrategy()
        self.gate_strategy = gate_strategy or DefaultGateEvaluationStrategy()

    def evaluate(self, element: Element, process: "Process", current_stage_name: str | None = None) -> StatusResult:
        """
        Evaluate element against process using modular pipeline.

        Args:
            element: Element to evaluate
            process: Process to evaluate against
            current_stage_name: Known current stage (for optimization)

        Returns:
            StatusResult with evaluation outcome
        """
        try:
            element_id = self._get_element_id(element)

            # Phase 1: Stage Resolution (Scoping)
            current_stage, scoping_error = self._resolve_current_stage(
                element, process, current_stage_name
            )

            if scoping_error:
                return scoping_error

            # Phase 2: Stage Evaluation
            stage_result = None
            if current_stage:
                stage_result = current_stage.evaluate(element)

            # Phase 3: Context Building
            context = self._build_evaluation_context(
                element, element_id, current_stage, stage_result, process
            )

            # Phase 4: State Determination
            evaluation_state = self.state_machine.determine_state(context)

            # Phase 5: Action Generation
            actions = self.state_machine.get_next_actions(evaluation_state, context)

            # Phase 6: Result Composition
            result = self._compose_result(evaluation_state, context, actions)

            # Phase 7: History Recording (if enabled)
            self._record_history(process, element, result)

            return result

        except Exception as e:
            # Error handling
            element_id = self._get_element_id(element)
            return self._create_error_result(element_id, e)

    def _resolve_current_stage(
        self,
        element: Element,
        process: "Process",
        current_stage_name: str | None
    ) -> tuple[Any, StatusResult | None]:
        """
        Resolve the current stage for the element.

        Returns:
            Tuple of (current_stage, error_result)
            If error_result is not None, evaluation should return it immediately
        """
        if current_stage_name:
            current_stage = process.get_stage(current_stage_name)
            if not current_stage:
                element_id = self._get_element_id(element)
                invalid_stage_action = Action(
                    type=ActionType.MANUAL_REVIEW,
                    description=f"Invalid current stage: {current_stage_name}",
                    priority=Priority.HIGH
                )
                return None, StatusResult.create(
                    state=EvaluationState.SCOPING,
                    element_id=element_id,
                    actions=[invalid_stage_action],
                    errors=[f"Stage '{current_stage_name}' not found in process"],
                )
            return current_stage, None
        else:
            # Use strategy to find best matching stage
            current_stage = self.stage_strategy.find_best_matching_stage(
                element, process.stages
            )
            return current_stage, None

    def _build_evaluation_context(
        self,
        element: Element,
        element_id: str,
        current_stage: Any,
        stage_result: Any,
        process: "Process"
    ) -> EvaluationContext:
        """Build evaluation context with all necessary information."""
        context = EvaluationContext(
            element=element,
            element_id=element_id,
            current_stage=current_stage,
            stage_result=stage_result
        )

        if current_stage:
            # Determine if this is the final stage
            context.is_final_stage = self._is_final_stage(current_stage.name, process)

            # Get next stage if not final
            if not context.is_final_stage:
                context.next_stage = self._get_next_stage(current_stage.name, process)

                # Check if element can advance to next stage
                if context.next_stage:
                    context.can_advance, context.advance_errors = self._validate_stage_progression(
                        element, current_stage.name, context.next_stage.name, process
                    )

            # Get completion percentage
            context.completion_percentage = current_stage.get_completion_percentage(element)

        return context

    def _compose_result(
        self,
        evaluation_state: EvaluationState,
        context: EvaluationContext,
        actions: list[Action]
    ) -> StatusResult:
        """Compose the final StatusResult."""
        metadata = self.state_machine.get_state_metadata(evaluation_state, context)

        return StatusResult.create(
            state=evaluation_state,
            element_id=context.element_id,
            current_stage=context.current_stage.name if context.current_stage else None,
            proposed_stage=context.next_stage.name if context.next_stage else None,
            actions=actions,
            metadata=metadata
        )

    def _record_history(self, process: "Process", element: Element, result: StatusResult) -> None:
        """Record state transition in element history if enabled."""
        if hasattr(process, '_record_state_transition'):
            try:
                evaluation_time = 0.001  # Placeholder - could be measured
                process._record_state_transition(
                    element,
                    None,  # Previous state not tracked in this refactor
                    result.state.value,
                    result.current_stage,
                    "Pipeline Evaluation",
                    evaluation_time
                )
            except Exception:
                # Don't fail evaluation due to history recording issues
                pass

    def _create_error_result(self, element_id: str, error: Exception) -> StatusResult:
        """Create error result for exception handling."""
        error_action = Action(
            type=ActionType.MANUAL_REVIEW,
            description="Process evaluation failed",
            priority=Priority.CRITICAL,
            metadata={"error": str(error)}
        )
        return StatusResult.create(
            state=EvaluationState.SCOPING,
            element_id=element_id,
            actions=[error_action],
            errors=[f"Evaluation error: {str(error)}"],
        )

    def _get_element_id(self, element: Element) -> str:
        """Extract element ID for identification."""
        try:
            # Try to get 'id' property first
            element_id = element.get_property("id")
            if element_id is not None:
                return str(element_id)

            # Try to get '_id' property (MongoDB style)
            element_id = element.get_property("_id")
            if element_id is not None:
                return str(element_id)

            # Fallback to object id
            return str(id(element))
        except Exception:
            return str(id(element))

    def _is_final_stage(self, stage_name: str, process: "Process") -> bool:
        """Check if a stage is the final stage in the process."""
        return self._get_next_stage(stage_name, process) is None

    def _get_next_stage(self, current_stage_name: str, process: "Process") -> Any | None:
        """Get the next stage in the process order."""
        try:
            current_index = process.stage_order.index(current_stage_name)
            if current_index < len(process.stage_order) - 1:
                next_stage_name = process.stage_order[current_index + 1]
                return process.get_stage(next_stage_name)
        except ValueError:
            pass
        return None

    def _validate_stage_progression(
        self,
        element: Element,
        from_stage: str,
        to_stage: str,
        process: "Process"
    ) -> tuple[bool, list[str]]:
        """Validate if an element can progress from one stage to another."""
        # Delegate to process validation logic
        return process.validate_stage_progression(element, from_stage, to_stage)

    def configure_strategies(
        self,
        stage_strategy: StageEvaluationStrategy | None = None,
        gate_strategy: GateEvaluationStrategy | None = None
    ) -> None:
        """
        Configure evaluation strategies.

        Args:
            stage_strategy: New stage evaluation strategy
            gate_strategy: New gate evaluation strategy
        """
        if stage_strategy is not None:
            self.stage_strategy = stage_strategy
        if gate_strategy is not None:
            self.gate_strategy = gate_strategy

    def get_evaluation_metrics(self) -> dict[str, Any]:
        """
        Get metrics about the evaluation pipeline.

        Returns:
            Dictionary with pipeline metrics and configuration
        """
        return {
            "state_machine_class": self.state_machine.__class__.__name__,
            "stage_strategy_class": self.stage_strategy.__class__.__name__,
            "gate_strategy_class": self.gate_strategy.__class__.__name__,
            "pipeline_version": "1.0.0"
        }
