"""Status result and evaluation state definitions for StageFlow."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EvaluationState(Enum):
    """
    Seven-state evaluation flow for StageFlow processes.

    States represent the current status of an element within a process:
    - SCOPING: Determining which stage applies to the element
    - FULFILLING: Element is working toward stage completion
    - QUALIFYING: Element meets stage requirements, ready to advance
    - AWAITING: Element is waiting for external conditions
    - ADVANCING: Element is transitioning to the next stage
    - REGRESSING: Element is moving backward in the process
    - COMPLETED: Element has finished the entire process
    """

    SCOPING = "scoping"
    FULFILLING = "fulfilling"
    QUALIFYING = "qualifying"
    AWAITING = "awaiting"
    ADVANCING = "advancing"
    REGRESSING = "regressing"
    COMPLETED = "completed"


@dataclass(frozen=True)
class StatusResult:
    """
    Immutable result of element evaluation against a process.

    Contains the complete state of evaluation including current position,
    proposed next steps, and any actions needed.
    """

    state: EvaluationState
    current_stage: str | None
    proposed_stage: str | None
    actions: list[str]
    metadata: dict[str, Any]
    errors: list[str]

    def __post_init__(self):
        """Validate result consistency after initialization."""
        if self.state == EvaluationState.COMPLETED and self.current_stage is not None:
            # For completed state, current_stage should be None
            pass

        if self.state == EvaluationState.SCOPING and not self.current_stage:
            # Scoping may not have a current stage yet
            pass

    @classmethod
    def scoping(
        cls,
        actions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create a SCOPING result."""
        return cls(
            state=EvaluationState.SCOPING,
            current_stage=None,
            proposed_stage=None,
            actions=actions or [],
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def fulfilling(
        cls,
        current_stage: str,
        actions: list[str],
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create a FULFILLING result."""
        return cls(
            state=EvaluationState.FULFILLING,
            current_stage=current_stage,
            proposed_stage=current_stage,
            actions=actions,
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def qualifying(
        cls,
        current_stage: str,
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create a QUALIFYING result."""
        return cls(
            state=EvaluationState.QUALIFYING,
            current_stage=current_stage,
            proposed_stage=current_stage,
            actions=["Ready to advance to next stage"],
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def awaiting(
        cls,
        current_stage: str,
        actions: list[str],
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create an AWAITING result."""
        return cls(
            state=EvaluationState.AWAITING,
            current_stage=current_stage,
            proposed_stage=current_stage,
            actions=actions,
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def advancing(
        cls,
        current_stage: str,
        proposed_stage: str,
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create an ADVANCING result."""
        return cls(
            state=EvaluationState.ADVANCING,
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            actions=[f"Transition to stage: {proposed_stage}"],
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def regressing(
        cls,
        current_stage: str,
        proposed_stage: str,
        actions: list[str],
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create a REGRESSING result."""
        return cls(
            state=EvaluationState.REGRESSING,
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            actions=actions,
            metadata=metadata or {},
            errors=errors or [],
        )

    @classmethod
    def completed(
        cls,
        metadata: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> "StatusResult":
        """Create a COMPLETED result."""
        return cls(
            state=EvaluationState.COMPLETED,
            current_stage=None,
            proposed_stage=None,
            actions=["Process completed"],
            metadata=metadata or {},
            errors=errors or [],
        )

    def has_errors(self) -> bool:
        """Check if result contains any errors."""
        return len(self.errors) > 0

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (completed or error)."""
        return self.state == EvaluationState.COMPLETED or self.has_errors()

    def summary(self) -> str:
        """Generate a human-readable summary of the result."""
        if self.has_errors():
            return f"Error in {self.state.value}: {'; '.join(self.errors)}"

        stage_info = f" (stage: {self.current_stage})" if self.current_stage else ""
        action_info = f" - {'; '.join(self.actions)}" if self.actions else ""

        return f"{self.state.value.title()}{stage_info}{action_info}"
