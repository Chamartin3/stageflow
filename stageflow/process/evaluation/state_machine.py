"""
ProcessStateMachine for 7-state evaluation flow.

This module implements the core state machine logic that was previously
embedded in the Process.evaluate() method, providing cleaner separation
of concerns and better testability.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from stageflow.element import Element
from stageflow.process.result import (
    Action,
    ActionType,
    EvaluationState,
    Priority,
)

if TYPE_CHECKING:
    from stageflow.stage import Stage


@dataclass
class EvaluationContext:
    """
    Context information for evaluation operations.

    Contains all the contextual information needed for state machine
    decisions and action generation.
    """
    element: Element
    element_id: str
    current_stage: "Stage | None" = None
    next_stage: "Stage | None" = None
    stage_result: Any = None  # Result from stage evaluation
    is_final_stage: bool = False
    can_advance: bool = False
    advance_errors: list[str] | None = None
    completion_percentage: float = 0.0
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize defaults after creation."""
        if self.metadata is None:
            self.metadata = {}


class ProcessStateMachine:
    """
    Handles 7-state evaluation flow logic for StageFlow processes.

    This class extracts the state machine logic from Process.evaluate()
    to provide a focused, testable component for determining evaluation
    states and transitions.
    """

    def determine_state(self, context: EvaluationContext) -> EvaluationState:
        """
        Determine the evaluation state based on context.

        Args:
            context: Evaluation context with all necessary information

        Returns:
            Appropriate EvaluationState for the context
        """
        if context.current_stage is None:
            return EvaluationState.SCOPING

        if context.stage_result is None:
            # No stage evaluation result - should not happen in normal flow
            return EvaluationState.SCOPING

        # Stage evaluation completed successfully
        if context.stage_result.overall_passed:
            if context.is_final_stage:
                return EvaluationState.COMPLETED
            elif context.can_advance:
                return EvaluationState.ADVANCING
            else:
                return EvaluationState.QUALIFYING
        else:
            # Stage requirements not met
            return EvaluationState.FULFILLING

    def get_next_actions(self, state: EvaluationState, context: EvaluationContext) -> list[Action]:
        """
        Get actions for a given state and context.

        Args:
            state: Current evaluation state
            context: Evaluation context

        Returns:
            List of actions appropriate for the state
        """
        if state == EvaluationState.SCOPING:
            return self._get_scoping_actions(context)
        elif state == EvaluationState.FULFILLING:
            return self._get_fulfilling_actions(context)
        elif state == EvaluationState.QUALIFYING:
            return self._get_qualifying_actions(context)
        elif state == EvaluationState.ADVANCING:
            return self._get_advancing_actions(context)
        elif state == EvaluationState.COMPLETED:
            return self._get_completion_actions(context)
        else:
            return []

    def should_transition(self, current_stage: "Stage", proposed_stage: "Stage") -> bool:
        """
        Check if transition between stages is allowed.

        Args:
            current_stage: Current stage
            proposed_stage: Proposed next stage

        Returns:
            True if transition is allowed
        """
        # Basic transition logic - can be extended
        # For now, allow any transition (policy can be enforced elsewhere)
        return True

    def validate_state_transition(self, from_state: EvaluationState, to_state: EvaluationState) -> bool:
        """
        Validate if a state transition is allowed.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid
        """
        valid_transitions = {
            EvaluationState.SCOPING: [EvaluationState.FULFILLING, EvaluationState.SCOPING],
            EvaluationState.FULFILLING: [
                EvaluationState.QUALIFYING,
                EvaluationState.AWAITING,
                EvaluationState.REGRESSING,
                EvaluationState.FULFILLING
            ],
            EvaluationState.QUALIFYING: [
                EvaluationState.ADVANCING,
                EvaluationState.AWAITING,
                EvaluationState.REGRESSING
            ],
            EvaluationState.AWAITING: [
                EvaluationState.ADVANCING,
                EvaluationState.REGRESSING,
                EvaluationState.FULFILLING
            ],
            EvaluationState.ADVANCING: [EvaluationState.COMPLETED, EvaluationState.FULFILLING],
            EvaluationState.REGRESSING: [EvaluationState.FULFILLING, EvaluationState.SCOPING],
            EvaluationState.COMPLETED: [],
        }

        return to_state in valid_transitions.get(from_state, [])

    def _get_scoping_actions(self, context: EvaluationContext) -> list[Action]:
        """Get actions for SCOPING state."""
        if context.current_stage is None:
            return [Action(
                type=ActionType.VALIDATE_DATA,
                description="Element does not match any stage in process",
                priority=Priority.HIGH
            )]
        return []

    def _get_fulfilling_actions(self, context: EvaluationContext) -> list[Action]:
        """Get actions for FULFILLING state."""
        # Try to get stage-based actions first
        if context.current_stage:
            stage_actions = context.current_stage.resolve_actions_for_state(
                "fulfilling",
                context.element,
                {"completion": context.completion_percentage}
            )
            if stage_actions:
                return stage_actions

        # Fallback to gate-based actions if available
        if context.stage_result and hasattr(context.stage_result, 'actions'):
            actions = []
            for action in context.stage_result.actions:
                if isinstance(action, str):
                    actions.append(Action(
                        type=ActionType.COMPLETE_FIELD,
                        description=action,
                        priority=Priority.NORMAL
                    ))
                else:
                    actions.append(action)
            return actions

        # Default fallback action
        return [Action(
            type=ActionType.COMPLETE_FIELD,
            description="Complete missing requirements",
            priority=Priority.NORMAL
        )]

    def _get_qualifying_actions(self, context: EvaluationContext) -> list[Action]:
        """Get actions for QUALIFYING state."""
        if context.current_stage and context.next_stage:
            stage_actions = context.current_stage.resolve_actions_for_state(
                "qualifying",
                context.element,
                {"next_stage": context.next_stage.name}
            )
            if stage_actions:
                return stage_actions

        # Default action for qualifying state
        next_stage_name = context.next_stage.name if context.next_stage else "next stage"
        return [Action(
            type=ActionType.WAIT_FOR_CONDITION,
            description=f"Ready to advance to {next_stage_name} once requirements are met",
            priority=Priority.NORMAL
        )]

    def _get_advancing_actions(self, context: EvaluationContext) -> list[Action]:
        """Get actions for ADVANCING state."""
        if context.current_stage and context.next_stage:
            stage_actions = context.current_stage.resolve_actions_for_state(
                "advancing",
                context.element,
                {"next_stage": context.next_stage.name}
            )
            if stage_actions:
                return stage_actions

        # Default action for advancing state
        next_stage_name = context.next_stage.name if context.next_stage else "next stage"
        return [Action(
            type=ActionType.TRANSITION_STAGE,
            description=f"Ready to advance to {next_stage_name}",
            priority=Priority.NORMAL
        )]

    def _get_completion_actions(self, context: EvaluationContext) -> list[Action]:
        """Get actions for COMPLETED state."""
        if context.current_stage:
            stage_actions = context.current_stage.resolve_actions_for_state(
                "completed",
                context.element,
                {"final_stage": context.current_stage.name}
            )
            if stage_actions:
                return stage_actions

        # Default completion action
        return [Action(
            type=ActionType.TRANSITION_STAGE,
            description="Process completed successfully",
            priority=Priority.NORMAL
        )]

    def get_state_metadata(self, state: EvaluationState, context: EvaluationContext) -> dict[str, Any]:
        """
        Get metadata appropriate for the given state.

        Args:
            state: Evaluation state
            context: Evaluation context

        Returns:
            Metadata dictionary for the state
        """
        metadata = dict(context.metadata or {})

        if state == EvaluationState.FULFILLING:
            metadata["completion"] = context.completion_percentage
        elif state == EvaluationState.QUALIFYING:
            if context.next_stage:
                metadata["next_stage"] = context.next_stage.name
            if context.advance_errors:
                metadata["advance_blocked"] = context.advance_errors
        elif state == EvaluationState.ADVANCING:
            if context.next_stage:
                metadata["next_stage"] = context.next_stage.name
        elif state == EvaluationState.COMPLETED:
            if context.current_stage:
                metadata["final_stage"] = context.current_stage.name

        return metadata
