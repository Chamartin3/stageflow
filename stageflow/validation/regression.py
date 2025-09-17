"""Regression detection logic for StageFlow."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from stageflow.core.element import Element
from stageflow.core.process import Process
from stageflow.core.result import StatusResult


class RegressionType(Enum):
    """Types of regression that can be detected."""

    STAGE_REGRESSION = "stage_regression"  # Element moved to earlier stage
    PROPERTY_LOSS = "property_loss"  # Required properties were lost
    GATE_FAILURE = "gate_failure"  # Previously passing gates now fail
    SCHEMA_VIOLATION = "schema_violation"  # Schema violations introduced


@dataclass(frozen=True)
class RegressionIssue:
    """Individual regression issue."""

    regression_type: RegressionType
    description: str
    current_value: Any
    expected_value: Any
    location: str
    severity: str = "warning"


@dataclass(frozen=True)
class RegressionResult:
    """Result of regression detection analysis."""

    element_id: str
    has_regression: bool
    issues: list[RegressionIssue]
    current_state: StatusResult
    previous_state: StatusResult | None
    metadata: dict[str, Any]

    @property
    def regression_count(self) -> int:
        """Get total number of regression issues."""
        return len(self.issues)

    @property
    def severe_regressions(self) -> list[RegressionIssue]:
        """Get only severe regression issues."""
        return [issue for issue in self.issues if issue.severity == "error"]


class RegressionDetector:
    """
    Regression detection system for StageFlow processes.

    Detects when elements have regressed in their process flow by comparing
    current state with historical snapshots or expected progression.
    """

    def __init__(self):
        """Initialize regression detector."""
        self._snapshots: dict[str, dict[str, Any]] = {}

    def detect_regression(
        self,
        element: Element,
        process: Process,
        element_id: str,
        previous_result: StatusResult | None = None,
    ) -> RegressionResult:
        """
        Detect regression by comparing current state with previous state.

        Args:
            element: Current element to evaluate
            process: Process to evaluate against
            element_id: Unique identifier for element
            previous_result: Previous evaluation result for comparison

        Returns:
            RegressionResult with detected issues
        """
        # Evaluate current state
        current_result = process.evaluate(element)

        # Get previous state from snapshot or parameter
        if previous_result is None:
            previous_result = self._get_snapshot(element_id)

        issues = []

        if previous_result:
            issues.extend(self._check_stage_regression(current_result, previous_result))
            issues.extend(self._check_property_regression(element, element_id))
            issues.extend(self._check_gate_regression(element, process, element_id))

        # Store current snapshot
        self._store_snapshot(element_id, element, current_result)

        return RegressionResult(
            element_id=element_id,
            has_regression=len(issues) > 0,
            issues=issues,
            current_state=current_result,
            previous_state=previous_result,
            metadata={"detection_timestamp": self._get_timestamp()},
        )

    def _check_stage_regression(
        self, current_result: StatusResult, previous_result: StatusResult
    ) -> list[RegressionIssue]:
        """Check for stage-level regression."""
        issues = []

        if not current_result.current_stage or not previous_result.current_stage:
            return issues

        # Simple check: if element moved to an earlier stage
        # Note: This assumes stage order represents progression
        # In a real implementation, you'd need stage ordering logic
        if current_result.current_stage != previous_result.current_stage:
            # For now, flag any stage change as potential regression
            # In practice, you'd compare stage positions in process order
            issues.append(
                RegressionIssue(
                    regression_type=RegressionType.STAGE_REGRESSION,
                    description=f"Element moved from stage '{previous_result.current_stage}' to '{current_result.current_stage}'",
                    current_value=current_result.current_stage,
                    expected_value=previous_result.current_stage,
                    location="stage",
                    severity="warning",
                )
            )

        return issues

    def _check_property_regression(self, element: Element, element_id: str) -> list[RegressionIssue]:
        """Check for property-level regression."""
        issues = []

        previous_snapshot = self._snapshots.get(element_id, {})
        previous_properties = previous_snapshot.get("properties", {})

        if not previous_properties:
            return issues

        current_data = element.to_dict()

        # Check for lost properties
        for prop_path, prev_value in previous_properties.items():
            if not element.has_property(prop_path):
                issues.append(
                    RegressionIssue(
                        regression_type=RegressionType.PROPERTY_LOSS,
                        description=f"Property '{prop_path}' was removed",
                        current_value=None,
                        expected_value=prev_value,
                        location=f"property.{prop_path}",
                        severity="error",
                    )
                )
            else:
                current_value = element.get_property(prop_path)
                # Check for significant value changes
                if self._is_significant_change(prev_value, current_value):
                    issues.append(
                        RegressionIssue(
                            regression_type=RegressionType.PROPERTY_LOSS,
                            description=f"Property '{prop_path}' value changed significantly",
                            current_value=current_value,
                            expected_value=prev_value,
                            location=f"property.{prop_path}",
                            severity="warning",
                        )
                    )

        return issues

    def _check_gate_regression(self, element: Element, process: Process, element_id: str) -> list[RegressionIssue]:
        """Check for gate-level regression."""
        issues = []

        previous_snapshot = self._snapshots.get(element_id, {})
        previous_gates = previous_snapshot.get("passed_gates", set())

        if not previous_gates:
            return issues

        # Re-evaluate all stages to see which gates pass now
        current_passed_gates = set()
        for stage in process.stages:
            stage_result = stage.evaluate(element)
            current_passed_gates.update(stage_result.passed_gates)

        # Check for gates that previously passed but now fail
        failed_gates = previous_gates - current_passed_gates
        for gate_name in failed_gates:
            issues.append(
                RegressionIssue(
                    regression_type=RegressionType.GATE_FAILURE,
                    description=f"Gate '{gate_name}' was passing but now fails",
                    current_value=False,
                    expected_value=True,
                    location=f"gate.{gate_name}",
                    severity="error",
                )
            )

        return issues

    def _store_snapshot(self, element_id: str, element: Element, result: StatusResult):
        """Store snapshot of element state for future regression detection."""
        # Collect passed gates from all stages
        passed_gates = set()
        # Note: This is simplified - in practice you'd re-evaluate or store more detail

        self._snapshots[element_id] = {
            "properties": element.to_dict(),
            "stage": result.current_stage,
            "state": result.state.value,
            "passed_gates": passed_gates,
            "timestamp": self._get_timestamp(),
        }

    def _get_snapshot(self, element_id: str) -> StatusResult | None:
        """Retrieve previous snapshot for element."""
        snapshot = self._snapshots.get(element_id)
        if not snapshot:
            return None

        # Reconstruct StatusResult from snapshot
        # This is simplified - in practice you'd store/restore the full result
        from stageflow.core.result import EvaluationState

        try:
            state = EvaluationState(snapshot["state"])
            return StatusResult(
                state=state,
                current_stage=snapshot["stage"],
                proposed_stage=snapshot["stage"],
                actions=[],
                metadata={"from_snapshot": True},
                errors=[],
            )
        except (KeyError, ValueError):
            return None

    def _is_significant_change(self, old_value: Any, new_value: Any) -> bool:
        """Determine if a value change is significant enough to flag."""
        # Simple heuristics for detecting significant changes
        if type(old_value) != type(new_value):
            return True

        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            # Flag numeric changes > 10%
            if old_value != 0:
                change_percent = abs(new_value - old_value) / abs(old_value)
                return change_percent > 0.1
            else:
                return new_value != 0

        if isinstance(old_value, str) and isinstance(new_value, str):
            # Flag string changes in length > 20%
            if len(old_value) > 0:
                length_change = abs(len(new_value) - len(old_value)) / len(old_value)
                return length_change > 0.2
            else:
                return len(new_value) > 0

        # For other types, flag any change
        return old_value != new_value

    def _get_timestamp(self) -> str:
        """Get current timestamp for snapshots."""
        import datetime

        return datetime.datetime.now().isoformat()

    def clear_snapshots(self, element_id: str | None = None):
        """Clear stored snapshots."""
        if element_id:
            self._snapshots.pop(element_id, None)
        else:
            self._snapshots.clear()

    def get_snapshot_count(self) -> int:
        """Get number of stored snapshots."""
        return len(self._snapshots)
