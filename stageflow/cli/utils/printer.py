"""CLI Printer for consistent output formatting."""

from rich.console import Console

from stageflow.cli.utils.format import (
    EvaluationFormatter,
    LoadResultFormatter,
    ProcessFormatter,
)
from stageflow.models import ProcessLoadResult
from stageflow.models.base import ProcessElementEvaluationResult
from stageflow.process import Process


class CliPrinter:
    """Centralized printer for CLI output.

    This class handles all printing operations for the CLI, ensuring consistent
    formatting across commands and proper handling of verbose/JSON modes.
    """

    def __init__(
        self, console: Console, verbose: bool = False, json_mode: bool = False
    ):
        """Initialize printer with console and mode settings.

        Args:
            console: Rich console for output
            verbose: Whether to show detailed output
            json_mode: Whether to output in JSON format (can be set later)
        """
        self.console = console
        self.verbose = verbose
        self.json_mode = json_mode

    def print_load_result(
        self, result: ProcessLoadResult, json_mode: bool | None = None
    ) -> None:
        """Print process load result with errors or warnings.

        Handles all conditional logic for displaying load results:
        - In JSON mode: outputs result.to_dict()
        - In normal mode: formats with colors and details
        - Respects verbose mode for additional context

        Args:
            result: ProcessLoadResult from process loading
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        if json_mode:
            # In JSON mode, output the result as a dictionary
            self.console.print_json(data=result.to_dict())
        else:
            # In normal mode, use formatted output
            formatted = LoadResultFormatter.format_load_result(result, self.verbose)
            if formatted:
                self.console.print(formatted)

    def print_process_description(self, process: Process) -> None:
        """Print human-readable process description.

        Args:
            process: Process instance
        """
        desc = ProcessFormatter.build_description(process)
        formatted = ProcessFormatter.format_process_description(desc)
        self.console.print(formatted)

    def print_process_details(
        self,
        process: Process,
        source: str,
        source_type_value: str,
        load_result: ProcessLoadResult | None = None,
        json_mode: bool | None = None,
    ) -> None:
        """Print complete process details with load information.

        Handles all conditional logic for displaying process details:
        - In JSON mode: outputs full process info with load status
        - In normal mode: formats with colors and structure
        - Includes load warnings if present

        Args:
            process: Process instance
            source: Source identifier (file path or registry name)
            source_type_value: Source type as string (e.g., "file", "registry")
            load_result: Optional load result for additional metadata
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        # Build description using formatter
        description = ProcessFormatter.build_description(process)

        if json_mode:
            # In JSON mode, create comprehensive output
            json_data = dict(description)
            json_data["source"] = source
            json_data["source_type"] = source_type_value
            json_data["is_valid"] = process.is_valid

            # Set status based on validity
            if process.is_valid:
                json_data["status"] = "success"
            else:
                json_data["status"] = "consistency_error"

            # Include consistency issues from process
            json_data["consistency_issues"] = [
                {
                    "issue_type": str(i.issue_type),
                    "description": i.description,
                    "stages": i.stages,
                    "blocking": i.issue_type in process.BLOCKING_ISSUE_TYPES,
                }
                for i in process.issues
            ]

            if load_result:
                json_data["load_status"] = load_result.status.value
                json_data["warnings"] = [w.to_dict() for w in load_result.warnings]

            self.console.print_json(data=json_data)
        else:
            # In normal mode, use formatted output
            formatted = ProcessFormatter.format_process_description(description)
            self.console.print(formatted)

    def print_evaluation_result(
        self,
        process: Process,
        result: ProcessElementEvaluationResult,
        json_mode: bool | None = None,
    ) -> None:
        """Print evaluation result with mode detection.

        Handles all conditional logic for displaying evaluation results:
        - In JSON mode: outputs comprehensive evaluation data
        - In normal mode: formats with colors and structure

        Args:
            process: Process instance
            result: Evaluation result from Process.evaluate()
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        if json_mode:
            # In JSON mode, create comprehensive output
            json_result = EvaluationFormatter.format_json_result(process, result)
            self.console.print_json(data=json_result)
        else:
            # In normal mode, use formatted output
            formatted = EvaluationFormatter.format_evaluation_result(result)
            self.console.print(formatted)

    def show_progress(self, message: str) -> None:
        """Show progress message if verbose mode is enabled.

        Args:
            message: Progress message to show
        """
        if self.verbose:
            self.console.print(f"🔄 {message}")

    def show_success(self, message: str) -> None:
        """Show success message with green checkmark.

        Args:
            message: Success message to show
        """
        self.console.print(f"✅ {message}")

    def print_json(self, data: dict) -> None:
        """Print data as JSON.

        Args:
            data: Dictionary to print as JSON
        """
        self.console.print_json(data=data)

    def print(self, message: str, **kwargs) -> None:
        """Print message to console.

        Args:
            message: Message to print
            **kwargs: Additional arguments for rich.console.print
        """
        self.console.print(message, **kwargs)

    def print_error(self, message: str) -> None:
        """Print error message with red formatting.

        Args:
            message: Error message to print
        """
        self.console.print(f"[red]❌ Error:[/red] {message}")

    def print_consistency_issues(self, process: Process) -> None:
        """Print process consistency issues.

        Args:
            process: Process with consistency issues
        """
        blocking_issues = [
            i for i in process.issues
            if i.issue_type in process.BLOCKING_ISSUE_TYPES
        ]
        warning_issues = [
            i for i in process.issues
            if i.issue_type not in process.BLOCKING_ISSUE_TYPES
        ]

        self.console.print(f"[red]❌ Process has {len(blocking_issues)} blocking issue(s)[/red]")

        for issue in blocking_issues:
            self.console.print(f"  [red]• {issue.issue_type}: {issue.description}[/red]")
            if issue.stages:
                self.console.print(f"    Stages: {', '.join(issue.stages)}")

        if warning_issues:
            self.console.print(f"\n[yellow]⚠ {len(warning_issues)} warning(s)[/yellow]")
            for issue in warning_issues:
                self.console.print(f"  [yellow]• {issue.issue_type}: {issue.description}[/yellow]")

    def print_consistency_warnings(self, process: Process) -> None:
        """Print non-blocking consistency warnings.

        Args:
            process: Process with warnings
        """
        warning_issues = [
            i for i in process.issues
            if i.issue_type not in process.BLOCKING_ISSUE_TYPES
        ]
        if warning_issues:
            self.console.print(f"[yellow]⚠ {len(warning_issues)} warning(s)[/yellow]")
            for issue in warning_issues:
                self.console.print(f"  [yellow]• {issue.issue_type}: {issue.description}[/yellow]")

    def print_all_consistency_issues(self, process: Process) -> None:
        """Print all consistency issues (blocking and warnings).

        Args:
            process: Process with issues
        """
        blocking = [i for i in process.issues if i.issue_type in process.BLOCKING_ISSUE_TYPES]
        warnings = [i for i in process.issues if i.issue_type not in process.BLOCKING_ISSUE_TYPES]

        if blocking:
            self.console.print(f"[red]❌ {len(blocking)} blocking issue(s)[/red]")
            for issue in blocking:
                self.console.print(f"  [red]• {issue.issue_type}: {issue.description}[/red]")

        if warnings:
            self.console.print(f"[yellow]⚠ {len(warnings)} warning(s)[/yellow]")
            for issue in warnings:
                self.console.print(f"  [yellow]• {issue.issue_type}: {issue.description}[/yellow]")

    def print_consistency_issues_json(self, process: Process, source: str) -> None:
        """Print process consistency issues as JSON.

        Args:
            process: Process with consistency issues
            source: Source file path
        """
        issues_data = []
        for issue in process.issues:
            issue_dict = {
                "issue_type": str(issue.issue_type),
                "description": issue.description,
                "stages": issue.stages,
                "blocking": issue.issue_type in process.BLOCKING_ISSUE_TYPES,
            }
            if issue.details:
                issue_dict["details"] = issue.details
            issues_data.append(issue_dict)

        result = {
            "status": "consistency_error",
            "source": source,
            "process": process.to_dict(),
            "is_valid": process.is_valid,
            "consistency_issues": issues_data,
        }
        self.console.print_json(data=result)

    def print_evaluation_error(
        self, error: Exception, json_mode: bool | None = None
    ) -> None:
        """Print evaluation error with consistent formatting.

        Args:
            error: Exception that occurred during evaluation
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode
        error_msg = f"Evaluation failed: {error}"
        if json_mode:
            self.console.print_json(data={"error": error_msg})
        else:
            self.print_error(error_msg)

    def print_diagram_success(
        self,
        output_path: str,
        diagram_format: str = "mermaid",
        json_mode: bool | None = None,
    ) -> None:
        """Print diagram generation success with consistent formatting.

        Args:
            output_path: Path where diagram was written
            diagram_format: Format of the diagram (e.g., "mermaid", "graphviz")
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode
        if json_mode:
            self.console.print_json(
                data={"visualization": output_path, "format": diagram_format}
            )
        else:
            self.show_success(f"Mermaid visualization written to {output_path}")

    def print_diagram_error(
        self,
        error: Exception,
        error_type: str = "generation",
        json_mode: bool | None = None,
    ) -> None:
        """Print diagram error with consistent formatting.

        Args:
            error: Exception that occurred
            error_type: Type of error ("generation" or "write")
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode
        if error_type == "generation":
            error_msg = f"Failed to generate diagram: {error}"
        else:
            error_msg = f"Failed to write diagram file: {error}"

        if json_mode:
            self.console.print_json(data={"error": error_msg})
        else:
            self.print_error(error_msg)

    def print_process_created(
        self,
        process_name: str,
        file_path: str,
        template: str,
        stages_count: int,
        json_mode: bool | None = None,
    ) -> None:
        """Print process creation success with consistent formatting.

        Args:
            process_name: Name of the created process
            file_path: Path where process was created
            template: Template type used
            stages_count: Number of stages in the process
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode
        if json_mode:
            result = {
                "message": f"Process '{process_name}' created successfully",
                "file_path": file_path,
                "template": template,
                "stages": stages_count,
            }
            self.console.print_json(data=result)
        else:
            self.show_success(f"Process '{process_name}' created at {file_path}")
            self.console.print(f"   Template: {template}")
            self.console.print(f"   Stages: {stages_count}")
            self.console.print(
                f"\n💡 Use 'stageflow view {file_path}' to view the new process"
            )

    def print_registry_list(
        self,
        processes: list[str],
        registry_dir: str,
        process_details: list[dict],
        json_mode: bool | None = None,
    ) -> None:
        """Print registry process list with consistent formatting.

        Args:
            processes: List of process names in registry
            registry_dir: Path to registry directory
            process_details: List of process detail dictionaries
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        if json_mode:
            result = {
                "registry_processes": process_details,
                "total_count": len(processes),
            }
            self.console.print_json(data=result)
        else:
            if not processes:
                self.console.print("📂 No processes found in registry")
                self.console.print(f"   Registry directory: {registry_dir}")
                self.console.print(
                    "   Use 'stageflow reg import' to add processes to registry"
                )
                return

            self.console.print(
                f"[bold]📂 Registry Processes ({len(processes)} found)[/bold]"
            )
            self.console.print(f"   Registry directory: {registry_dir}\n")

            for i, detail in enumerate(process_details):
                prefix = "└─" if i == len(process_details) - 1 else "├─"
                status_icon = "✅" if detail.get("valid", False) else "❌"
                registry_name = detail.get("registry_name", "unknown")

                if "error" in detail:
                    self.console.print(f"{prefix} {status_icon} @{registry_name}")
                    self.console.print(f"   [red]{detail['error']}[/red]")
                else:
                    self.console.print(f"{prefix} {status_icon} @{registry_name}")
                    self.console.print(f"   Name: {detail.get('name', 'N/A')}")
                    if detail.get("description"):
                        self.console.print(f"   Description: {detail['description']}")
                    self.console.print(f"   Stages: {len(detail.get('stages', []))}")

                    issues = detail.get("consistency_issues", [])
                    if issues:
                        self.console.print(
                            f"   [yellow]Issues: {len(issues)} consistency problems[/yellow]"
                        )

                self.console.print()

            self.console.print(
                "💡 Use 'stageflow view @process_name' to inspect a specific process"
            )

    def print_registry_import_success(
        self,
        registry_name: str,
        source_file: str,
        overwritten: bool = False,
        json_mode: bool | None = None,
    ) -> None:
        """Print registry import success with consistent formatting.

        Args:
            registry_name: Name of process in registry
            source_file: Source file path
            overwritten: Whether process was overwritten
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode
        action = "overwritten" if overwritten else "imported"

        if json_mode:
            result = {
                "message": f"Process {action} successfully",
                "source_file": source_file,
                "registry_name": registry_name,
                "overwritten": overwritten,
            }
            self.console.print_json(data=result)
        else:
            self.show_success(f"Process {action} to registry as '@{registry_name}'")

    def print_registry_export_success(
        self,
        registry_name: str,
        destination_file: str,
        json_mode: bool | None = None,
    ) -> None:
        """Print registry export success with consistent formatting.

        Args:
            registry_name: Name of process in registry
            destination_file: Destination file path
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        if json_mode:
            result = {
                "message": "Process exported successfully",
                "registry_name": registry_name,
                "destination_file": destination_file,
            }
            self.console.print_json(data=result)
        else:
            self.show_success(
                f"Process '@{registry_name}' exported to {destination_file}"
            )

    def print_registry_delete_success(
        self,
        registry_name: str,
        file_path: str,
        json_mode: bool | None = None,
    ) -> None:
        """Print registry delete success with consistent formatting.

        Args:
            registry_name: Name of deleted process
            file_path: Path to deleted file
            json_mode: If True, output as JSON. If None, uses self.json_mode
        """
        json_mode = json_mode if json_mode is not None else self.json_mode

        if json_mode:
            result = {
                "message": f"Process '{registry_name}' deleted successfully",
                "process": registry_name,
                "file": file_path,
            }
            self.console.print_json(data=result)
        else:
            self.show_success(f"Process '{registry_name}' deleted from registry")

    def print_schema_success(
        self, output_path: str, stage: str, schema_type: str
    ) -> None:
        """Print schema generation success message.

        Args:
            output_path: Path where schema was written
            stage: Target stage name
            schema_type: Type of schema generated (cumulative or stage-specific)
        """
        if self.json_mode:
            self.console.print_json(
                data={
                    "success": True,
                    "output_path": output_path,
                    "stage": stage,
                    "schema_type": schema_type,
                }
            )
        else:
            self.console.print("[green]✓[/green] Schema generated successfully")
            self.console.print(f"  Stage: {stage}")
            self.console.print(f"  Type: {schema_type}")
            self.console.print(f"  Output: {output_path}")
