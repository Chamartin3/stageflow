"""Core Process class for StageFlow multi-stage validation orchestration."""

import time

# Lazy import to avoid circular dependency
from typing import TYPE_CHECKING, Any

from stageflow.core.element import Element

if TYPE_CHECKING:
    from stageflow.core.stage import Stage
from stageflow.process.config import ProcessConfig
from stageflow.process.extras.history import ElementStateHistory
from stageflow.process.result import Action, ActionType, EvaluationState, Priority, StatusResult


class Process:
    """
    Multi-stage workflow orchestration for element validation.

    Processes define the complete validation pipeline, managing stage
    transitions and implementing the 7-state evaluation flow.
    """

    def __init__(
        self,
        name: str,
        stages: list[Any] | None = None,
        config: ProcessConfig | None = None,
        allow_stage_skipping: bool = False,
        stage_order: list[str] | None = None,
    ):
        """
        Initialize Process from configuration.

        Args:
            name: Process name
            stages: Optional list of stages to initialize with
            config: Process configuration (optional, will be created if not provided)
            allow_stage_skipping: Whether stage skipping is allowed
            stage_order: Explicit stage order (optional, will be auto-generated)
        """
        if config is None:
            config = ProcessConfig(
                name=name,
                allow_stage_skipping=allow_stage_skipping
            )

        self._config = config
        self._stages = stages or []
        self._stage_order: list[str] = stage_order or []

        # Initialize components based on config
        self._state_histories: dict[str, ElementStateHistory] = {}

        # Performance caches
        self._stage_cache: dict[str, Stage] = {}
        self._property_cache: dict[str, set[str]] = {}
        self._transition_cache: dict[tuple[str, str], bool] = {}

        # Build stage mappings and validate
        self._rebuild_stage_mappings()
        self._validate_process()

    # Configuration properties
    @property
    def name(self) -> str:
        """Process name."""
        return self._config.name

    @property
    def initial_stage(self) -> str | None:
        """Initial stage name."""
        return self._config.initial_stage

    @property
    def final_stage(self) -> str | None:
        """Final stage name."""
        return self._config.final_stage

    @property
    def allow_stage_skipping(self) -> bool:
        """Whether stage skipping is allowed."""
        return self._config.allow_stage_skipping



    @property
    def metadata(self) -> dict[str, Any]:
        """Process metadata."""
        return self._config.metadata

    @property
    def stages(self) -> list[Any]:
        """List of process stages."""
        return self._stages

    @property
    def stage_order(self) -> list[str]:
        """Ordered list of stage names."""
        return self._stage_order

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
                    element_id = self._get_element_id(element)
                    # Create action for invalid stage
                    invalid_stage_action = Action(
                        type=ActionType.MANUAL_REVIEW,
                        description=f"Invalid current stage: {current_stage_name}",
                        priority=Priority.HIGH
                    )
                    result = StatusResult.create(
                        state=EvaluationState.SCOPING,
                        element_id=element_id,
                        actions=[invalid_stage_action],
                        errors=[f"Stage '{current_stage_name}' not found in process"],
                    )
                    return result
            else:
                current_stage, scope_result = self._scope_element(element)
                if scope_result:
                    return scope_result

            # Phase 2: Evaluation - assess current stage
            if current_stage:
                stage_result = current_stage.evaluate(element)
                element_id = self._get_element_id(element)

                if stage_result.overall_passed:
                    # Check if we can advance to next stage
                    next_stage = self._get_next_stage(current_stage.name)
                    if next_stage:
                        # Check if element is ready for next stage
                        can_advance, advance_errors = self.validate_stage_progression(
                            element, current_stage.name, next_stage.name
                        )
                        if can_advance:
                            # Recursively evaluate next stage
                            return self.evaluate(element, next_stage.name)
                        else:
                            # Use stage-based actions for awaiting state if available
                            stage_actions = current_stage.resolve_actions_for_state("awaiting", element, {"next_stage": next_stage.name})
                            if not stage_actions:
                                # Fallback to error-based actions
                                stage_actions = [Action(
                                    type=ActionType.WAIT_FOR_CONDITION,
                                    description=error,
                                    priority=Priority.NORMAL
                                ) for error in advance_errors]

                            result = StatusResult.create(
                                state=EvaluationState.AWAITING,
                                element_id=element_id,
                                current_stage=current_stage.name,
                                actions=stage_actions,
                                metadata={"next_stage": next_stage.name},
                            )
                    else:
                        # Final stage reached - use stage-based completion actions
                        stage_actions = current_stage.resolve_actions_for_state("completed", element, {"final_stage": current_stage.name})
                        if not stage_actions:
                            # Fallback to default completion action
                            stage_actions = [Action(
                                type=ActionType.TRANSITION_STAGE,
                                description="Process completed successfully",
                                priority=Priority.NORMAL
                            )]

                        result = StatusResult.create(
                            state=EvaluationState.COMPLETED,
                            element_id=element_id,
                            current_stage=current_stage.name,
                            actions=stage_actions,
                            metadata={"final_stage": current_stage.name},
                        )
                else:
                    # Use stage-based actions for fulfilling state
                    stage_actions = current_stage.resolve_actions_for_state("fulfilling", element, {"completion": current_stage.get_completion_percentage(element)})
                    if not stage_actions:
                        # Fallback to gate-based actions
                        stage_actions = [Action(
                            type=ActionType.COMPLETE_FIELD,
                            description=action,
                            priority=Priority.NORMAL
                        ) for action in stage_result.actions if isinstance(action, str)]
                        # Keep existing Action objects
                        stage_actions.extend([action for action in stage_result.actions if not isinstance(action, str)])

                    result = StatusResult.create(
                        state=EvaluationState.FULFILLING,
                        element_id=element_id,
                        current_stage=current_stage.name,
                        actions=stage_actions,
                        metadata={"completion": current_stage.get_completion_percentage(element)},
                    )
            else:
                # Element doesn't match any stage - scoping issue
                element_id = self._get_element_id(element)
                scoping_action = Action(
                    type=ActionType.VALIDATE_DATA,
                    description="Element does not match any stage in process",
                    priority=Priority.HIGH
                )
                result = StatusResult.create(
                    state=EvaluationState.SCOPING,
                    element_id=element_id,
                    actions=[scoping_action],
                    errors=["Unable to determine appropriate stage for element"],
                )

            return result

        except Exception as e:
            element_id = self._get_element_id(element)
            error_action = Action(
                type=ActionType.MANUAL_REVIEW,
                description="Process evaluation failed",
                priority=Priority.CRITICAL,
                metadata={"error": str(e)}
            )
            result = StatusResult.create(
                state=EvaluationState.SCOPING,
                element_id=element_id,
                actions=[error_action],
                errors=[f"Evaluation error: {str(e)}"],
            )
            return result

    def get_stage(self, stage_name: str) -> Any | None:
        """Get stage by name with caching."""
        if stage_name in self._stage_cache:
            return self._stage_cache[stage_name]

        for stage in self._stages:
            if stage.name == stage_name:
                self._stage_cache[stage_name] = stage
                return stage
        return None

    def add_stage(self, stage: Any) -> None:
        """Add stage to process."""
        # Check for duplicate stage names
        for existing_stage in self._stages:
            if existing_stage.name == stage.name:
                raise ValueError(f"Stage '{stage.name}' already exists in process")

        self._stages.append(stage)
        # Add to stage order as well
        if stage.name not in self._stage_order:
            self._stage_order.append(stage.name)
        self._rebuild_stage_mappings()

    def get_element_state_history(self, element: Element) -> ElementStateHistory | None:
        """Get state history for element."""
        element_id = self._get_element_id(element)
        return self._state_histories.get(element_id)

    def _scope_element(self, element: Element) -> tuple[Any | None, StatusResult | None]:
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
        for stage in self._stages:
            if stage.is_compatible_with_element(element):
                compatible_stages.append(stage)

        if not compatible_stages:
            element_id = self._get_element_id(element)
            scoping_action = Action(
                type=ActionType.COMPLETE_FIELD,
                description="Ensure element has required properties for at least one stage",
                priority=Priority.HIGH
            )
            return None, StatusResult.create(
                state=EvaluationState.SCOPING,
                element_id=element_id,
                actions=[scoping_action],
                errors=["Element lacks required properties for any stage"],
            )

        # If multiple stages match, use the one with highest completion
        if len(compatible_stages) > 1:
            best_stage = max(compatible_stages, key=lambda s: s.get_completion_percentage(element))
            return best_stage, None

        return compatible_stages[0], None


    def _get_next_stage(self, current_stage_name: str) -> Any | None:
        """Get the next stage in the process order."""
        try:
            current_index = self._stage_order.index(current_stage_name)
            if current_index < len(self._stage_order) - 1:
                next_stage_name = self._stage_order[current_index + 1]
                return self.get_stage(next_stage_name)
        except ValueError:
            pass
        return None

    def _can_transition_to_stage(self, from_stage: str, to_stage: str) -> bool:
        """Check if transition between stages is allowed."""
        cache_key = (from_stage, to_stage)
        if cache_key in self._transition_cache:
            return self._transition_cache[cache_key]

        # Basic transition logic - can be extended
        if not self.allow_stage_skipping:
            # Must follow sequential order
            try:
                from_index = self._stage_order.index(from_stage)
                to_index = self._stage_order.index(to_stage)
                allowed = to_index == from_index + 1
            except ValueError:
                allowed = False
        else:
            allowed = True

        self._transition_cache[cache_key] = allowed
        return allowed


    def _record_state_transition(
        self,
        element: Element,
        from_state: str | None,
        to_state: str,
        stage_name: str | None,
        reason: str,
        evaluation_time: float,
        additional_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record state transition in element history."""
        element_id = self._get_element_id(element)

        # Get or create history
        if element_id not in self._state_histories:
            self._state_histories[element_id] = ElementStateHistory(
                element_id=element_id,
                initial_timestamp=time.time(),
            )

        history = self._state_histories[element_id]
        history.add_transition(
            from_state=from_state,
            to_state=to_state,
            stage_name=stage_name,
            reason=reason,
            evaluation_time=evaluation_time,
            additional_metadata=additional_metadata,
        )

    def _rebuild_stage_mappings(self) -> None:
        """Rebuild internal stage mappings and clear caches."""
        self._stage_cache.clear()
        self._property_cache.clear()
        self._transition_cache.clear()

        # Build stage order if not explicitly set
        if not self._stage_order:
            self._stage_order = [stage.name for stage in self._stages]

    def _validate_process(self) -> None:
        """Validate process configuration and structure."""
        # Validate process name
        if not self.name or not self.name.strip():
            raise ValueError("Process must have a name")

        # Validate stages exist
        if not self._stages:
            raise ValueError("Process must contain at least one stage")

        # Validate stage order matches stages
        if self._stage_order:
            stage_names = {stage.name for stage in self._stages}
            order_names = set(self._stage_order)
            if stage_names != order_names:
                raise ValueError(
                    f"Stage order mismatch. Expected: {sorted(stage_names)}, "
                    f"Got: {sorted(order_names)}"
                )

        # Check for duplicate stage names
        stage_names = [stage.name for stage in self._stages]
        if len(stage_names) != len(set(stage_names)):
            duplicates = {name for name in stage_names if stage_names.count(name) > 1}
            raise ValueError(f"Duplicate stage names found: {duplicates}")

    def _get_element_id(self, element: Element) -> str:
        """Extract element ID for history tracking."""
        try:
            # Try to get 'id' property, fallback to object id
            element_id = element.get_property("id")
            return str(element_id) if element_id is not None else str(id(element))
        except Exception:
            return str(id(element))

    @classmethod
    def from_config(cls, config: ProcessConfig, stages: list[Any] | None = None) -> "Process":
        """Create Process from ProcessConfig."""
        return cls(
            name=config.name,
            stages=stages,
            config=config,
            allow_stage_skipping=config.allow_stage_skipping
        )

    def evaluate_batch(self, elements: list[Element]) -> list[StatusResult]:
        """Evaluate multiple elements in batch."""
        return [self.evaluate(element) for element in elements]

    def get_stage_index(self, stage_name: str) -> int:
        """Get index of stage in ordering."""
        try:
            return self._stage_order.index(stage_name)
        except ValueError:
            return -1

    def can_transition(self, from_stage: str, to_stage: str) -> bool:
        """Check if transition between stages is allowed."""
        return self._can_transition_to_stage(from_stage, to_stage)

    def get_next_stage_name(self, current_stage: str) -> str | None:
        """Get name of next stage in order."""
        next_stage = self._get_next_stage(current_stage)
        return next_stage.name if next_stage else None

    def validate_stage_progression(self, element: Element, from_stage: str, to_stage: str) -> tuple[bool, list[str]]:
        """Validate if an element can progress from one stage to another.

        Returns:
            Tuple of (can_progress, reasons)
        """
        errors = []

        # Check if transition is allowed
        if not self._can_transition_to_stage(from_stage, to_stage):
            errors.append(f"Direct transition from '{from_stage}' to '{to_stage}' not allowed")

        # Check if element meets requirements for target stage
        target_stage = self.get_stage(to_stage)
        if target_stage and not target_stage.is_compatible_with_element(element):
            errors.append(f"Element does not meet requirements for stage '{to_stage}'")

        return len(errors) == 0, errors

    # Public API for history (optional components)


