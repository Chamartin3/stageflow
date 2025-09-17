"""Process schema validation and linting for StageFlow."""

from dataclasses import dataclass
from enum import Enum

from stageflow.core.process import Process


class LintSeverity(Enum):
    """Severity levels for lint messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class LintMessage:
    """Individual lint message."""

    severity: LintSeverity
    code: str
    message: str
    location: str
    suggestion: str = ""


@dataclass(frozen=True)
class LintResult:
    """Result of process linting."""

    process_name: str
    messages: list[LintMessage]
    errors: int
    warnings: int
    info: int

    @classmethod
    def from_messages(cls, process_name: str, messages: list[LintMessage]) -> "LintResult":
        """Create LintResult from list of messages."""
        errors = sum(1 for msg in messages if msg.severity == LintSeverity.ERROR)
        warnings = sum(1 for msg in messages if msg.severity == LintSeverity.WARNING)
        info = sum(1 for msg in messages if msg.severity == LintSeverity.INFO)

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


class ProcessLinter:
    """
    Comprehensive linter for StageFlow processes.

    Validates process structure, checks for common issues, and provides
    actionable suggestions for improvement.
    """

    def __init__(self):
        """Initialize linter with default rules."""
        self._rules = [
            self._check_stage_reachability,
            self._check_dead_end_stages,
            self._check_circular_dependencies,
            self._check_property_coverage,
            self._check_gate_logic,
            self._check_naming_conventions,
            self._check_schema_consistency,
        ]

    def lint_process(self, process: Process) -> LintResult:
        """
        Lint a process for structural and semantic issues.

        Args:
            process: Process to lint

        Returns:
            LintResult with findings and suggestions
        """
        messages = []

        # Run all linting rules
        for rule in self._rules:
            try:
                rule_messages = rule(process)
                messages.extend(rule_messages)
            except Exception as e:
                messages.append(
                    LintMessage(
                        severity=LintSeverity.ERROR,
                        code="LINT_ERROR",
                        message=f"Linting rule failed: {str(e)}",
                        location="process",
                    )
                )

        return LintResult.from_messages(process.name, messages)

    def _check_stage_reachability(self, process: Process) -> list[LintMessage]:
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
                        LintMessage(
                            severity=LintSeverity.WARNING,
                            code="UNREACHABLE_STAGE",
                            message=f"Stage '{stage_name}' may be unreachable from '{prev_stage_name}'",
                            location=f"stage.{stage_name}",
                            suggestion="Ensure stages share some common properties for progression",
                        )
                    )

        return messages

    def _check_dead_end_stages(self, process: Process) -> list[LintMessage]:
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
                    LintMessage(
                        severity=LintSeverity.WARNING,
                        code="DEAD_END_STAGE",
                        message=f"Stage '{stage.name}' has no property continuity to next stage",
                        location=f"stage.{stage.name}",
                        suggestion="Add gates that prepare properties needed for next stage",
                    )
                )

        return messages

    def _check_circular_dependencies(self, process: Process) -> list[LintMessage]:
        """Check for circular dependencies in stage flow."""
        messages = []

        # Simple check: ensure stage order doesn't repeat
        seen_stages = set()
        for stage_name in process.stage_order:
            if stage_name in seen_stages:
                messages.append(
                    LintMessage(
                        severity=LintSeverity.ERROR,
                        code="CIRCULAR_DEPENDENCY",
                        message=f"Stage '{stage_name}' appears multiple times in process order",
                        location=f"stage.{stage_name}",
                        suggestion="Remove duplicate stage references",
                    )
                )
            seen_stages.add(stage_name)

        return messages

    def _check_property_coverage(self, process: Process) -> list[LintMessage]:
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
                    LintMessage(
                        severity=LintSeverity.INFO,
                        code="SINGLE_USE_PROPERTY",
                        message=f"Property '{prop}' only used by stage '{using_stages[0]}'",
                        location=f"property.{prop}",
                        suggestion="Consider if property should be used by other stages",
                    )
                )

        return messages

    def _check_gate_logic(self, process: Process) -> list[LintMessage]:
        """Check gate logic for common issues."""
        messages = []

        for stage in process.stages:
            for gate in stage.gates:
                # Check for gates with only one lock using AND logic
                if len(gate.locks) == 1 and gate.logic.value == "and":
                    messages.append(
                        LintMessage(
                            severity=LintSeverity.INFO,
                            code="UNNECESSARY_AND_LOGIC",
                            message=f"Gate '{gate.name}' has only one lock but uses AND logic",
                            location=f"stage.{stage.name}.gate.{gate.name}",
                            suggestion="Consider simplifying gate logic for single locks",
                        )
                    )

                # Check for gates with no locks
                if len(gate.locks) == 0:
                    messages.append(
                        LintMessage(
                            severity=LintSeverity.ERROR,
                            code="EMPTY_GATE",
                            message=f"Gate '{gate.name}' contains no locks",
                            location=f"stage.{stage.name}.gate.{gate.name}",
                            suggestion="Add locks to gate or remove empty gate",
                        )
                    )

        return messages

    def _check_naming_conventions(self, process: Process) -> list[LintMessage]:
        """Check naming conventions for consistency."""
        messages = []

        # Check process name
        if not process.name or not process.name.strip():
            messages.append(
                LintMessage(
                    severity=LintSeverity.ERROR,
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
                    LintMessage(
                        severity=LintSeverity.ERROR,
                        code="EMPTY_STAGE_NAME",
                        message="Stage has empty or missing name",
                        location="stage",
                        suggestion="Provide descriptive stage names",
                    )
                )

            # Check for stage names with spaces (may cause issues)
            if " " in stage.name:
                messages.append(
                    LintMessage(
                        severity=LintSeverity.WARNING,
                        code="STAGE_NAME_SPACES",
                        message=f"Stage name '{stage.name}' contains spaces",
                        location=f"stage.{stage.name}",
                        suggestion="Consider using underscores or camelCase instead of spaces",
                    )
                )

        return messages

    def _check_schema_consistency(self, process: Process) -> list[LintMessage]:
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
                    LintMessage(
                        severity=LintSeverity.INFO,
                        code="DUPLICATE_SCHEMA_NAME",
                        message=f"Schema '{schema_name}' used by multiple stages: {', '.join(stage_names)}",
                        location=f"schema.{schema_name}",
                        suggestion="Verify schemas are truly identical or use unique names",
                    )
                )

        return messages
