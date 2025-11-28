"""
Consistency models for StageFlow process validation.

This module defines data structures and enums for process consistency checking,
including issue types and termination analysis.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from .enums import IssueSeverity


class ProcessIssueTypes(StrEnum):
    """Types of consistency issues that can be found in a process definition."""

    # Existing issue types
    MISSING_STAGE = "missing_stage"
    INVALID_TRANSITION = "invalid_transition"
    DEAD_END_STAGE = "dead_end_stage"
    UNREACHABLE_STAGE = "unreachable_stage"
    ORPHANED_STAGE = "orphaned_stage"
    CIRCULAR_DEPENDENCY = "circular_dependency"  # Deprecated - kept for backward compatibility
    LOGICAL_CONFLICT = "logical_conflict"
    MULTIPLE_GATES_SAME_TARGET = "multiple_gates_same_target"
    SELF_REFERENCING_GATE = "self_referencing_gate"

    # New cycle-related issue types
    INFINITE_CYCLE = "infinite_cycle"           # Cycle with no exit path to final stage
    UNCONTROLLED_CYCLE = "uncontrolled_cycle"   # Cycle without clear termination conditions
    CONTROLLED_CYCLE = "controlled_cycle"        # Well-controlled cycle (INFO level, optional)

    # Final stage validation
    FINAL_STAGE_HAS_GATES = "final_stage_has_gates"  # Final stage should not have outgoing gates

    # Schema transformation validation
    EMPTY_STAGE_TRANSFORMATION = "empty_stage_transformation"  # Gate doesn't change schema
    DUPLICATE_GATE_SCHEMAS = "duplicate_gate_schemas"  # Two gates produce identical schemas
    SCHEMA_PROPERTY_REGRESSION = "schema_property_regression"  # Gate loses properties


@dataclass(frozen=True)
class ConsistencyIssue:
    """Represents a consistency issue found in a process definition."""
    issue_type: ProcessIssueTypes
    description: str
    stages: list[str] = field(default_factory=list)
    severity: IssueSeverity = IssueSeverity.WARNING
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TerminationAnalysis:
    """Analysis result for cycle termination detection."""
    has_termination: bool
    termination_type: str
    description: str
    common_properties: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
