"""Gate composition and evaluation logic for StageFlow.

This module provides a declarative way to compose validation rules using AND logic.
Gates contain locks (atomic validators) or other gates, enabling nested
validation logic with short-circuit evaluation for performance.

Key Features:
- AND-only logical composition for simplicity and clarity
- Short-circuit evaluation for performance optimization
- Nested gate composition for validation trees
- Detailed evaluation results with comprehensive error reporting
- Immutable design for thread safety with tuple-based components
- Class method builders for easy construction

Example Usage:
    Basic gate creation:
        >>> gate1 = Gate.AND(lock1, lock2, lock3)
        >>> gate2 = Gate.AND(lock4, lock5)

    Nested composition:
        >>> complex_gate = Gate.AND(
        ...     gate1,
        ...     gate2,
        ...     lock6
        ... )

    Evaluation:
        >>> result = complex_gate.evaluate(element)
        >>> print(f"Passed: {result.passed}")
        >>> print(f"Messages: {result.messages}")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union

from stageflow.core.element import Element
from stageflow.gates.lock import Lock


class GateOperation(str, Enum):
    """Legacy gate operation enum for compatibility.

    StageFlow currently implements AND-only logic for gates. This enum exists
    to support older test fixtures and APIs that referenced OR/NOT. Non-AND
    operations are accepted for construction but not used to alter evaluation
    semantics.
    """

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass(frozen=True)
class GateResult:
    """Result of gate evaluation with comprehensive details.

    Contains success/failure status, lists of passed/failed components,
    error messages, and suggested actions for remediation.
    """

    passed: bool
    failed_components: tuple[Union[Lock, "Gate"], ...] = field(default_factory=tuple)
    passed_components: tuple[Union[Lock, "Gate"], ...] = field(default_factory=tuple)
    messages: tuple[str, ...] = field(default_factory=tuple)
    actions: tuple[str, ...] = field(default_factory=tuple)
    evaluation_time_ms: float = 0.0
    short_circuited: bool = False

    @property
    def has_failures(self) -> bool:
        """Check if any components failed."""
        return len(self.failed_components) > 0

    @property
    def has_passes(self) -> bool:
        """Check if any components passed."""
        return len(self.passed_components) > 0

    @property
    def total_components(self) -> int:
        """Total number of components evaluated."""
        return len(self.failed_components) + len(self.passed_components)


class Evaluable(ABC):
    """Abstract base for objects that can be evaluated against an Element."""

    @abstractmethod
    def evaluate(self, element: Element) -> GateResult:
        """Evaluate this component against an element."""
        pass

    @abstractmethod
    def get_property_paths(self) -> set[str]:
        """Get all property paths referenced by this component."""
        pass


@dataclass(frozen=True)
class LockWrapper(Evaluable):
    """Wrapper to make Lock conform to Evaluable interface."""

    lock: Lock

    def evaluate(self, element: Element) -> GateResult:
        """Evaluate the wrapped lock."""
        import time
        start_time = time.perf_counter()

        # Handle both new ValidationResult and legacy boolean returns
        result = self.lock.validate(element)
        if hasattr(result, 'success'):
            # New ValidationResult interface
            passed = result.success
        else:
            # Legacy boolean interface
            passed = result

        end_time = time.perf_counter()
        evaluation_time = (end_time - start_time) * 1000  # Convert to milliseconds

        if passed:
            return GateResult(
                passed=True,
                passed_components=(self.lock,),
                evaluation_time_ms=evaluation_time
            )
        else:
            # Try to get messages from lock if available
            messages = []
            actions = []
            try:
                messages.append(self.lock.get_failure_message(element))
                actions.append(self.lock.get_action_message(element))
            except AttributeError:
                # Fallback if methods don't exist
                messages.append(f"Lock validation failed for {self.lock.property_path}")
                actions.append(f"Check property {self.lock.property_path}")

            return GateResult(
                passed=False,
                failed_components=(self.lock,),
                messages=tuple(messages),
                actions=tuple(actions),
                evaluation_time_ms=evaluation_time
            )

    def get_property_paths(self) -> set[str]:
        """Get property paths from the wrapped lock."""
        return {str(self.lock.property_path)}


@dataclass(frozen=True)
class Gate(Evaluable):
    """
    Composable validation gate that can contain locks or other gates.

    Gates support logical composition with AND operations only,
    providing short-circuit evaluation for performance and detailed
    error reporting for debugging.

    Gates are immutable and thread-safe, making them suitable for
    concurrent evaluation scenarios.
    """

    name: str
    components: tuple[Evaluable, ...] | None = None
    target_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Compatibility fields (legacy API):
    locks: list[Lock] | tuple[Lock, ...] | None = None
    logic: GateOperation = GateOperation.AND

    def __post_init__(self):
        """Validate gate configuration after initialization and handle legacy API."""
        if not self.name:
            raise ValueError("Gate must have a name")

        # If components are not provided, allow legacy construction via locks + logic
        comps = self.components if self.components is not None else ()
        if not comps:
            if self.locks:
                wrapped = tuple(LockWrapper(lock) for lock in (self.locks if isinstance(self.locks, (list, tuple)) else [self.locks]))
                object.__setattr__(self, "components", wrapped)
            else:
                raise ValueError("Gate must contain at least one component")
        else:
            # Ensure components is a tuple for immutability
            if not isinstance(comps, tuple):
                object.__setattr__(self, "components", tuple(comps))

        # Preserve legacy logic info without altering evaluation semantics
        if self.logic != GateOperation.AND:
            md = dict(self.metadata) if self.metadata else {}
            md.setdefault("legacy_logic", self.logic.value if isinstance(self.logic, GateOperation) else str(self.logic))
            object.__setattr__(self, "metadata", md)

    @classmethod
    def create(
        cls,
        *components: Union[Lock, "Gate"],
        name: str | None = None,
        target_stage: str | None = None,
        **metadata,
    ) -> "Gate":
        """Create a gate that requires all components to pass (AND logic).

        Args:
            *components: Locks or Gates to combine with AND logic
            name: Optional name for the gate (auto-generated if not provided)
            target_stage: Optional target stage name for successful evaluation
            **metadata: Additional metadata for the gate

        Returns:
            Gate configured with AND operation

        Example:
            >>> gate = Gate.create(lock1, lock2, lock3, name="profile_complete", target_stage="next_stage")
        """
        if not components:
            raise ValueError("Gate requires at least one component")

        # Wrap locks in LockWrapper
        wrapped_components: list[Evaluable] = []
        for comp in components:
            if isinstance(comp, Lock):
                wrapped_components.append(LockWrapper(comp))
            elif isinstance(comp, Gate):
                wrapped_components.append(comp)
            else:
                raise TypeError(f"Components must be Lock or Gate, got {type(comp)}")

        if name is None:
            name = f"gate_{len(wrapped_components)}_components"

        return cls(
            name=name,
            components=tuple(wrapped_components),
            target_stage=target_stage,
            metadata=metadata,
        )

    @classmethod
    def AND(cls, *components: Union[Lock, "Gate"], name: str | None = None, **metadata) -> "Gate":
        """Create an AND gate that requires all components to pass.

        DEPRECATED: Use Gate.create() instead.

        Args:
            *components: Locks or Gates to combine with AND logic
            name: Optional name for the gate (auto-generated if not provided)
            **metadata: Additional metadata for the gate

        Returns:
            Gate configured with AND operation

        Example:
            >>> gate = Gate.AND(lock1, lock2, lock3, name="profile_complete")
        """
        return cls.create(*components, name=name, **metadata)

    def evaluate(self, element: Element) -> GateResult:
        """
        Evaluate this gate against an element with short-circuit optimization.
        Uses AND logic - all components must pass for the gate to pass.

        Args:
            element: Element to evaluate

        Returns:
            GateResult with evaluation outcome and details
        """
        import time
        start_time = time.perf_counter()

        passed_components: list[Union[Lock, Gate]] = []
        failed_components: list[Union[Lock, Gate]] = []
        all_messages: list[str] = []
        all_actions: list[str] = []
        short_circuited = False

        # mypy: components is set in __post_init__
        assert self.components is not None

        for i, component in enumerate(self.components):
            result = component.evaluate(element)

            if result.passed:
                passed_components.append(component)
            else:
                failed_components.append(component)
                all_messages.extend(result.messages)
                all_actions.extend(result.actions)

            # Short-circuit evaluation for AND: Stop on first failure
            if not result.passed:
                short_circuited = i < len(self.components) - 1
                break

        # AND logic: All components must pass
        gate_passed = len(failed_components) == 0

        end_time = time.perf_counter()
        evaluation_time = (end_time - start_time) * 1000  # Convert to milliseconds

        return GateResult(
            passed=gate_passed,
            failed_components=tuple(failed_components),
            passed_components=tuple(passed_components),
            messages=tuple(all_messages),
            actions=tuple(all_actions),
            evaluation_time_ms=evaluation_time,
            short_circuited=short_circuited,
        )

    def get_property_paths(self) -> set[str]:
        """
        Get all property paths referenced by this gate and its components.

        Returns:
            Set of property paths
        """
        paths = set()
        assert self.components is not None
        for component in self.components:
            paths.update(component.get_property_paths())
        return paths

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
        Get human-readable summary of gate logic.

        Returns:
            Summary string describing gate operation and components
        """
        assert self.components is not None
        component_count = len(self.components)
        target_desc = f" → {self.target_stage}" if self.target_stage else ""
        return f"Gate '{self.name}' requires all {component_count} components to pass{target_desc}"

    def get_complexity(self) -> int:
        """
        Calculate the complexity of this gate (total number of locks).

        Returns:
            Total number of locks in this gate and all nested gates
        """
        assert self.components is not None
        complexity = 0
        for component in self.components:
            if isinstance(component, LockWrapper):
                complexity += 1
            elif isinstance(component, Gate):
                complexity += component.get_complexity()
        return complexity

    def validate_structure(self) -> list[str]:
        """
        Validate gate structure for potential issues.

        Returns:
            List of validation warnings/errors
        """
        issues: list[str] = []

        # Check for excessive nesting depth
        max_depth = self._get_max_depth()
        if max_depth > 5:
            issues.append(f"Gate has deep nesting (depth {max_depth}), consider flattening")

        # Check for excessive complexity
        complexity = self.get_complexity()
        if complexity > 100:
            issues.append(f"Gate has high complexity ({complexity} locks), consider breaking down")

        # No specific validation needed for AND-only gates

        return issues

    def is_compatible_with(self, other: "Gate") -> bool:
        """
        Check if this gate is compatible with another gate for use in the same stage.

        Args:
            other: Another gate to check compatibility with

        Returns:
            True if gates are compatible, False otherwise
        """
        # For now, assume all gates are compatible
        # This could be extended to check for conflicting property requirements
        # or other logical incompatibilities
        return True

    def _get_max_depth(self, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of this gate."""
        assert self.components is not None
        max_depth = current_depth
        for component in self.components:
            if isinstance(component, Gate):
                depth = component._get_max_depth(current_depth + 1)
                max_depth = max(max_depth, depth)
        return max_depth
