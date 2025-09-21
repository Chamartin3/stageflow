"""Element state history tracking for StageFlow processes."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StateTransition:
    """
    Record of a single state transition during element evaluation.

    Tracks the progression of an element through the 7-state evaluation flow,
    including timing, conditions, and metadata for each transition.
    """

    timestamp: float
    from_state: str | None
    to_state: str
    element_id: str | None
    stage_name: str | None
    transition_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_since_previous(self) -> float | None:
        """Calculate duration since previous transition (requires external tracking)."""
        return self.metadata.get("duration_since_previous")

    def is_progression(self) -> bool:
        """Check if this represents forward progression through states."""
        progression_map = {
            "scoping": 0,
            "fulfilling": 1,
            "qualifying": 2,
            "awaiting": 1.5,  # Considered lateral movement
            "advancing": 3,
            "regressing": -1,  # Backward movement
            "completed": 4,
        }

        if self.from_state is None:
            return True  # Initial state assignment

        from_level = progression_map.get(self.from_state, 0)
        to_level = progression_map.get(self.to_state, 0)

        return to_level > from_level

    def is_regression(self) -> bool:
        """Check if this represents backward movement through states."""
        return self.to_state == "regressing" or (
            bool(self.from_state) and not self.is_progression() and self.to_state != "awaiting"
        )


@dataclass
class ElementStateHistory:
    """
    Complete state history tracking for a single element.

    Maintains chronological record of all state transitions, performance
    metrics, and evaluation metadata for comprehensive audit trails.
    """

    element_id: str
    initial_timestamp: float
    transitions: list[StateTransition] = field(default_factory=list)
    evaluation_count: int = 0
    total_evaluation_time: float = 0.0
    current_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_transition(
        self,
        from_state: str | None,
        to_state: str,
        stage_name: str | None,
        reason: str,
        evaluation_time: float,
        additional_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a new state transition to the history."""
        timestamp = time.time()

        # Calculate duration since previous transition
        duration_since_previous = None
        if self.transitions:
            duration_since_previous = timestamp - self.transitions[-1].timestamp

        metadata = {
            "evaluation_time": evaluation_time,
            "duration_since_previous": duration_since_previous,
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        transition = StateTransition(
            timestamp=timestamp,
            from_state=from_state,
            to_state=to_state,
            element_id=self.element_id,
            stage_name=stage_name,
            transition_reason=reason,
            metadata=metadata,
        )

        self.transitions.append(transition)
        self.evaluation_count += 1
        self.total_evaluation_time += evaluation_time
        self.current_stage = stage_name

    @property
    def current_state(self) -> str | None:
        """Get the current state of the element."""
        return self.transitions[-1].to_state if self.transitions else None

    @property
    def progression_count(self) -> int:
        """Count of forward progression transitions."""
        return sum(1 for t in self.transitions if t.is_progression())

    @property
    def regression_count(self) -> int:
        """Count of regression transitions."""
        return sum(1 for t in self.transitions if t.is_regression())

    @property
    def total_time_in_process(self) -> float:
        """Total time element has been in the process."""
        if not self.transitions:
            return 0.0
        return self.transitions[-1].timestamp - self.initial_timestamp

    @property
    def average_evaluation_time(self) -> float:
        """Average time per evaluation."""
        return self.total_evaluation_time / self.evaluation_count if self.evaluation_count > 0 else 0.0

    def get_time_in_state(self, state: str) -> float:
        """Calculate total time spent in a specific state."""
        total_time = 0.0
        current_state_start = None

        for _i, transition in enumerate(self.transitions):
            if transition.to_state == state:
                current_state_start = transition.timestamp
            elif current_state_start is not None:
                # State changed, add duration
                total_time += transition.timestamp - current_state_start
                current_state_start = None

        # Handle case where element is still in the state
        if current_state_start is not None and self.current_state == state:
            total_time += time.time() - current_state_start

        return total_time

    def get_state_summary(self) -> dict[str, Any]:
        """Get summary of state history and performance."""
        state_counts = {}
        for transition in self.transitions:
            state_counts[transition.to_state] = state_counts.get(transition.to_state, 0) + 1

        return {
            "element_id": self.element_id,
            "current_state": self.current_state,
            "current_stage": self.current_stage,
            "total_evaluations": self.evaluation_count,
            "total_time": self.total_time_in_process,
            "average_eval_time": self.average_evaluation_time,
            "progressions": self.progression_count,
            "regressions": self.regression_count,
            "state_counts": state_counts,
            "last_transition": self.transitions[-1].timestamp if self.transitions else None,
        }
