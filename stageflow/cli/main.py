"""StageFlow CLI - Typer-based command line interface."""

from typing import Annotated

import typer
from rich.console import Console

from stageflow.cli.commands import (
    evaluate_command,
    process_app,
)
from stageflow.cli.utils import CLIContext

# Create main app and console
app = typer.Typer(
    name="stageflow",
    help="StageFlow: A declarative multi-stage validation framework",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main_callback(
    ctx: typer.Context,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
):
    """
    StageFlow CLI callback - sets up context for all commands.

    This callback initializes the CLIContext object that is shared across all commands.
    Commands can access the context via ctx.obj, which provides:
    - Process loading and validation
    - Error handling and reporting
    - Console output management
    - Verbose mode control
    """
    # Initialize context with console and verbose setting
    cli_context = CLIContext(console=console, verbose=verbose)

    # Store the context for all commands to access
    ctx.obj = cli_context


# Register process command group
app.add_typer(process_app)

# Register evaluate command at top level
app.command(name="evaluate")(evaluate_command)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
