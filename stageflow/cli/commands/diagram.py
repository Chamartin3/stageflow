"""Diagram command for generating process visualizations."""

from pathlib import Path
from typing import Annotated

import typer

from stageflow.cli.utils import safe_write_file
from stageflow.models import ProcessSourceType
from stageflow.visualization.mermaid import MermaidDiagramGenerator


def diagram_command(
    ctx: typer.Context,
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file path")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Generate process visualization diagram."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode to suppress all non-JSON output
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Load process using context (handles all error reporting and exits on failure)
    process = cli_ctx.load_process_or_exit(source)

    # Determine output filename
    if not output:
        source_type = cli_ctx.loader.detect_source_type(source)
        if source_type == ProcessSourceType.REGISTRY:
            process_name = source[1:]
            output = Path(f"{process_name}_diagram.md")
        else:
            source_path = Path(source)
            output = source_path.with_suffix(".diagram.md")

    # Generate diagram
    cli_ctx.print_progress("Generating diagram...")
    try:
        generator = MermaidDiagramGenerator()
        diagram_content = generator.generate_process_diagram(process, style="overview")
    except Exception as e:
        # Diagram generation errors are handled by printer for consistent formatting
        cli_ctx.printer.print_diagram_error(e, error_type="generation")
        raise typer.Exit(1) from e

    # Ensure .md extension
    if not output.suffix:
        output = output.with_suffix(".md")

    # Write diagram to file
    try:
        safe_write_file(output, diagram_content, verbose=False)
    except Exception as e:
        # File write errors are handled by printer for consistent formatting
        cli_ctx.printer.print_diagram_error(e, error_type="write")
        raise typer.Exit(1) from e

    # Print success (handles JSON vs normal mode, errors, and formatting)
    cli_ctx.printer.print_diagram_success(
        output_path=str(output),
        diagram_format="mermaid",
    )
