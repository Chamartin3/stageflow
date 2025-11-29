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

    # Load process (non-exiting to allow printing details even with issues)
    success = cli_ctx.load_process(source)

    if not success:
        # Load failed completely (file not found, parse error, etc.)
        raise typer.Exit(code=1)

    process = cli_ctx.process
    source_type = cli_ctx.loader.detect_source_type(source)

    # Print process details (handles JSON vs normal mode)
    cli_ctx.printer.print_process_details(
        process=process,
        source=cli_ctx.source,
        source_type_value=source_type.value,
        load_result=cli_ctx.load_result,
    )

    # Show consistency issues after process details
    if process.issues and not json_output:
        cli_ctx.printer.print_all_consistency_issues(process)

    # Exit with code 1 if process has blocking issues
    if not process.is_valid:
        raise typer.Exit(code=1)
