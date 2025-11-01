"""View command for displaying process details."""

from typing import Annotated

import typer
from rich.console import Console

from stageflow.cli.commands.common import detect_source_type, load_process_from_source
from stageflow.cli.utils import build_process_description, print_process_description
from stageflow.schema import ProcessWithErrors

console = Console()


def view_command(
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """View process details including stages, transitions, and validation status."""
    try:
        process = load_process_from_source(source, verbose=False)
        description = build_process_description(process)

        if json_output:
            # Create a mutable dict with additional fields for JSON output
            json_data = dict(description)
            json_data["source"] = source
            # Convert enum to its string value for JSON serialization
            json_data["source_type"] = detect_source_type(source).value

            # For ProcessWithErrors, also add an error field to match expected format
            if isinstance(process, ProcessWithErrors):
                json_data["error"] = process.get_error_summary()

            console.print_json(data=json_data)
        else:
            print_process_description(description, process)

        # Exit with error code only for structural validation errors
        # (ProcessWithErrors without a partial_process means structural issues)
        # Consistency errors (invalid references) should not cause exit code 1
        if isinstance(process, ProcessWithErrors):
            # Check if this is a structural error (no partial process could be created)
            # vs a consistency error (process was created but has issues)
            # Structural errors are those caught during config parsing/validation
            # (before Process object creation) and include phrases like:
            # "Required field 'name' is missing from process definition"
            # "Process 'initial_stage' must be a non-empty string"
            is_structural_error = any(
                "required field" in err.lower() and "missing from process definition" in err.lower()
                for err in process.validation_errors
            )
            if is_structural_error:
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
