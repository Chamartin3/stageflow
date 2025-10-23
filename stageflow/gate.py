"""Gate composition and evaluation logic for StageFlow.

This module provides a declarative way to compose validation rules using AND logic.
"""

from dataclasses import dataclass, field
from typing import TypedDict

from stageflow.element import Element
from stageflow.lock import Lock, LockDefinition, LockFactory, LockResult


class GateDefinition(TypedDict):
    name: str
    description: str
    target_stage: str
    parent_stage: str | None
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
        for lock_result in self.failed:
            if lock_result.error_message:
                msgs.append(lock_result.error_message)
        return msgs

    def get_contextualized_messages(self, gate_name: str, target_stage: str) -> list[str]:
        """Get failure messages with gate context included.

        Args:
            gate_name: Name of the gate that failed
            target_stage: Target stage this gate would transition to

        Returns:
            List of error messages with transition context
        """
        if not self.failed:
            return []

        # Create header describing the transition
        header = f"To transition via '{gate_name}' to stage '{target_stage}':"

        # Add individual lock failures with indentation
        msgs = [header]
        for lock_result in self.failed:
            if lock_result.error_message:
                msgs.append(f"  → {lock_result.error_message}")

        return msgs


class Gate:
    """
    Composable validation that validates an Element against multiple Locks, in order.
    """

    name: str
    target_stage: str
    _locks: list[Lock]

    def __init__(self, gate_config: GateDefinition, parent_stage: str | None = None):
        name = gate_config.get('name')
        if not name:
            raise ValueError("Gate must have a name")
        self.name = name
        self.description = gate_config.get('description', '')
        self.target_stage = gate_config.get('target_stage')
        self.parent_stage = parent_stage
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
        """Evaluate element against all locks using AND logic."""
        passed = []
        failed = []

        for lock in self._locks:
            result: LockResult = lock.validate(element)
            if result.success:
                passed.append(result)
            else:
                failed.append(result)

        gate_passed = len(failed) == 0
        success_rate = len(passed) / len(self._locks) if self._locks else 0.0

        return GateResult(
            success=gate_passed,
            failed=failed,
            passed=passed,
            success_rate=success_rate,
        )

    @property
    def locks(self) -> list[Lock]:
        """Get all locks in this gate."""
        return self._locks.copy()

    @property
    def required_paths(self) -> set[str]:
        """Get all property paths required by the gate."""
        paths = set()
        for lock in self._locks:
            paths.add(lock.property_path)
        return paths

    def lock_to_dict(self) -> list[LockDefinition]:
        """Serialize locks to a list of dictionaries."""
        return [lock.to_dict() for lock in self._locks]

    def to_dict(self) -> GateDefinition:
        """Serialize gate to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "target_stage": self.target_stage,
            "locks": self.lock_to_dict(),
        }

