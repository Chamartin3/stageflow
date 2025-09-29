"""Element evaluation command for StageFlow CLI."""

from pathlib import Path

import click

from stageflow.cli.utils import (
    format_result,
    handle_error,
    load_element_data,
    safe_write_file,
    show_progress,
    show_success,
    validate_output_format,
)
from stageflow.element import DictElement
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
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    try:
        # Validate output format
        supported_formats = ["text", "json", "yaml"]
        validate_output_format(output_format, supported_formats)

        # Load process with progress
        show_progress(f"Loading process from {process_file}", verbose)
        process = load_process(str(process_file))

        # Load element data with enhanced error handling
        show_progress(f"Loading element from {element_file}", verbose)
        element_data = load_element_data(element_file, verbose)
        element = DictElement(element_data)

        # Evaluate element
        show_progress("Evaluating element against process...", verbose)
        result = process.evaluate(element, current_stage)

        # Format and output result
        show_progress("Formatting evaluation result...", verbose)
        output_text = format_result(result, output_format, verbose)

        if output:
            safe_write_file(output, output_text, verbose)
            show_success(f"Evaluation result written to {output}")
        else:
            click.echo(output_text)

    except click.ClickException:
        # Re-raise click exceptions (already properly formatted)
        raise
    except Exception as e:
        handle_error(e, verbose)
