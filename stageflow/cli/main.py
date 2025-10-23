"""StageFlow CLI - Typer-based command line interface."""

import typer
from rich.console import Console

from stageflow.cli.commands import (
    diagram_command,
    evaluate_command,
    new_command,
    reg_app,
    view_command,
)

# Create main app and console
app = typer.Typer(
    name="stageflow",
    help="StageFlow: A declarative multi-stage validation framework",
    no_args_is_help=True,
)
console = Console()

# Register top-level commands
app.command(name="view")(view_command)
app.command(name="evaluate")(evaluate_command)
app.command(name="new")(new_command)
app.command(name="diagram")(diagram_command)

# Register registry subcommand group
app.add_typer(reg_app, name="reg")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == '__main__':
    main()
