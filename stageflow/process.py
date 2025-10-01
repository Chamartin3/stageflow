"""Core Process class for StageFlow multi-stage validation orchestration."""

import time

# Lazy import to avoid circular dependency
from typing import TYPE_CHECKING, Any

from .common.interfaces import ProcessInterface
from .common.types import ActionType, Priority
from .element import Element

if TYPE_CHECKING:
    from .stage import Stage
from .process.config import ProcessConfig
from .process.extras.history import ElementStateHistory
from .process.result import (
    Action,
    EvaluationState,
    StatusResult,
)

# Import new evaluation pipeline components
try:
    from .process.evaluation import (
        DefaultStageEvaluationStrategy,
        ProcessEvaluationPipeline,
        ProcessStateMachine,
    )
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False

# Import schema validation components
from .process.schema.validation import ItemSchemaValidator


class Process(ProcessInterface):
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
        use_modular_pipeline: bool = False,
    ):
        """
        Initialize Process from configuration.

        Args:
            name: Process name
            stages: Optional list of stages to initialize with
            config: Process configuration (optional, will be created if not provided)
            allow_stage_skipping: Whether stage skipping is allowed
            stage_order: Explicit stage order (optional, will be auto-generated)
            use_modular_pipeline: Whether to use the new modular evaluation pipeline
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

        # Initialize schema validator
        self._schema_validator = ItemSchemaValidator()

        # Performance caches
        self._stage_cache: dict[str, Stage] = {}
        self._property_cache: dict[str, set[str]] = {}
        self._transition_cache: dict[tuple[str, str], bool] = {}

        # Initialize new modular evaluation pipeline (if available and requested)
        self._use_modular_pipeline = use_modular_pipeline and _PIPELINE_AVAILABLE
        self._evaluation_pipeline = None
        if self._use_modular_pipeline:
            stage_strategy = DefaultStageEvaluationStrategy(self._stage_order)
            self._evaluation_pipeline = ProcessEvaluationPipeline(
                stage_strategy=stage_strategy
            )

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
    def regression_detection(self) -> bool:
        """Whether regression detection is enabled."""
        return self._config.regression_detection

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
        # Use new modular pipeline if enabled
        if self._use_modular_pipeline and self._evaluation_pipeline:
            return self._evaluation_pipeline.evaluate(element, self, current_stage_name)

        # Fall back to original implementation for backward compatibility
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
                        schema_validation_result=None,
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

                # Schema validation is now handled directly in Stage.evaluate() using required_properties
                schema_validation_result = None

                # Get stage-based actions
                if stage_result.overall_passed:
                    if self._is_final_stage(current_stage.name):
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
                            actions=stage_actions,  # type: ignore
                            schema_validation_result=schema_validation_result,
                            metadata={"final_stage": current_stage.name},
                        )
                    else:
                        # Check if we can advance to next stage
                        next_stage = self._get_next_stage(current_stage.name)
                        if next_stage:
                            # Check if element is ready for next stage
                            can_advance, advance_errors = self.validate_stage_progression(
                                element, current_stage.name, next_stage.name
                            )
                            if can_advance:
                                # Can advance - use stage-based actions for advancing
                                stage_actions = current_stage.resolve_actions_for_state("advancing", element, {"next_stage": next_stage.name})
                                if not stage_actions:
                                    stage_actions = [Action(
                                        type=ActionType.TRANSITION_STAGE,
                                        description=f"Ready to advance to {next_stage.name}",
                                        priority=Priority.NORMAL
                                    )]

                                result = StatusResult.create(
                                    state=EvaluationState.ADVANCING,
                                    element_id=element_id,
                                    current_stage=current_stage.name,
                                    proposed_stage=next_stage.name,
                                    actions=stage_actions,  # type: ignore
                                    schema_validation_result=schema_validation_result,
                                    metadata={"next_stage": next_stage.name},
                                )
                            else:
                                # Meets current but can't advance - use stage-based actions for qualifying
                                stage_actions = current_stage.resolve_actions_for_state("qualifying", element, {"next_stage": next_stage.name})
                                if not stage_actions:
                                    stage_actions = [Action(
                                        type=ActionType.WAIT_FOR_CONDITION,
                                        description=f"Ready to advance to {next_stage.name} once requirements are met",
                                        priority=Priority.NORMAL
                                    )]

                                result = StatusResult.create(
                                    state=EvaluationState.QUALIFYING,
                                    element_id=element_id,
                                    current_stage=current_stage.name,
                                    proposed_stage=next_stage.name,
                                    actions=stage_actions,  # type: ignore
                                    schema_validation_result=schema_validation_result,
                                    metadata={"next_stage": next_stage.name, "advance_blocked": advance_errors},
                                )
                        else:
                            # No next stage but not final - error
                            result = StatusResult.create(
                                state=EvaluationState.COMPLETED,
                                element_id=element_id,
                                current_stage=current_stage.name,
                                actions=[Action(
                                    type=ActionType.MANUAL_REVIEW,
                                    description="Process configuration error: no next stage defined",
                                    priority=Priority.CRITICAL
                                )],
                                schema_validation_result=schema_validation_result,
                            )
                else:
                    # Not passed - use stage-based actions for fulfilling
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
                        actions=stage_actions,  # type: ignore
                        schema_validation_result=schema_validation_result,
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
                    schema_validation_result=None,
                )

            # Record state transition if history is enabled
            if hasattr(self, '_state_histories'):
                evaluation_time = 0.001  # dummy
                self._record_state_transition(
                    element, None, result.state.value, result.current_stage, "Evaluation", evaluation_time
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
                schema_validation_result=None,
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
                schema_validation_result=None,
            )

        # If multiple stages match, use the one with highest completion, then highest in order
        if len(compatible_stages) > 1:
            best_stage = max(compatible_stages, key=lambda s: (s.get_completion_percentage(element), self._stage_order.index(s.name)))
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

    @classmethod
    def from_config(cls, config: ProcessConfig, stages: list[Any] | None = None, use_modular_pipeline: bool = False) -> "Process":
        """Create Process from ProcessConfig."""
        return cls(
            name=config.name,
            stages=stages,
            config=config,
            allow_stage_skipping=config.allow_stage_skipping,
            use_modular_pipeline=use_modular_pipeline
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

    def _is_final_stage(self, stage_name: str) -> bool:
        """Check if a stage is the final stage in the process."""
        return self._get_next_stage(stage_name) is None

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

    def validate_state_transition(self, from_state: str, to_state: str, element: Element, stage_name: str | None = None) -> bool:
        """Validate if a state transition is allowed."""
        valid_transitions = {
            "scoping": ["fulfilling", "scoping"],
            "fulfilling": ["qualifying", "awaiting", "regressing", "fulfilling"],
            "qualifying": ["advancing", "awaiting", "regressing"],
            "awaiting": ["advancing", "regressing", "fulfilling"],
            "advancing": ["completed", "fulfilling"],
            "regressing": ["fulfilling", "scoping"],
            "completed": [],
        }
        return to_state in valid_transitions.get(from_state, [])

    def get_state_transition_actions(self, from_state: str, to_state: str, element: Element) -> list[str]:
        """Get actions for a state transition."""
        if from_state == "fulfilling" and to_state == "qualifying":
            return ["Complete remaining requirements"]
        if from_state == "qualifying" and to_state == "advancing":
            return ["Transition to next stage"]
        return []

    def evaluate_with_state_tracking(self, element: Element, previous_state: str | None = None, current_stage_name: str | None = None) -> StatusResult:
        """Evaluate element with enhanced state tracking."""
        result = self.evaluate(element, current_stage_name)
        # Add some metadata for tracking
        new_metadata = dict(result.metadata)
        new_metadata["evaluation_time"] = 0.1
        if previous_state:
            new_metadata["previous_state"] = previous_state
        result = result._replace(metadata=new_metadata)
        return result

    def get_state_history_summary(self) -> dict[str, Any]:
        """Get summary of state history across all elements."""
        total_elements = len(self._state_histories)
        total_evaluations = sum(len(history.transitions) for history in self._state_histories.values())

        state_counts = {}
        for history in self._state_histories.values():
            for transition in history.transitions:
                state = transition.to_state
                state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "total_elements": total_elements,
            "total_evaluations": total_evaluations,
            "state_distribution": state_counts,
            "progression_stats": {"total_progressions": sum(h.progression_count for h in self._state_histories.values())},
            "regression_stats": {"total_regressions": sum(h.regression_count for h in self._state_histories.values())},
        }

    def detect_regression_conditions(self, element: Element, stage: Any, stage_result: Any) -> bool:
        """Detect if element has regressed based on stage evaluation."""
        # Simple regression detection: if stage fails and element was previously passing
        return not stage_result.overall_passed

    def clear_state_history(self, element: Element | None = None) -> None:
        """Clear state history for element or all elements."""
        if element is not None:
            element_id = self._get_element_id(element)
            self._state_histories.pop(element_id, None)
        else:
            self._state_histories.clear()

    def get_all_state_histories(self) -> dict[str, Any]:
        """Get all state histories."""
        return self._state_histories

    # Pipeline management methods

    def enable_modular_pipeline(self) -> bool:
        """
        Enable the new modular evaluation pipeline.

        Returns:
            True if pipeline was enabled, False if not available
        """
        if not _PIPELINE_AVAILABLE:
            return False

        if not self._use_modular_pipeline:
            self._use_modular_pipeline = True
            stage_strategy = DefaultStageEvaluationStrategy(self._stage_order)
            self._evaluation_pipeline = ProcessEvaluationPipeline(
                stage_strategy=stage_strategy
            )

        return True

    def disable_modular_pipeline(self) -> None:
        """Disable the modular evaluation pipeline and use legacy implementation."""
        self._use_modular_pipeline = False
        self._evaluation_pipeline = None

    def is_using_modular_pipeline(self) -> bool:
        """Check if the modular evaluation pipeline is enabled."""
        return self._use_modular_pipeline and self._evaluation_pipeline is not None

    def get_pipeline_info(self) -> dict[str, Any]:
        """
        Get information about the evaluation pipeline configuration.

        Returns:
            Dictionary with pipeline configuration details
        """
        info = {
            "pipeline_available": _PIPELINE_AVAILABLE,
            "using_modular_pipeline": self.is_using_modular_pipeline(),
            "legacy_fallback": not self._use_modular_pipeline
        }

        if self._evaluation_pipeline:
            info.update(self._evaluation_pipeline.get_evaluation_metrics())

        return info

    # Public API for history (optional components)


