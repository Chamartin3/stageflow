"""
Evaluation strategy classes for StageFlow process evaluation.

This module provides strategy implementations for stage and gate evaluation
that separate concerns and improve testability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from stageflow.element import Element

if TYPE_CHECKING:
    from stageflow.stage import Stage
    from stageflow.gates import Gate


@dataclass
class StageResult:
    """Result of stage evaluation."""
    compatible: bool
    completion_percentage: float = 0.0
    missing_properties: list[str] | None = None
    validation_errors: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize defaults after creation."""
        if self.missing_properties is None:
            self.missing_properties = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GateResult:
    """Result of gate evaluation."""
    passed: bool
    gate: "Gate | None" = None
    failure_reasons: list[str] | None = None
    actions: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize defaults after creation."""
        if self.failure_reasons is None:
            self.failure_reasons = []
        if self.actions is None:
            self.actions = []
        if self.metadata is None:
            self.metadata = {}


class StageEvaluationStrategy(ABC):
    """
    Abstract strategy for evaluating elements against stages.

    This strategy pattern allows for different approaches to stage evaluation
    while maintaining a consistent interface.
    """

    @abstractmethod
    def evaluate_stage_compatibility(self, element: Element, stage: "Stage") -> StageResult:
        """
        Evaluate if an element is compatible with a stage.

        Args:
            element: Element to evaluate
            stage: Stage to evaluate against

        Returns:
            StageResult with compatibility information
        """
        pass

    @abstractmethod
    def find_best_matching_stage(self, element: Element, stages: list["Stage"]) -> "Stage | None":
        """
        Find the best matching stage for an element.

        Args:
            element: Element to evaluate
            stages: List of available stages

        Returns:
            Best matching stage or None if no match found
        """
        pass


class DefaultStageEvaluationStrategy(StageEvaluationStrategy):
    """
    Default implementation of stage evaluation strategy.

    Uses the existing stage evaluation logic from the original implementation.
    """

    def __init__(self, stage_order: list[str] | None = None):
        """
        Initialize strategy.

        Args:
            stage_order: Ordered list of stage names for prioritization
        """
        self.stage_order = stage_order or []

    def evaluate_stage_compatibility(self, element: Element, stage: "Stage") -> StageResult:
        """Evaluate stage compatibility using existing stage logic."""
        try:
            # Use existing stage compatibility check
            is_compatible = stage.is_compatible_with_element(element)
            completion = stage.get_completion_percentage(element) if is_compatible else 0.0

            return StageResult(
                compatible=is_compatible,
                completion_percentage=completion,
                metadata={"stage_name": stage.name}
            )
        except Exception as e:
            return StageResult(
                compatible=False,
                validation_errors=[f"Stage evaluation error: {e}"],
                metadata={"stage_name": stage.name, "error": str(e)}
            )

    def find_best_matching_stage(self, element: Element, stages: list["Stage"]) -> "Stage | None":
        """Find best matching stage using completion percentage and stage order."""
        compatible_stages = []

        # Find all compatible stages
        for stage in stages:
            result = self.evaluate_stage_compatibility(element, stage)
            if result.compatible:
                compatible_stages.append((stage, result))

        if not compatible_stages:
            return None

        # If multiple stages match, use the one with highest completion, then highest in order
        def stage_priority(stage_result_tuple):
            stage, result = stage_result_tuple
            completion = result.completion_percentage
            try:
                order_index = self.stage_order.index(stage.name)
            except ValueError:
                order_index = len(self.stage_order)  # Put unknown stages at end
            return (completion, -order_index)  # Negative for reverse order (higher index = higher priority)

        best_stage, _ = max(compatible_stages, key=stage_priority)
        return best_stage


class GateEvaluationStrategy(ABC):
    """
    Abstract strategy for gate evaluation and selection.

    This strategy pattern allows for different approaches to gate evaluation
    while maintaining a consistent interface.
    """

    @abstractmethod
    def find_passing_gate(self, element: Element, gates: list["Gate"]) -> GateResult:
        """
        Find the first passing gate for an element.

        Args:
            element: Element to evaluate
            gates: List of gates to evaluate

        Returns:
            GateResult with evaluation outcome
        """
        pass

    @abstractmethod
    def evaluate_all_gates(self, element: Element, gates: list["Gate"]) -> list[GateResult]:
        """
        Evaluate all gates for diagnostic purposes.

        Args:
            element: Element to evaluate
            gates: List of gates to evaluate

        Returns:
            List of GateResult for each gate
        """
        pass


class DefaultGateEvaluationStrategy(GateEvaluationStrategy):
    """
    Default implementation of gate evaluation strategy.

    Uses the existing gate evaluation logic from the original implementation.
    """

    def find_passing_gate(self, element: Element, gates: list["Gate"]) -> GateResult:
        """Find first passing gate using existing gate logic."""
        for gate in gates:
            try:
                # Use existing gate evaluation
                if gate.evaluate(element):
                    return GateResult(
                        passed=True,
                        gate=gate,
                        metadata={"gate_name": gate.name}
                    )
            except Exception:
                # Continue to next gate on error
                continue

        # No gates passed
        return GateResult(
            passed=False,
            failure_reasons=["No gates passed evaluation"],
            metadata={"evaluated_gates": len(gates)}
        )

    def evaluate_all_gates(self, element: Element, gates: list["Gate"]) -> list[GateResult]:
        """Evaluate all gates for comprehensive analysis."""
        results = []

        for gate in gates:
            try:
                passed = gate.evaluate(element)
                result = GateResult(
                    passed=passed,
                    gate=gate,
                    metadata={"gate_name": gate.name}
                )
                if not passed:
                    # Try to get failure reasons if available
                    try:
                        failure_info = gate.get_failure_info(element)
                        result.failure_reasons = [failure_info] if isinstance(failure_info, str) else failure_info
                    except (AttributeError, Exception):
                        result.failure_reasons = ["Gate evaluation failed"]

                results.append(result)
            except Exception as e:
                results.append(GateResult(
                    passed=False,
                    gate=gate,
                    failure_reasons=[f"Gate evaluation error: {e}"],
                    metadata={"gate_name": gate.name, "error": str(e)}
                ))

        return results


class AdvancedStageEvaluationStrategy(StageEvaluationStrategy):
    """
    Advanced stage evaluation strategy with additional features.

    This strategy can be used for more sophisticated stage matching
    with custom scoring algorithms and constraints.
    """

    def __init__(
        self,
        stage_order: list[str] | None = None,
        completion_weight: float = 0.7,
        order_weight: float = 0.3,
        min_completion_threshold: float = 0.0
    ):
        """
        Initialize advanced strategy.

        Args:
            stage_order: Ordered list of stage names
            completion_weight: Weight for completion percentage in scoring
            order_weight: Weight for stage order in scoring
            min_completion_threshold: Minimum completion percentage to consider
        """
        self.stage_order = stage_order or []
        self.completion_weight = completion_weight
        self.order_weight = order_weight
        self.min_completion_threshold = min_completion_threshold

    def evaluate_stage_compatibility(self, element: Element, stage: "Stage") -> StageResult:
        """Enhanced stage compatibility evaluation."""
        try:
            is_compatible = stage.is_compatible_with_element(element)
            completion = stage.get_completion_percentage(element) if is_compatible else 0.0

            # Additional validation logic can be added here
            meets_threshold = completion >= self.min_completion_threshold

            return StageResult(
                compatible=is_compatible and meets_threshold,
                completion_percentage=completion,
                metadata={
                    "stage_name": stage.name,
                    "meets_threshold": meets_threshold,
                    "threshold": self.min_completion_threshold
                }
            )
        except Exception as e:
            return StageResult(
                compatible=False,
                validation_errors=[f"Enhanced stage evaluation error: {e}"],
                metadata={"stage_name": stage.name, "error": str(e)}
            )

    def find_best_matching_stage(self, element: Element, stages: list["Stage"]) -> "Stage | None":
        """Find best matching stage using weighted scoring."""
        compatible_stages = []

        for stage in stages:
            result = self.evaluate_stage_compatibility(element, stage)
            if result.compatible:
                compatible_stages.append((stage, result))

        if not compatible_stages:
            return None

        # Calculate weighted scores
        def calculate_score(stage_result_tuple):
            stage, result = stage_result_tuple
            completion_score = result.completion_percentage * self.completion_weight

            # Order score (higher index = higher score)
            try:
                order_position = self.stage_order.index(stage.name)
                order_score = (len(self.stage_order) - order_position) / len(self.stage_order)
            except (ValueError, ZeroDivisionError):
                order_score = 0.0

            order_score *= self.order_weight

            return completion_score + order_score

        best_stage, _ = max(compatible_stages, key=calculate_score)
        return best_stage
