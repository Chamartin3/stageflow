"""Process management command group."""

import typer

from stageflow.cli.commands.diagram import diagram_command
from stageflow.cli.commands.new import new_command
from stageflow.cli.commands.registry import reg_app
from stageflow.cli.commands.schema import schema_command
from stageflow.cli.commands.view import view_command

# Create process command group
process_app = typer.Typer(
    name="process",
    help="Process management commands",
    no_args_is_help=True,
)

# Register subcommands
process_app.command("view")(view_command)
process_app.command("new")(new_command)
process_app.command("diagram")(diagram_command)
process_app.command("schema")(schema_command)

# Add registry as subcommand group with explicit name
process_app.add_typer(reg_app, name="registry")
