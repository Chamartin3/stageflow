"""Gate-level analysis for StageFlow processes.

Handles single gate validation including:
- Self-referencing gate detection
- Lock conflict detection
"""

from stageflow.models import (
    ConsistencyIssue,
    GateDefinition,
    IssueSeverity,
    LockType,
    ProcessIssueTypes,
)


class GateAnalyzer:
    """Analyzes a single gate for issues.

    Issues returned:
        - SELF_REFERENCING_GATE
        - LOGICAL_CONFLICT
    """

    def __init__(self, gate: GateDefinition, stage_id: str):
        """Initialize with single gate data.

        Args:
            gate: Gate definition to analyze
            stage_id: Parent stage identifier
        """
        self.gate = gate
        self.stage_id = stage_id

    def get_issues(self) -> list[ConsistencyIssue]:
        """Run all gate-based analysis checks."""
        issues: list[ConsistencyIssue] = []
        issues.extend(self._check_self_referencing())
        issues.extend(self._check_logical_conflicts())
        return issues

    def _check_self_referencing(self) -> list[ConsistencyIssue]:
        """Check if gate targets its own stage (self-loop)."""
        if self.gate.get("target_stage") == self.stage_id:
            return [ConsistencyIssue(
                issue_type=ProcessIssueTypes.SELF_REFERENCING_GATE,
                description=f"Gate '{self.gate['name']}' in stage '{self.stage_id}' targets itself, creating a self-loop",
                stages=[self.stage_id],
                severity=IssueSeverity.WARNING,
            )]
        return []

    def _check_logical_conflicts(self) -> list[ConsistencyIssue]:
        """Identify logical conflicts within gate lock conditions."""
        issues: list[ConsistencyIssue] = []
        locks = self.gate.get("locks", [])

        if not locks:
            return issues

        conflicts = self._detect_lock_conflicts(locks)
        for conflict in conflicts:
            issues.append(ConsistencyIssue(
                issue_type=ProcessIssueTypes.LOGICAL_CONFLICT,
                description=f"Gate '{self.gate['name']}' in stage '{self.stage_id}' has conflicting conditions: {conflict}",
                stages=[self.stage_id],
                severity=IssueSeverity.FATAL,
            ))
        return issues

    def _detect_lock_conflicts(self, locks: list) -> list[str]:
        """Detect logical conflicts between locks."""
        conflicts: list[str] = []

        # Group locks by property
        by_property: dict[str, list] = {}
        for lock in locks:
            if not isinstance(lock, dict):
                continue
            prop = lock.get("property_path")
            if prop:
                if prop not in by_property:
                    by_property[prop] = []
                by_property[prop].append(lock)

        # Check each property group
        for prop, prop_locks in by_property.items():
            conflict = self._detect_property_conflicts(prop, prop_locks)
            if conflict:
                conflicts.append(conflict)

        return conflicts

    def _detect_property_conflicts(self, prop: str, locks: list) -> str | None:
        """Detect conflicts between locks on the same property."""
        if len(locks) < 2:
            return None

        # Extract lock info
        equals_values: list = []
        gt_values: list[float] = []
        lt_values: list[float] = []

        for lock in locks:
            lock_type = lock.get("type")
            expected = lock.get("expected_value")

            if lock_type == LockType.EQUALS.value or lock_type == "equals":
                equals_values.append(expected)
            elif lock_type in (LockType.GREATER_THAN.value, "greater_than") and isinstance(expected, (int, float)):
                gt_values.append(expected)
            elif lock_type in (LockType.LESS_THAN.value, "less_than") and isinstance(expected, (int, float)):
                lt_values.append(expected)

        # Check for multiple different EQUALS values
        if len(equals_values) > 1:
            unique = {str(v) for v in equals_values}
            if len(unique) > 1:
                return f"Property '{prop}' must equal multiple different values: {', '.join(unique)}"

        # Check GREATER_THAN vs LESS_THAN conflicts
        for gt in gt_values:
            for lt in lt_values:
                if gt >= lt:
                    return f"Property '{prop}' must be > {gt} AND < {lt} (impossible)"

        # Check EQUALS vs bounds conflicts
        for eq in equals_values:
            if isinstance(eq, (int, float)):
                for gt in gt_values:
                    if eq <= gt:
                        return f"Property '{prop}' must equal {eq} AND be > {gt} (impossible)"
                for lt in lt_values:
                    if eq >= lt:
                        return f"Property '{prop}' must equal {eq} AND be < {lt} (impossible)"

        return None
