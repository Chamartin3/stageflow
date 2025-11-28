"""Analysis data models for StageFlow process validation.

This module defines the input data structures for process analyzers,
providing clear separation between data extraction and analysis logic.
"""

from dataclasses import dataclass

from .base import GateDefinition
from .schema import StageSchema

__all__ = [
    "ProcessGraph",
    "StageSchemaMutations",
]


@dataclass(frozen=True)
class ProcessGraph:
    """Graph topology for structural analysis.

    Contains minimal data needed for graph-based validation:
    - Reachability analysis
    - Cycle detection
    - Orphaned stage detection

    Attributes:
        edges: Tuple of (from_stage_id, to_stage_id) transitions
        initial_id: Starting stage identifier
        final_id: Terminal stage identifier
        stage_ids: All stage identifiers in the process
        stages_with_gates: Stage IDs that have outgoing gates
    """

    edges: tuple[tuple[str, str], ...]
    initial_id: str
    final_id: str
    stage_ids: frozenset[str]
    stages_with_gates: frozenset[str]

    def get_targets(self, stage_id: str) -> list[str]:
        """Get all target stages from a given stage."""
        return [to_id for from_id, to_id in self.edges if from_id == stage_id]

    def has_path(
        self, from_id: str, to_id: str, exclude: set[str] | None = None
    ) -> bool:
        """Check if path exists between stages (BFS).

        Args:
            from_id: Starting stage
            to_id: Target stage
            exclude: Stages to not traverse through (but from_id is always processed)
        """
        if from_id == to_id:
            return True

        exclude = exclude or set()
        visited: set[str] = set()
        queue = [from_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            # Allow starting node even if in exclude
            if current != from_id and current in exclude:
                continue
            visited.add(current)

            for target in self.get_targets(current):
                if target == to_id:
                    return True
                if target not in visited and target not in exclude:
                    queue.append(target)

        return False


@dataclass(frozen=True)
class StageSchemaMutations:
    """Schema transformations for a single stage.

    Contains all data needed for stage-level validation:
    - Schema transformation checks
    - Gate grouping analysis
    - Duplicate detection

    Attributes:
        stage_id: Stage identifier
        is_final: Whether this is the final stage
        initial_schema: Schema at stage entry (fields only)
        final_schemas: Schema per gate at stage exit
        gates: Gate definitions for this stage
        is_transition_target: Whether any gate targets this stage
    """

    stage_id: str
    is_final: bool
    initial_schema: StageSchema
    final_schemas: dict[str, StageSchema]
    gates: tuple[GateDefinition, ...]
    is_transition_target: bool
