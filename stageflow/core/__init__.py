"""
Core domain models for StageFlow.

This module contains the fundamental building blocks of the StageFlow framework:
- Element: Data wrapper interface
- Lock: Individual validation constraints
- Gate: Composed validation rules
- Stage: Validation stages with gates
- Process: Multi-stage workflow orchestration
- StatusResult: Evaluation outcomes
"""

from stageflow.core.element import Element
from stageflow.core.gate import Gate
from stageflow.core.lock import Lock, LockType
from stageflow.core.process import Process
from stageflow.core.result import EvaluationState, StatusResult
from stageflow.core.schema import ItemSchema
from stageflow.core.stage import Stage

__all__ = [
    "Element",
    "Lock",
    "LockType",
    "Gate",
    "Stage",
    "Process",
    "StatusResult",
    "EvaluationState",
    "ItemSchema",
]
