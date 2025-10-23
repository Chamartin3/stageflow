"""Diagram command for generating process visualizations."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from stageflow.cli.commands.common import (
    SourceType,
    detect_source_type,
    load_process_from_source,
)
from stageflow.cli.utils import safe_write_file, show_success
from stageflow.schema import ProcessWithErrors
from stageflow.visualization.mermaid import MermaidDiagramGenerator

console = Console()


def diagram_command(
    source: Annotated[str, typer.Argument(help="Process source (file path or @registry_name)")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
):
    """Generate process visualization diagram."""
    try:
        process = load_process_from_source(source, verbose=False)

        # Check if process has validation errors
        if isinstance(process, ProcessWithErrors):
            error_msg = f"Cannot generate diagram for invalid process. {process.get_error_summary()}"
            if json_output:
                console.print_json(data={
                    "error": error_msg,
                    "validation_errors": process.validation_errors
                })
            else:
                console.print("[red]❌ Error:[/red] Cannot generate diagram for invalid process")
                console.print(f"   {process.get_error_summary()}")
                console.print(f"   Fix the process first using: stageflow view {source}")
            raise typer.Exit(1)

        # Default output filename if not provided
        if not output:
            source_type = detect_source_type(source)
            if source_type == SourceType.REGISTRY:
                process_name = source[1:]
                output = Path(f"{process_name}_diagram.md")
            else:
                source_path = Path(source)
                output = source_path.with_suffix('.diagram.md')

        generator = MermaidDiagramGenerator()
        diagram_content = generator.generate_process_diagram(process, style="overview")

        if not output.suffix:
            output = output.with_suffix(".md")

        safe_write_file(output, diagram_content, verbose=False)

        if json_output:
            console.print_json(data={"visualization": str(output), "format": "mermaid"})
        else:
            show_success(f"Mermaid visualization written to {output}")

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
