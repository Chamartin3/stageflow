"""Evaluate command for assessing elements against processes."""

import json
import sys
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console

from stageflow.cli.commands.common import load_process_from_source
from stageflow.cli.utils import (
    EvaluationFormatter,
    print_evaluation_result,
    show_progress,
)
from stageflow.element import create_element
from stageflow.process import Process
from stageflow.schema import LoadError, ProcessWithErrors, load_element

console = Console()


def evaluate_command(
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    element: Annotated[
        Path | None,
        typer.Option(
            "--element",
            "-e",
            help="Element file for evaluation (JSON/YAML). If omitted, reads from stdin",
        ),
    ] = None,
    stage: Annotated[
        str | None,
        typer.Option(
            "--stage",
            "-s",
            help="Override current stage (default: auto-extract from element or use initial_stage)",
        ),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Verbose output")
    ] = False,
):
    """
    Evaluate an element against a process.

    Stage selection precedence:
    1. --stage/-s flag (highest priority)
    2. Auto-extraction from element (if stage_prop configured)
    3. Process initial_stage (lowest priority)

    Element source:
    - If --element/-e is provided, reads from the specified file
    - If omitted, reads JSON from stdin (useful for piping data)
    """
    try:
        process_result = load_process_from_source(source, verbose)

        # Check if process has validation errors
        if isinstance(process_result, ProcessWithErrors):
            error_msg = f"Cannot evaluate against invalid process. {process_result.get_error_summary()}"
            if json_output:
                console.print_json(
                    data={
                        "error": error_msg,
                        "validation_errors": process_result.validation_errors,
                    }
                )
            else:
                console.print(
                    "[red]❌ Error:[/red] Cannot evaluate against invalid process"
                )
                console.print(f"   {process_result.get_error_summary()}")
                console.print(
                    f"   Fix the process first using: stageflow view {source}"
                )
            raise typer.Exit(1)

        # Type narrowing: at this point, process_result must be Process
        process = cast(Process, process_result)

        # Load element from file or stdin
        if element:
            # Load from file
            if verbose:
                show_progress(f"Loading element from {element}", verbose=True)

            try:
                elem = load_element(str(element))
            except LoadError as e:
                raise typer.BadParameter(f"Failed to load element: {e}") from e
        else:
            # Load from stdin
            if verbose:
                show_progress("Reading element from stdin...", verbose=True)

            try:
                stdin_data = sys.stdin.read()
                if not stdin_data.strip():
                    raise typer.BadParameter("No data provided on stdin")

                element_data = json.loads(stdin_data)
                elem = create_element(element_data)
            except json.JSONDecodeError as e:
                raise typer.BadParameter(f"Failed to parse JSON from stdin: {e}") from e
            except Exception as e:
                raise typer.BadParameter(
                    f"Failed to create element from stdin: {e}"
                ) from e

        # Show stage selection method in verbose mode
        if verbose:
            if stage:
                console.print(f"[dim]Using explicit stage override: '{stage}'[/dim]")
            elif hasattr(process, "stage_prop") and process.stage_prop:
                console.print(
                    f"[dim]Process configured to auto-extract stage from property: "
                    f"'{process.stage_prop}'[/dim]"
                )
                # Try to show what stage will be extracted
                try:
                    extracted_stage = elem.get_property(process.stage_prop)
                    if extracted_stage:
                        console.print(
                            f"[dim]Extracted stage from element: '{extracted_stage}'[/dim]"
                        )
                except Exception:
                    pass
            else:
                console.print(
                    f"[dim]Using process initial stage: '{process.initial_stage._id}'[/dim]"
                )

        # Evaluate
        if verbose:
            show_progress("Evaluating element against process...", verbose=True)

        result = process.evaluate(elem, stage)

        if json_output:
            json_result = EvaluationFormatter.format_json_result(process, result)
            console.print_json(data=json_result)
        else:
            print_evaluation_result(result)

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
