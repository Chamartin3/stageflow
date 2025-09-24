"""Process schema validation for StageFlow."""

from dataclasses import dataclass
from enum import Enum

# Lazy import to avoid circular dependency
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class ValidationSeverity(Enum):
    """Severity levels for validation messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationMessage:
    """Individual validation message."""

    severity: ValidationSeverity
    code: str
    message: str
    location: str
    suggestion: str = ""


@dataclass(frozen=True)
class ProcessValidationResult:
    """Result of process validation."""

    process_name: str
    messages: list[ValidationMessage]
    errors: int
    warnings: int
    info: int

    @classmethod
    def from_messages(cls, process_name: str, messages: list[ValidationMessage]) -> "ProcessValidationResult":
        """Create ProcessValidationResult from list of messages."""
        errors = sum(1 for msg in messages if msg.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for msg in messages if msg.severity == ValidationSeverity.WARNING)
        info = sum(1 for msg in messages if msg.severity == ValidationSeverity.INFO)

        return cls(
            process_name=process_name,
            messages=messages,
            errors=errors,
            warnings=warnings,
            info=info,
        )

    @property
    def has_errors(self) -> bool:
        """Check if result contains errors."""
        return self.errors > 0

    @property
    def is_clean(self) -> bool:
        """Check if result has no issues."""
        return len(self.messages) == 0


class ProcessValidator:
    """
    Comprehensive validator for StageFlow processes.

    Validates process structure, checks for common issues, and provides
    actionable suggestions for improvement.
    """

    def __init__(self):
        """Initialize validator with default rules."""
        self._rules = [
            self._check_stage_reachability,
            self._check_dead_end_stages,
            self._check_circular_dependencies,
            self._check_property_coverage,
            self._check_gate_logic,
            self._check_naming_conventions,
            self._check_schema_consistency,
            self._check_stage_ordering,
            self._check_transition_validity,
        ]

    def validate_process(self, process: Any) -> ProcessValidationResult:
        """
        Validate a process for structural and semantic issues.

        Args:
            process: Any to validate

        Returns:
            ProcessValidationResult with findings and suggestions
        """
        messages = []

        # Run all validation rules
        for rule in self._rules:
            try:
                rule_messages = rule(process)
                messages.extend(rule_messages)
            except Exception as e:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="VALIDATION_ERROR",
                        message=f"Validation rule failed: {str(e)}",
                        location="process",
                    )
                )

        return ProcessValidationResult.from_messages(process.name, messages)

    def _check_stage_reachability(self, process: Any) -> list[ValidationMessage]:
        """Check if all stages are reachable."""
        messages = []

        if len(process.stages) <= 1:
            return messages

        # Check if stages can be reached in order
        for i, stage_name in enumerate(process.stage_order[1:], 1):
            prev_stage_name = process.stage_order[i - 1]
            prev_stage = process.get_stage(prev_stage_name)
            current_stage = process.get_stage(stage_name)

            if prev_stage and current_stage:
                prev_props = prev_stage.get_required_properties()
                curr_props = current_stage.get_required_properties()

                # Check for property continuity
                if prev_props.isdisjoint(curr_props):
                    messages.append(
                        ValidationMessage(
                            severity=ValidationSeverity.WARNING,
                            code="UNREACHABLE_STAGE",
                            message=f"Stage '{stage_name}' may be unreachable from '{prev_stage_name}'",
                            location=f"stage.{stage_name}",
                            suggestion="Ensure stages share some common properties for progression",
                        )
                    )

        return messages

    def _check_dead_end_stages(self, process: Any) -> list[ValidationMessage]:
        """Check for stages that cannot advance."""
        messages = []

        # Exclude the last stage (which is expected to be terminal)
        for stage in process.stages[:-1]:
            next_stage = process._get_next_stage(stage.name)
            if not next_stage:
                continue

            stage_props = stage.get_required_properties()
            next_props = next_stage.get_required_properties()

            # Check if there's any way to progress
            if stage_props.isdisjoint(next_props):
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="DEAD_END_STAGE",
                        message=f"Stage '{stage.name}' has no property continuity to next stage",
                        location=f"stage.{stage.name}",
                        suggestion="Add gates that prepare properties needed for next stage",
                    )
                )

        return messages

    def _check_circular_dependencies(self, process: Any) -> list[ValidationMessage]:
        """Check for circular dependencies in stage flow."""
        messages = []

        # Simple check: ensure stage order doesn't repeat
        seen_stages = set()
        for stage_name in process.stage_order:
            if stage_name in seen_stages:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="CIRCULAR_DEPENDENCY",
                        message=f"Stage '{stage_name}' appears multiple times in process order",
                        location=f"stage.{stage_name}",
                        suggestion="Remove duplicate stage references",
                    )
                )
            seen_stages.add(stage_name)

        return messages

    def _check_property_coverage(self, process: Any) -> list[ValidationMessage]:
        """Check for unused or missing property coverage."""
        messages = []

        all_properties = set()
        stage_properties = {}

        # Collect all properties used by stages
        for stage in process.stages:
            stage_props = stage.get_required_properties()
            stage_properties[stage.name] = stage_props
            all_properties.update(stage_props)

        # Check for properties used by only one stage
        for prop in all_properties:
            using_stages = [name for name, props in stage_properties.items() if prop in props]
            if len(using_stages) == 1:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        code="SINGLE_USE_PROPERTY",
                        message=f"Property '{prop}' only used by stage '{using_stages[0]}'",
                        location=f"property.{prop}",
                        suggestion="Consider if property should be used by other stages",
                    )
                )

        return messages

    def _check_gate_logic(self, process: Any) -> list[ValidationMessage]:
        """Check gate structure for common issues."""
        messages = []

        for stage in process.stages:
            for gate in stage.gates:
                # Check for gates with no locks
                if len(gate.locks) == 0:
                    messages.append(
                        ValidationMessage(
                            severity=ValidationSeverity.ERROR,
                            code="EMPTY_GATE",
                            message=f"Gate '{gate.name}' contains no locks",
                            location=f"stage.{stage.name}.gate.{gate.name}",
                            suggestion="Add locks to gate or remove empty gate",
                        )
                    )

        return messages

    def _check_naming_conventions(self, process: Any) -> list[ValidationMessage]:
        """Check naming conventions for consistency."""
        messages = []

        # Check process name
        if not process.name or not process.name.strip():
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="EMPTY_PROCESS_NAME",
                    message="Process has empty or missing name",
                    location="process",
                    suggestion="Provide a descriptive process name",
                )
            )

        # Check stage names
        for stage in process.stages:
            if not stage.name or not stage.name.strip():
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="EMPTY_STAGE_NAME",
                        message="Stage has empty or missing name",
                        location="stage",
                        suggestion="Provide descriptive stage names",
                    )
                )

            # Check for stage names with spaces (may cause issues)
            if " " in stage.name:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="STAGE_NAME_SPACES",
                        message=f"Stage name '{stage.name}' contains spaces",
                        location=f"stage.{stage.name}",
                        suggestion="Consider using underscores or camelCase instead of spaces",
                    )
                )

        return messages

    def _check_schema_consistency(self, process: Any) -> list[ValidationMessage]:
        """Check schema definitions for consistency."""
        messages = []

        schemas_with_same_name = {}

        for stage in process.stages:
            if stage.schema:
                schema_name = stage.schema.name
                if schema_name in schemas_with_same_name:
                    schemas_with_same_name[schema_name].append(stage.name)
                else:
                    schemas_with_same_name[schema_name] = [stage.name]

        # Check for schemas with same name but potentially different definitions
        for schema_name, stage_names in schemas_with_same_name.items():
            if len(stage_names) > 1:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        code="DUPLICATE_SCHEMA_NAME",
                        message=f"Schema '{schema_name}' used by multiple stages: {', '.join(stage_names)}",
                        location=f"schema.{schema_name}",
                        suggestion="Verify schemas are truly identical or use unique names",
                    )
                )

        return messages

    def _check_stage_ordering(self, process: Any) -> list[ValidationMessage]:
        """Check stage ordering for logical consistency."""
        messages = []

        # Check if initial_stage exists and is in the process
        if process.initial_stage:
            if not process.get_stage(process.initial_stage):
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_INITIAL_STAGE",
                        message=f"Initial stage '{process.initial_stage}' not found in process",
                        location="process.initial_stage",
                        suggestion="Set initial_stage to an existing stage name or remove it",
                    )
                )
            elif process.initial_stage != process.stage_order[0]:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="INITIAL_STAGE_NOT_FIRST",
                        message=f"Initial stage '{process.initial_stage}' is not first in stage order",
                        location="process.initial_stage",
                        suggestion="Consider reordering stages or updating initial_stage",
                    )
                )

        # Check if final_stage exists and is in the process
        if process.final_stage:
            if not process.get_stage(process.final_stage):
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_FINAL_STAGE",
                        message=f"Final stage '{process.final_stage}' not found in process",
                        location="process.final_stage",
                        suggestion="Set final_stage to an existing stage name or remove it",
                    )
                )
            elif process.final_stage != process.stage_order[-1]:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="FINAL_STAGE_NOT_LAST",
                        message=f"Final stage '{process.final_stage}' is not last in stage order",
                        location="process.final_stage",
                        suggestion="Consider reordering stages or updating final_stage",
                    )
                )

        # Check for single-stage processes
        if len(process.stages) == 1:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.INFO,
                    code="SINGLE_STAGE_PROCESS",
                    message="Process contains only one stage",
                    location="process.stages",
                    suggestion="Consider if this process really needs multi-stage validation",
                )
            )

        return messages

    def _check_transition_validity(self, process: Any) -> list[ValidationMessage]:
        """Check validity of stage transitions."""
        messages = []

        if len(process.stages) <= 1:
            return messages

        # Check if stage skipping is disabled but transitions would require it
        if not process.allow_stage_skipping:
            for i, stage_name in enumerate(process.stage_order[:-1]):
                next_stage_name = process.stage_order[i + 1]
                current_stage = process.get_stage(stage_name)
                next_stage = process.get_stage(next_stage_name)

                if current_stage and next_stage:
                    # Check if there's a logical progression path
                    current_props = current_stage.get_required_properties()
                    next_props = next_stage.get_required_properties()

                    # If no property overlap, might be difficult to progress
                    if current_props.isdisjoint(next_props):
                        messages.append(
                            ValidationMessage(
                                severity=ValidationSeverity.WARNING,
                                code="DIFFICULT_TRANSITION",
                                message=f"No property overlap between '{stage_name}' and '{next_stage_name}'",
                                location=f"stage.{stage_name}",
                                suggestion="Ensure stages have logical progression or enable stage skipping",
                            )
                        )

        # Check for stages that can never be reached due to strict ordering
        if not process.allow_stage_skipping and len(process.stage_order) > 2:
            for i, stage_name in enumerate(process.stage_order[1:-1], 1):
                prev_stage_name = process.stage_order[i - 1]
                prev_stage = process.get_stage(prev_stage_name)
                current_stage = process.get_stage(stage_name)

                if prev_stage and current_stage:
                    # Check if progression from previous stage is possible
                    if not prev_stage.gates:
                        messages.append(
                            ValidationMessage(
                                severity=ValidationSeverity.WARNING,
                                code="UNGATED_INTERMEDIATE_STAGE",
                                message=f"Stage '{prev_stage_name}' has no gates but is not final",
                                location=f"stage.{prev_stage_name}",
                                suggestion="Add gates to control progression or reconsider stage order",
                            )
                        )

        return messages
