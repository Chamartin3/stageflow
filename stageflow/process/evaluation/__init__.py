"""
Process evaluation framework for StageFlow.

This module contains the modular evaluation components that implement
the 7-state evaluation flow with clean separation of concerns.
"""

from .pipeline import ProcessEvaluationPipeline
from .state_machine import EvaluationContext, ProcessStateMachine
from .strategies import (
    DefaultStageEvaluationStrategy,
    GateEvaluationStrategy,
    StageEvaluationStrategy,
)

__all__ = [
    "ProcessStateMachine",
    "EvaluationContext",
    "StageEvaluationStrategy",
    "GateEvaluationStrategy",
    "DefaultStageEvaluationStrategy",
    "ProcessEvaluationPipeline",
]
