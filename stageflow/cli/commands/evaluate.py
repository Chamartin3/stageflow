"""Element evaluation command for StageFlow CLI."""

import json
from pathlib import Path

import click

from stageflow.cli.utils import format_result, handle_error
from stageflow.core.element import DictElement
from stageflow.process.schema.loaders import load_process


@click.command()
@click.argument("process_file", type=click.Path(exists=True, path_type=Path))
@click.argument("element_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--current-stage",
    "-s",
    help="Specify current stage to optimize evaluation",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (default: stdout)",
)
@click.pass_context
def evaluate_command(
    ctx: click.Context,
    process_file: Path,
    element_file: Path,
    current_stage: str,
    output_format: str,
    output: Path,
):
    """
    Evaluate an element against a process.

    PROCESS_FILE: Path to process definition (YAML/JSON)
    ELEMENT_FILE: Path to element data (JSON)

    Example:
        stageflow evaluate process.yaml element.json --current-stage=profile_setup
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Load process
        if verbose:
            click.echo(f"Loading process from {process_file}")
        process = load_process(str(process_file))

        # Load element data
        if verbose:
            click.echo(f"Loading element from {element_file}")
        with open(element_file, encoding="utf-8") as f:
            element_data = json.load(f)

        element = DictElement(element_data)

        # Evaluate element
        if verbose:
            click.echo("Evaluating element against process...")
        result = process.evaluate(element, current_stage)

        # Format and output result
        output_text = format_result(result, output_format, verbose)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_text)
            if verbose:
                click.echo(f"Result written to {output}")
        else:
            click.echo(output_text)

    except Exception as e:
        handle_error(e, verbose)
