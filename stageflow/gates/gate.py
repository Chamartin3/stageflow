"""Gate composition and evaluation logic for StageFlow.

This module provides a declarative way to compose validation rules using AND logic.
"""

from dataclasses import dataclass, field
from typing import Any, TypedDict

from stageflow.element import Element
from stageflow.gates.lock import Lock, LockDefinition, LockFactory, LockResult


class GateDefinition(TypedDict):
    name: str
    description: str
    target_stage: str
    parent_stage: str
    locks: list[LockDefinition]


@dataclass(frozen=True)
class GateResult:
    """Result of gate evaluation with comprehensive details.

    Contains success/failure status, lists of passed/failed components,
    error messages, and suggested actions for remediation.
    """

    success: bool
    success_rate: float = 0.0
    failed: list[LockResult] = field(default_factory=list)
    passed: list[LockResult] = field(default_factory=list)

    @property
    def messages(self) -> list[str]:
        """Aggregate messages from all failed components."""
        msgs = []
        for lock in self.failed:
            msgs.extend(lock.error_message)
        return msgs


class Gate:
    """
    Composable validation that validates an Element against multiple Locks, in order.
    """

    name: str
    target_stage: str
    _locks: list[Lock]

    def __init__(self,gate_config: GateDefinition):
        name = gate_config.get('name')
        if not name:
            raise ValueError("Gate must have a name")
        self.name = name
        self.description = gate_config.get('description', '')
        self.target_stage = gate_config.get('target_stage')
        locks = [
            LockFactory.create(lock_def) for lock_def in gate_config.get('locks', [])
        ]

        self.target_stage = gate_config.get('target_stage')
        if not locks  or not self.target_stage:
            raise ValueError("Gate must have at least one lock and a target stage")

        self._locks = locks


    @classmethod
    def create(
            cls, config: GateDefinition
    ) -> "Gate":
        return cls(config)


    def evaluate(self, element: Element) -> GateResult:

        passed = []
        failed = []
        for lock in self._locks:
            result: LockResult = lock.validate(element)
            if result.success:
                passed.append(lock)
            else:
                failed.append(lock)
        gate_passed = len(failed) == 0
        success_rate = len(passed) / len(self._locks) if self._locks else 0.0

        return GateResult(
            success=gate_passed,
            failed=failed,
            passed=passed,
            success_rate=success_rate,
        )

    @property
    def required_paths(self) -> set[str]:
        """Get all property paths required by the gate."""
        paths = set()
        for lock in self._locks:
            paths.update(lock.property_path)
        return paths

