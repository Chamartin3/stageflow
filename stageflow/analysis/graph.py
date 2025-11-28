"""Graph analysis for StageFlow processes.

Handles process-wide structural analysis including:
- Path finding (reachability)
- Cycle detection and classification
- Dead-end and unreachable stage detection
- Orphaned stage detection
"""

from stageflow.models import (
    ConsistencyIssue,
    IssueSeverity,
    ProcessGraph,
    ProcessIssueTypes,
)


class GraphAnalyzer:
    """Analyzes process graph structure for reachability and cycles.

    Issues returned:
        - DEAD_END_STAGE
        - UNREACHABLE_STAGE
        - INFINITE_CYCLE
        - UNCONTROLLED_CYCLE
        - FINAL_STAGE_HAS_GATES
        - ORPHANED_STAGE
    """

    def __init__(self, graph: ProcessGraph):
        """Initialize with graph topology data only."""
        self.graph = graph

    def get_issues(self) -> list[ConsistencyIssue]:
        """Run all graph-based analysis checks."""
        issues: list[ConsistencyIssue] = []
        issues.extend(self._check_dead_end_stages())
        issues.extend(self._check_unreachable_stages())
        issues.extend(self._check_circular_dependencies())
        issues.extend(self._check_final_stage_has_gates())
        issues.extend(self._check_orphaned_stages())
        return issues

    # =========================================================================
    # Dead-end and Unreachable Detection
    # =========================================================================

    def _check_dead_end_stages(self) -> list[ConsistencyIssue]:
        """Identify non-final stages that cannot reach the final stage."""
        issues: list[ConsistencyIssue] = []

        for stage_id in self.graph.stage_ids:
            if stage_id == self.graph.final_id:
                continue
            if not self.graph.has_path(stage_id, self.graph.final_id):
                issues.append(ConsistencyIssue(
                    issue_type=ProcessIssueTypes.DEAD_END_STAGE,
                    description=f"Stage '{stage_id}' cannot reach final stage '{self.graph.final_id}'",
                    stages=[stage_id],
                    severity=IssueSeverity.WARNING,
                ))
        return issues

    def _check_unreachable_stages(self) -> list[ConsistencyIssue]:
        """Identify stages that cannot be reached from the initial stage."""
        issues: list[ConsistencyIssue] = []

        for stage_id in self.graph.stage_ids:
            if stage_id == self.graph.initial_id:
                continue
            if not self.graph.has_path(self.graph.initial_id, stage_id):
                # Only report if it also can't reach final (orphaned)
                if not self.graph.has_path(stage_id, self.graph.final_id):
                    issues.append(ConsistencyIssue(
                        issue_type=ProcessIssueTypes.UNREACHABLE_STAGE,
                        description=f"Stage '{stage_id}' is unreachable from initial stage '{self.graph.initial_id}'",
                        stages=[stage_id],
                        severity=IssueSeverity.FATAL,
                    ))
        return issues

    def _check_final_stage_has_gates(self) -> list[ConsistencyIssue]:
        """Check that final stage does not have outgoing gates."""
        issues: list[ConsistencyIssue] = []

        if self.graph.final_id in self.graph.stages_with_gates:
            targets = self.graph.get_targets(self.graph.final_id)
            issues.append(ConsistencyIssue(
                issue_type=ProcessIssueTypes.FINAL_STAGE_HAS_GATES,
                description=f"Final stage '{self.graph.final_id}' has outgoing gates targeting: {', '.join(targets)}. Final stages should not have transitions.",
                stages=[self.graph.final_id],
                severity=IssueSeverity.FATAL,
            ))
        return issues

    def _check_orphaned_stages(self) -> list[ConsistencyIssue]:
        """Identify stages with no gates that aren't final or referenced."""
        issues: list[ConsistencyIssue] = []

        # Get all target stages from transitions
        target_stages = {to_id for _, to_id in self.graph.edges}

        for stage_id in self.graph.stage_ids:
            # Skip stages with gates or final stages
            if stage_id in self.graph.stages_with_gates or stage_id == self.graph.final_id:
                continue

            # Stage has no gates, not final - should be a target
            if stage_id not in target_stages:
                issues.append(ConsistencyIssue(
                    issue_type=ProcessIssueTypes.ORPHANED_STAGE,
                    description=(
                        f"Stage '{stage_id}' has no gates, is not final, "
                        f"and is not referenced by any other stage"
                    ),
                    stages=[stage_id],
                    severity=IssueSeverity.WARNING,
                ))

        return issues

    # =========================================================================
    # Cycle Detection and Classification
    # =========================================================================

    def _check_circular_dependencies(self) -> list[ConsistencyIssue]:
        """Enhanced cycle detection with intelligent classification."""
        issues: list[ConsistencyIssue] = []
        cycles = self._detect_all_cycles()

        for cycle_path in cycles:
            has_exit = self._cycle_has_exit_to_final(cycle_path)

            if not has_exit:
                issues.append(self._create_infinite_cycle_issue(cycle_path))
                continue

            # For now, cycles with exits are considered controlled
            # More detailed termination analysis would need lock data
            # which is outside GraphAnalyzer's scope

        return issues

    def _detect_all_cycles(self) -> list[list[str]]:
        """Detect all cycles using DFS."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(stage_id: str) -> None:
            visited.add(stage_id)
            rec_stack.add(stage_id)
            path.append(stage_id)

            for target in self.graph.get_targets(stage_id):
                if target not in visited:
                    dfs(target)
                elif target in rec_stack:
                    cycle_start = path.index(target)
                    cycles.append(path[cycle_start:] + [target])

            path.pop()
            rec_stack.remove(stage_id)

        for stage_id in self.graph.stage_ids:
            if stage_id not in visited:
                dfs(stage_id)

        return cycles

    def _cycle_has_exit_to_final(self, cycle_path: list[str]) -> bool:
        """Check if any stage in cycle can reach final stage via non-cycle path."""
        cycle_stages = set(cycle_path[:-1])

        for stage_id in cycle_stages:
            if self.graph.has_path(stage_id, self.graph.final_id, exclude=cycle_stages):
                return True
        return False

    def _create_infinite_cycle_issue(self, cycle_path: list[str]) -> ConsistencyIssue:
        """Create issue for infinite cycle (no exit path)."""
        return ConsistencyIssue(
            issue_type=ProcessIssueTypes.INFINITE_CYCLE,
            description=f"Infinite cycle with no path to final stage: {' → '.join(cycle_path)}",
            stages=cycle_path,
            severity=IssueSeverity.FATAL,
            details={"cycle_path": cycle_path},
        )
