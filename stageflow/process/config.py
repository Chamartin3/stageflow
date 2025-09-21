"""Process configuration for StageFlow."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProcessConfig:
    """
    Configuration for process initialization and behavior.

    Contains all configurable aspects of process behavior including
    validation settings, performance options, and metadata.
    """

    name: str
    initial_stage: str | None = None
    final_stage: str | None = None
    allow_stage_skipping: bool = False
    regression_detection: bool = True
    max_batch_size: int = 1000
    metadata: dict[str, Any] = field(default_factory=dict)
