"""View command for displaying process details."""

from typing import Annotated

import typer


def view_command(
    ctx: typer.Context,
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """View process details including stages, transitions, and validation status."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode to suppress all non-JSON output
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Load process using context (handles all error reporting, warnings, and exits on failure)
    process = cli_ctx.load_process_or_exit(source)

    # Get source type for display
    source_type = cli_ctx.loader.detect_source_type(source)

    # Print process details (handles JSON vs normal mode, errors, and formatting)
    cli_ctx.printer.print_process_details(
        process=process,
        source=cli_ctx.source,
        source_type_value=source_type.value,
        load_result=cli_ctx.load_result,
    )
