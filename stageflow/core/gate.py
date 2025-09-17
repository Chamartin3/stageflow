"""Gate composition and evaluation logic for StageFlow."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from stageflow.core.element import Element
from stageflow.core.lock import Lock, LockType


class GateLogic(Enum):
    """
    Logic operators for combining locks within a gate.

    - AND: All locks must pass for gate to pass
    - OR: At least one lock must pass for gate to pass
    - XOR: Exactly one lock must pass for gate to pass
    - NOT: All locks must fail for gate to pass
    """

    AND = "and"
    OR = "or"
    XOR = "xor"
    NOT = "not"


@dataclass(frozen=True)
class GateResult:
    """Result of gate evaluation against an element."""

    passed: bool
    failed_locks: list[Lock]
    passed_locks: list[Lock]
    messages: list[str]
    actions: list[str]

    @property
    def has_failures(self) -> bool:
        """Check if any locks failed."""
        return len(self.failed_locks) > 0

    @property
    def has_passes(self) -> bool:
        """Check if any locks passed."""
        return len(self.passed_locks) > 0


@dataclass(frozen=True)
class Gate:
    """
    Composed validation rule consisting of multiple locks.

    Gates evaluate collections of locks using specified logic operators
    to determine if an element meets the gate's criteria.
    """

    name: str
    locks: list[Lock]
    logic: GateLogic = GateLogic.AND
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Validate gate configuration after initialization."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        if not self.locks:
            raise ValueError("Gate must contain at least one lock")

        if not self.name:
            raise ValueError("Gate must have a name")

        # Validate no duplicate property paths within same gate
        property_paths = [lock.property_path for lock in self.locks]
        if len(property_paths) != len(set(property_paths)):
            duplicates = {path for path in property_paths if property_paths.count(path) > 1}
            raise ValueError(f"Gate '{self.name}' has duplicate property paths: {duplicates}")

    def evaluate(self, element: Element) -> GateResult:
        """
        Evaluate element against this gate's locks.

        Args:
            element: Element to evaluate

        Returns:
            GateResult containing evaluation outcome and details
        """
        passed_locks = []
        failed_locks = []
        messages = []
        actions = []

        # Evaluate each lock
        for lock in self.locks:
            if lock.validate(element):
                passed_locks.append(lock)
            else:
                failed_locks.append(lock)
                messages.append(lock.get_failure_message(element))
                actions.append(lock.get_action_message(element))

        # Apply gate logic
        gate_passed = self._apply_logic(passed_locks, failed_locks)

        return GateResult(
            passed=gate_passed,
            failed_locks=failed_locks,
            passed_locks=passed_locks,
            messages=messages,
            actions=actions,
        )

    def _apply_logic(self, passed_locks: list[Lock], failed_locks: list[Lock]) -> bool:
        """
        Apply gate logic to determine if gate passes.

        Args:
            passed_locks: Locks that passed validation
            failed_locks: Locks that failed validation

        Returns:
            True if gate passes according to logic, False otherwise
        """
        total_locks = len(passed_locks) + len(failed_locks)
        passed_count = len(passed_locks)

        if self.logic == GateLogic.AND:
            return passed_count == total_locks

        if self.logic == GateLogic.OR:
            return passed_count > 0

        if self.logic == GateLogic.XOR:
            return passed_count == 1

        if self.logic == GateLogic.NOT:
            return passed_count == 0

        return False

    def get_property_paths(self) -> set[str]:
        """
        Get all property paths referenced by this gate's locks.

        Returns:
            Set of property paths
        """
        return {lock.property_path for lock in self.locks}

    def requires_property(self, property_path: str) -> bool:
        """
        Check if gate requires a specific property.

        Args:
            property_path: Property path to check

        Returns:
            True if gate references this property
        """
        return property_path in self.get_property_paths()

    def get_summary(self) -> str:
        """
        Get human-readable summary of gate requirements.

        Returns:
            Summary string describing gate logic and locks
        """
        lock_count = len(self.locks)
        logic_desc = {
            GateLogic.AND: f"all {lock_count} conditions",
            GateLogic.OR: f"at least 1 of {lock_count} conditions",
            GateLogic.XOR: f"exactly 1 of {lock_count} conditions",
            GateLogic.NOT: f"none of {lock_count} conditions",
        }

        return f"Gate '{self.name}' requires {logic_desc[self.logic]} to pass"

    def is_compatible_with(self, other: "Gate") -> bool:
        """
        Check if this gate is logically compatible with another gate.

        Gates are compatible if they don't have conflicting requirements
        for the same properties. This implementation allows multiple gates
        to reference the same properties with different validations.

        Args:
            other: Other gate to check compatibility with

        Returns:
            True if gates are compatible, False otherwise
        """
        # Gates are generally compatible unless they have directly conflicting
        # requirements for the same property (e.g., one requires a value to be
        # "true" and another requires it to be "false")

        shared_properties = self.get_property_paths() & other.get_property_paths()

        if not shared_properties:
            return True

        # For shared properties, check for direct conflicts
        for prop in shared_properties:
            self_locks = [lock for lock in self.locks if lock.property_path == prop]
            other_locks = [lock for lock in other.locks if lock.property_path == prop]

            # Check for conflicting EQUALS locks on same property
            self_equals = [lock for lock in self_locks if lock.lock_type == LockType.EQUALS]
            other_equals = [lock for lock in other_locks if lock.lock_type == LockType.EQUALS]

            if self_equals and other_equals:
                # Check if any EQUALS locks have different expected values
                for self_lock in self_equals:
                    for other_lock in other_equals:
                        if self_lock.expected_value != other_lock.expected_value:
                            return False

            # Check for EXISTS vs NOT EXISTS conflicts
            self_exists = [lock for lock in self_locks if lock.lock_type == LockType.EXISTS]
            other_exists = [lock for lock in other_locks if lock.lock_type == LockType.EXISTS]

            if self_exists and other_exists:
                for self_lock in self_exists:
                    for other_lock in other_exists:
                        # If one requires exists=True and other requires exists=False
                        if (self_lock.expected_value is not False and
                            other_lock.expected_value is False) or \
                           (self_lock.expected_value is False and
                            other_lock.expected_value is not False):
                            return False

        return True
