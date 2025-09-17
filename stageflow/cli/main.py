"""Main CLI entry point for StageFlow."""


import click

from stageflow.cli.commands.evaluate import evaluate_command
from stageflow.cli.commands.init import init_command
from stageflow.cli.commands.validate import validate_command
from stageflow.cli.commands.visualize import visualize_command


@click.group()
@click.version_option(version="0.1.0", prog_name="stageflow")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """
    StageFlow: A declarative multi-stage validation framework.

    StageFlow provides a reusable, non-mutating way to evaluate where a
    data-bearing Element stands within a multi-stage Process.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# Register commands
cli.add_command(evaluate_command, name="evaluate")
cli.add_command(validate_command, name="validate")
cli.add_command(visualize_command, name="visualize")
cli.add_command(init_command, name="init")


def main():
    """Main entry point for the CLI."""
    cli()
