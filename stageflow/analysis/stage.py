"""Stage-level analysis for StageFlow processes.

Handles single stage validation including:
- Schema transformation checks
- Gate grouping analysis (duplicate targets, duplicate schemas)
"""

import json

from stageflow.models import (
    ConsistencyIssue,
    IssueSeverity,
    ProcessIssueTypes,
    StageSchemaMutations,
)


class StageAnalyzer:
    """Analyzes a single stage for schema and gate issues.

    Issues returned:
        - EMPTY_STAGE_TRANSFORMATION
        - MULTIPLE_GATES_SAME_TARGET
        - DUPLICATE_GATE_SCHEMAS
    """

    def __init__(self, mutations: StageSchemaMutations):
        """Initialize with stage schema mutations data.

        Args:
            mutations: Schema transformation data for this stage
        """
        self.mutations = mutations

    def get_issues(self) -> list[ConsistencyIssue]:
        """Run all stage-based analysis checks."""
        # Skip final stages - they don't need transformation checks
        if self.mutations.is_final:
            return []

        issues: list[ConsistencyIssue] = []
        issues.extend(self._check_schema_transformations())
        issues.extend(self._check_multiple_gates_same_target())
        issues.extend(self._check_duplicate_gate_schemas())
        return issues

    def _check_schema_transformations(self) -> list[ConsistencyIssue]:
        """Validate that gates perform meaningful schema transformations."""
        issues: list[ConsistencyIssue] = []

        initial_props = self.mutations.initial_schema.get("properties", {})

        for gate_name, final_schema in self.mutations.final_schemas.items():
            final_props = final_schema.get("properties", {})

            # Schema must change (add or modify properties)
            if final_props == initial_props:
                issues.append(ConsistencyIssue(
                    issue_type=ProcessIssueTypes.EMPTY_STAGE_TRANSFORMATION,
                    description=(
                        f"Gate '{gate_name}' in stage '{self.mutations.stage_id}' doesn't transform the schema. "
                        f"Gate locks should add new properties or modify existing ones."
                    ),
                    stages=[self.mutations.stage_id],
                    severity=IssueSeverity.WARNING,
                    details={
                        "gate": gate_name,
                        "existing_properties": list(initial_props.keys()),
                    },
                ))

        return issues

    def _check_multiple_gates_same_target(self) -> list[ConsistencyIssue]:
        """Check for multiple gates targeting the same stage."""
        issues: list[ConsistencyIssue] = []

        target_to_gates: dict[str, list[str]] = {}
        for gate in self.mutations.gates:
            target = gate.get("target_stage")
            if target:
                if target not in target_to_gates:
                    target_to_gates[target] = []
                target_to_gates[target].append(gate["name"])

        # Report duplicates
        for target, gate_names in target_to_gates.items():
            if len(gate_names) > 1:
                issues.append(ConsistencyIssue(
                    issue_type=ProcessIssueTypes.MULTIPLE_GATES_SAME_TARGET,
                    description=(
                        f"Stage '{self.mutations.stage_id}' has multiple gates targeting '{target}': "
                        f"{', '.join(gate_names)}. Consider combining into a single gate."
                    ),
                    stages=[self.mutations.stage_id],
                    severity=IssueSeverity.WARNING,
                ))

        return issues

    def _check_duplicate_gate_schemas(self) -> list[ConsistencyIssue]:
        """Check for gates that produce identical validation conditions.

        Two gates with the same lock conditions (property paths AND expected values)
        create ambiguous routing - an element satisfying those conditions would
        match both gates.
        """
        issues: list[ConsistencyIssue] = []

        # Compare gate lock conditions (normalized to be order-independent)
        seen_conditions: dict[frozenset, str] = {}  # normalized locks → first gate_name

        for gate in self.mutations.gates:
            gate_name = gate["name"]
            locks = gate.get("locks", [])

            # Normalize locks: extract key conditions and sort
            normalized = self._normalize_locks(locks)

            if normalized in seen_conditions:
                other_name = seen_conditions[normalized]
                issues.append(ConsistencyIssue(
                    issue_type=ProcessIssueTypes.DUPLICATE_GATE_SCHEMAS,
                    description=(
                        f"Gates '{gate_name}' and '{other_name}' in stage '{self.mutations.stage_id}' "
                        f"have identical lock conditions. An element satisfying these conditions would "
                        f"match both gates, creating ambiguous routing."
                    ),
                    stages=[self.mutations.stage_id],
                    severity=IssueSeverity.FATAL,
                    details={
                        "gates": [gate_name, other_name],
                    },
                ))
            else:
                seen_conditions[normalized] = gate_name

        return issues

    def _normalize_locks(self, locks: list) -> frozenset:
        """Normalize locks to an order-independent hashable representation."""
        normalized = []
        for lock in locks:
            if isinstance(lock, dict):
                # Handle shorthand: {exists: "prop"}
                if "exists" in lock:
                    normalized.append(("exists", lock["exists"]))
                else:
                    # Full form: {type, property_path, expected_value}
                    lock_type = str(lock.get("type", "")).upper()
                    prop = lock.get("property_path", "")
                    value = lock.get("expected_value")
                    normalized.append((lock_type, prop, json.dumps(value, sort_keys=True) if value is not None else None))
        return frozenset(normalized)
