"""Process formatting utilities for CLI output.

This module provides type-safe formatting of Process objects
for display in CLI commands. All methods return strings ready for printing rather
than printing directly.
"""

from typing import TYPE_CHECKING, NotRequired, TypedDict

from stageflow.models import (
    ActionDefinition,
    ExpectedObjectSchmema,
    ProcessLoadResult,
)

if TYPE_CHECKING:
    from stageflow.models import RegressionDetails
from stageflow.models.base import ProcessElementEvaluationResult
from stageflow.process import Process


class ConsistencyIssue(TypedDict):
    """Type definition for consistency issue."""

    type: str
    description: str


class StageInfo(TypedDict):
    """Type definition for stage information."""

    id: str
    name: str
    description: str
    expected_properties: list[str]
    gates: int
    target_stages: list[str]
    is_final: bool


class ProcessDescription(TypedDict):
    """Type definition for process description."""

    name: str
    description: str
    initial_stage: str | None
    final_stage: str | None
    stages: list[StageInfo]
    valid: bool
    consistency_issues: list[ConsistencyIssue]


class ActionInfo(TypedDict):
    """Type definition for action information in JSON output."""

    description: str
    type: str


class GateResultInfo(TypedDict):
    """Type definition for gate result information in JSON output."""

    passed: bool
    success_rate: float
    failed_locks: int
    passed_locks: int


class EvaluationData(TypedDict):
    """Type definition for evaluation data in JSON output."""

    stage: str
    status: str
    regression: bool
    actions: list[ActionInfo]
    gate_results: dict[str, GateResultInfo]
    regression_details: NotRequired["RegressionDetails"]
    configured_actions: NotRequired[list[ActionDefinition]]
    validation_messages: NotRequired[list[str]]


class EvaluationJsonResult(TypedDict):
    """Type definition for complete evaluation JSON result."""

    process: ProcessDescription
    evaluation: EvaluationData


class ProcessFormatter:
    """Type-safe formatter for Process objects.

    This class provides methods to format process information into strings
    ready for CLI output. All methods return strings and do not print directly.
    """

    @staticmethod
    def build_description(process: Process) -> ProcessDescription:
        """Build a structured process description dictionary.

        Args:
            process: Process instance

        Returns:
            ProcessDescription dictionary with all process information
        """
        return ProcessFormatter._build_description_from_process(process)

    @staticmethod
    def _build_description_from_process(process: Process) -> ProcessDescription:
        """Build description from Process instance.

        Args:
            process: Process instance

        Returns:
            ProcessDescription dictionary
        """
        # Determine validity based on consistency checker
        consistency_valid = (
            process.checker.valid
            if hasattr(process, "checker") and process.checker
            else True
        )

        # Collect consistency issues
        consistency_issues: list[ConsistencyIssue] = []
        if (
            hasattr(process, "checker")
            and process.checker
            and hasattr(process.checker, "issues")
        ):
            consistency_issues = [
                {"type": str(issue.issue_type), "description": issue.description}
                for issue in process.checker.issues
            ]

        # Collect stages in traversal order
        visited: set[str] = set()
        stage_order: list[str] = []

        def collect_stages(stage_id: str | None) -> None:
            """Recursively collect stages in traversal order."""
            if stage_id is None or stage_id in visited:
                return
            visited.add(stage_id)
            stage_order.append(stage_id)

            stage = process.get_stage(stage_id)
            if stage:
                for gate in stage.gates:
                    if hasattr(gate, "target_stage") and gate.target_stage:
                        collect_stages(gate.target_stage)

        # Start from initial stage
        if process.initial_stage:
            collect_stages(process.initial_stage._id)

        # Add any unvisited stages
        for stage in process.stages:
            if stage._id not in visited:
                stage_order.append(stage._id)

        # Build stage information
        stages: list[StageInfo] = []
        for stage_id in stage_order:
            stage = process.get_stage(stage_id)
            if stage:
                target_stages: list[str] = []
                for gate in stage.gates:
                    if hasattr(gate, "target_stage") and gate.target_stage:
                        if gate.target_stage not in target_stages:
                            target_stages.append(gate.target_stage)

                stage_info: StageInfo = {
                    "id": stage._id,
                    "name": stage.name,
                    "description": getattr(stage, "description", ""),
                    "expected_properties": list(stage._properties.keys())
                    if stage._properties
                    else [],
                    "gates": len(stage.gates),
                    "target_stages": target_stages,
                    "is_final": stage.is_final,
                }
                stages.append(stage_info)

        return ProcessDescription(
            name=process.name,
            description=getattr(process, "description", ""),
            initial_stage=process.initial_stage._id if process.initial_stage else None,
            final_stage=process.final_stage._id if process.final_stage else None,
            stages=stages,
            valid=consistency_valid,
            consistency_issues=consistency_issues,
        )

    @staticmethod
    def format_header(desc: ProcessDescription) -> str:
        """Format process header with validation status.

        Args:
            desc: ProcessDescription dictionary

        Returns:
            Formatted header string with rich markup
        """
        status_icon = "✅" if desc["valid"] else "❌"
        status_text = "Valid" if desc["valid"] else "Invalid"

        lines = [
            f"\n{status_icon} [bold]Process: {desc['name']}[/bold] ({status_text})"
        ]

        if desc["description"]:
            lines.append(f"   Description: {desc['description']}")

        lines.append(f"   Initial Stage: {desc['initial_stage']}")
        lines.append(f"   Final Stage: {desc['final_stage']}")
        lines.append(f"   Total Stages: {len(desc['stages'])}\n")

        return "\n".join(lines)

    @staticmethod
    def format_stages(desc: ProcessDescription) -> str:
        """Format stage listing with hierarchy.

        Args:
            desc: ProcessDescription dictionary

        Returns:
            Formatted stage list string with rich markup
        """
        if not desc["stages"]:
            return ""

        lines = ["[bold]Stages:[/bold]"]

        for i, stage in enumerate(desc["stages"]):
            is_last = i == len(desc["stages"]) - 1
            prefix = "└─" if is_last else "├─"
            final_marker = " (final)" if stage["is_final"] else ""

            targets_text = ""
            if stage["target_stages"]:
                targets_text = f" → {', '.join(stage['target_stages'])}"

            lines.append(f"{prefix} {stage['name']}{targets_text}{final_marker}")

            if stage.get("description"):
                lines.append(f"   Description: {stage['description']}")

            if stage["expected_properties"]:
                props = ", ".join(stage["expected_properties"])
                lines.append(f"   Expected properties: {props}")

        return "\n".join(lines)

    @staticmethod
    def format_consistency_issues(desc: ProcessDescription) -> str:
        """Format consistency issues section.

        Args:
            desc: ProcessDescription dictionary

        Returns:
            Formatted consistency issues string with rich markup, empty if no issues
        """
        if not desc["consistency_issues"]:
            return ""

        lines = [
            "",
            "[red]❌ Consistency Issues:[/red]",
        ]

        for issue in desc["consistency_issues"]:
            lines.append(f"   • {issue['description']}")

        lines.extend(
            [
                "",
                "⚠️  This process is not valid for execution due to the above consistency issues.",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def format_process_description(desc: ProcessDescription) -> str:
        """Format complete process description.

        Args:
            desc: ProcessDescription dictionary

        Returns:
            Complete formatted process description string
        """
        sections = [
            ProcessFormatter.format_header(desc),
            ProcessFormatter.format_stages(desc),
            ProcessFormatter.format_consistency_issues(desc),
        ]

        # Filter out empty sections
        return "\n".join(section for section in sections if section)


class EvaluationFormatter:
    """Type-safe formatter for evaluation results.

    This class provides methods to format ProcessElementEvaluationResult objects
    into strings ready for CLI output. All methods return strings and do not print directly.
    """

    @staticmethod
    def format_expected_actions(
        actions_def: list[ActionDefinition], indent: str = "   "
    ) -> str:
        """Format enhanced expected_actions with name and instructions.

        Args:
            actions_def: List of ActionDefinition dictionaries
            indent: String prefix for indentation

        Returns:
            Formatted expected actions string with rich markup, empty if no actions
        """
        if not actions_def:
            return ""

        lines = [f"\n{indent}📋 [bold]Expected Actions:[/bold]"]

        for action in actions_def:
            name = action.get("name")
            description = action.get("description", "No description")
            instructions = action.get("instructions", [])
            related_properties = action.get("related_properties", [])

            # Display action name and description
            if name:
                lines.append(f"\n{indent}  ▸ [cyan]{name}[/cyan]")
                lines.append(f"{indent}    {description}")
            else:
                lines.append(f"\n{indent}  ▸ {description}")

            # Display instructions if available
            if instructions:
                lines.append(f"{indent}    [dim]Guidelines:[/dim]")
                for i, instruction in enumerate(instructions, 1):
                    lines.append(f"{indent}      {i}. {instruction}")

            # Display related properties if available
            if related_properties:
                props_str = ", ".join(related_properties)
                lines.append(f"{indent}    [dim]Related properties:[/dim] {props_str}")

        return "\n".join(lines)

    @staticmethod
    def format_status_header(result: ProcessElementEvaluationResult) -> str:
        """Format evaluation result status header.

        Args:
            result: Evaluation result from Process.evaluate()

        Returns:
            Formatted header string with status emoji and basic info
        """
        stage_result = result["stage_result"]
        status = stage_result.status
        current_stage = result["stage"]

        status_emoji_map = {
            "ready": "✅",
            "blocked": "⚠️",
            "incomplete": "❌",
        }
        status_emoji = status_emoji_map.get(status, "❓")

        lines = [
            f"\n{status_emoji} [bold]Evaluation Result[/bold]",
            f"   Current Stage: {current_stage}",
            f"   Status: {status}",
        ]

        return "\n".join(lines)

    @staticmethod
    def format_transitions(result: ProcessElementEvaluationResult) -> str:
        """Format possible transitions section.

        Args:
            result: Evaluation result from Process.evaluate()

        Returns:
            Formatted transitions string with rich markup, empty if no actions
        """
        stage_result = result["stage_result"]

        # Combine configured actions and validation messages
        all_messages = []
        all_messages.extend(stage_result.validation_messages)
        for action_def in stage_result.configured_actions:
            all_messages.append(action_def["description"])

        if not all_messages:
            return ""

        lines = ["   [yellow]Possible Transitions:[/yellow]"]

        # Group messages for better readability
        for i, message in enumerate(all_messages):
            description = message

            # Check if this is a gate header (starts with "To transition via")
            if description.startswith("To transition via"):
                # Add spacing before new transition (except first one)
                if i > 0:
                    lines.append("")
                # Print the transition header with styling
                lines.append(f"     [cyan]•[/cyan] [bold]{description}[/bold]")
            else:
                # This is a required action under the current gate
                lines.append(f"       {description}")

        return "\n".join(lines)

    @staticmethod
    def format_passed_gates(result: ProcessElementEvaluationResult) -> str:
        """Format passed gates section for ready status.

        Args:
            result: Evaluation result from Process.evaluate()

        Returns:
            Formatted passed gates string, empty if not ready or no gates passed
        """
        stage_result = result["stage_result"]
        status = stage_result.status

        if status != "ready":
            return ""

        passed_gates = [
            gate_name
            for gate_name, gate_result in stage_result.results.items()
            if gate_result.success
        ]

        if not passed_gates:
            return ""

        gates_str = ", ".join(passed_gates)
        return f"   [green]Passed Gate(s):[/green] {gates_str}"

    @staticmethod
    def format_evaluation_result(result: ProcessElementEvaluationResult) -> str:
        """Format complete human-readable evaluation result.

        Args:
            result: Evaluation result from Process.evaluate()

        Returns:
            Formatted evaluation result string with rich markup
        """
        sections = [
            EvaluationFormatter.format_status_header(result),
            EvaluationFormatter.format_transitions(result),
            EvaluationFormatter.format_passed_gates(result),
        ]

        # Add configured actions for blocked status
        stage_result = result["stage_result"]
        configured_actions = stage_result.configured_actions
        if configured_actions and str(stage_result.status) == "blocked":
            sections.append(
                EvaluationFormatter.format_expected_actions(configured_actions)
            )

        # Add regression information
        regression_details = result.get("regression_details")
        if regression_details and regression_details["detected"]:
            sections.append(
                EvaluationFormatter.format_regression_details(regression_details)
            )

        # Add validation messages
        validation_messages = stage_result.validation_messages
        if validation_messages:
            sections.append(
                EvaluationFormatter.format_validation_messages(validation_messages)
            )

        # Filter out empty sections
        return "\n".join(section for section in sections if section)

    @staticmethod
    def format_regression_details(details: "RegressionDetails") -> str:
        """Format regression details for display."""
        lines = [f"\n⚠️  [yellow]Regression Detected[/yellow] (policy: {details['policy']})"]
        lines.append(f"   Failed Stages: {', '.join(details['failed_stages'])}")

        for stage_id in details["failed_stages"]:
            status = details["failed_statuses"].get(stage_id, "unknown")
            lines.append(f"   • {stage_id}: {status}")

            # Show missing properties if available
            if "missing_properties" in details:
                props = details.get("missing_properties", {}).get(stage_id, [])
                if props:
                    lines.append(f"     Missing: {', '.join(props)}")

            # Show failed gates if available
            if "failed_gates" in details:
                gates = details.get("failed_gates", {}).get(stage_id, [])
                if gates:
                    lines.append(f"     Failed gates: {', '.join(gates)}")

        return "\n".join(lines)

    @staticmethod
    def format_validation_messages(messages: list[str]) -> str:
        """Format validation messages for display."""
        if not messages:
            return ""

        lines = ["\n📝 [bold]Validation Messages:[/bold]"]
        for msg in messages:
            lines.append(f"   • {msg}")

        return "\n".join(lines)

    @staticmethod
    def format_json_result(
        process: Process,
        evaluation_result: ProcessElementEvaluationResult,
    ) -> EvaluationJsonResult:
        """Format evaluation result as JSON-serializable dictionary.

        This method uses ProcessFormatter.build_description() for the process
        serialization to ensure all data is JSON-serializable.

        Args:
            process: Process instance
            evaluation_result: Evaluation result from Process.evaluate()

        Returns:
            EvaluationJsonResult with process and evaluation data
        """
        # Use ProcessFormatter for JSON-safe process serialization
        process_description = ProcessFormatter.build_description(process)

        stage_result = evaluation_result["stage_result"]

        # Format actions (backward compatibility - combine configured and generated)
        actions: list[ActionInfo] = []

        # Add configured actions
        for action_def in stage_result.configured_actions:
            actions.append(ActionInfo(
                description=action_def["description"],
                type="execute"  # Configured actions are execute type
            ))

        # Add validation messages as generated actions
        for msg in stage_result.validation_messages:
            actions.append(ActionInfo(
                description=msg,
                type="execute"  # Generated actions are execute type
            ))

        # Format gate results
        gate_results: dict[str, GateResultInfo] = {
            gate_name: GateResultInfo(
                passed=gate_result.success,
                success_rate=gate_result.success_rate,
                failed_locks=len(gate_result.failed),
                passed_locks=len(gate_result.passed),
            )
            for gate_name, gate_result in stage_result.results.items()
        }

        # Format evaluation section
        evaluation_data = EvaluationData(
            stage=evaluation_result["stage"],
            status=stage_result.status,
            regression=evaluation_result["regression_details"]["detected"],
            actions=actions,
            gate_results=gate_results,
            regression_details=evaluation_result.get("regression_details"),
            configured_actions=stage_result.configured_actions,
            validation_messages=stage_result.validation_messages,
        )

        return EvaluationJsonResult(
            process=process_description, evaluation=evaluation_data
        )

    @staticmethod
    def format_schema_hint(
        schema: ExpectedObjectSchmema, stage_id: str, show_cumulative: bool = False
    ) -> str:
        """Format schema hint for expected properties.

        Args:
            schema: Expected object schema
            stage_id: Stage identifier
            show_cumulative: Whether showing cumulative schema

        Returns:
            Formatted schema hint string
        """
        if not schema:
            return ""

        schema_type = "cumulative" if show_cumulative else "current stage"
        lines = [f"\n[bold]Expected Properties ({schema_type}):[/bold]"]

        def flatten_schema(schema_dict: dict, prefix: str = "") -> list[str]:
            """Recursively flatten nested schema structure."""
            result_lines = []
            for key, value in schema_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    if "type" in value or "default" in value:
                        # This is a property definition
                        type_info = value.get("type", "any")
                        default_info = value.get("default")
                        prop_line = f"  • {full_key}: {type_info}"
                        if default_info is not None:
                            prop_line += f" (default: {default_info})"
                        result_lines.append(prop_line)
                    else:
                        # This is a nested structure - recurse
                        result_lines.extend(flatten_schema(value, full_key))
            return result_lines

        lines.extend(flatten_schema(schema))
        return "\n".join(lines) if len(lines) > 1 else ""


class LoadResultFormatter:
    """Formatter for ProcessLoadResult objects."""

    @staticmethod
    def format_load_result(result: ProcessLoadResult, verbose: bool = False) -> str:
        """Format a ProcessLoadResult for display.

        Args:
            result: ProcessLoadResult to format
            verbose: Whether to show detailed information

        Returns:
            Formatted string for display
        """
        if result.has_errors:
            lines = [
                f"[red]✗ Failed to load process from: {result.source}[/red]",
                f"[red]  Status: {result.status.value}[/red]",
                f"[red]  Errors: {result.error_count}[/red]",
                "",
                "[bold red]Errors:[/bold red]",
            ]

            for i, error in enumerate(result.errors, 1):
                lines.append(f"  {i}. {error.message}")
                if verbose and error.context:
                    for key, value in error.context.items():
                        lines.append(f"     {key}: {value}")

            return "\n".join(lines)
        else:
            if result.has_warnings:
                lines = [
                    f"[yellow]⚠ Process loaded with warnings from: {result.source}[/yellow]",
                    "",
                    "[bold yellow]Warnings:[/bold yellow]",
                ]
                for i, warning in enumerate(result.warnings, 1):
                    lines.append(f"  {i}. {warning.message}")
                return "\n".join(lines)
            else:
                return f"[green]✓ Process loaded successfully from: {result.source}[/green]"
