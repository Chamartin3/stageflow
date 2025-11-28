"""Main ProcessAnalyzer for StageFlow process validation.

Orchestrates sub-analyzers to provide comprehensive process analysis:
- GraphAnalyzer: Process-wide structural analysis (paths, cycles, reachability)
- GateAnalyzer: Single gate validation (self-reference, lock conflicts)
- StageAnalyzer: Single stage validation (schema transformations, gate grouping)

Usage:
    from stageflow.analysis import ProcessAnalyzer

    analyzer = ProcessAnalyzer(graph, stage_mutations)
    issues = analyzer.get_issues()
"""

from stageflow.models import (
    ConsistencyIssue,
    ProcessGraph,
    StageSchemaMutations,
)

from .gate import GateAnalyzer
from .graph import GraphAnalyzer
from .stage import StageAnalyzer


class ProcessAnalyzer:
    """Unified process analyzer orchestrating scope-specific sub-analyzers.

    Receives pre-extracted data models and delegates to specialized analyzers.
    Each sub-analyzer receives only the data it needs.

    Attributes:
        graph: Process graph topology
        stage_mutations: Schema mutations for each stage
    """

    def __init__(self, graph: ProcessGraph, stage_mutations: list[StageSchemaMutations]):
        """Initialize ProcessAnalyzer with extracted data.

        Args:
            graph: Process graph topology for structural analysis
            stage_mutations: Schema mutations for stage/gate analysis
        """
        self._graph = graph
        self._stage_mutations = stage_mutations

    def get_issues(self) -> list[ConsistencyIssue]:
        """Run all analysis checks.

        Returns:
            List of all detected issues
        """
        issues: list[ConsistencyIssue] = []

        # Phase 1: Graph analysis (process-wide)
        issues.extend(GraphAnalyzer(self._graph).get_issues())

        # Phase 2: Stage analysis (per-stage)
        for mutations in self._stage_mutations:
            issues.extend(StageAnalyzer(mutations).get_issues())

            # Phase 3: Gate analysis (per-gate within stage)
            for gate_def in mutations.gates:
                issues.extend(GateAnalyzer(gate_def, mutations.stage_id).get_issues())

        return issues
