"""View command for displaying process details."""

from typing import Annotated

import typer
from rich.console import Console

from stageflow.cli.commands.common import detect_source_type, load_process_from_source
from stageflow.cli.commands.helpers import (
    build_process_description,
    print_process_description,
)

console = Console()


def view_command(
    source: Annotated[str, typer.Argument(help="Process source (file path or @registry_name)")],
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
):
    """View process details including stages, transitions, and validation status."""
    try:
        process = load_process_from_source(source, verbose=False)
        description = build_process_description(process)
        description["source"] = source
        description["source_type"] = detect_source_type(source)

        if json_output:
            console.print_json(data=description)
        else:
            print_process_description(description, process)

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
