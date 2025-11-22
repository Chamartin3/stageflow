"""Evaluate command for assessing elements against processes."""

from pathlib import Path
from typing import Annotated

import typer

from stageflow.elements import Element
from stageflow.process import Process


def get_element_stage(
    stage_override: str | None, process: Process, elem: Element
) -> tuple[str, str]:
    """Determine the stage to use based on override, process config, or None.

    Args:
        stage_override: Stage name from command-line override
        process: Process instance
        elem: Element to evaluate

    Returns:
        Tuple of (stage_id, message) describing the stage selection

    Raises:
        ValueError: If the specified stage doesn't exist in the process
    """

    def validate_stage(stage_id: str, source: str) -> None:
        """Validate that stage exists in process."""
        if not process.get_stage(stage_id):
            available_stages = [s._id for s in process.stages]
            raise ValueError(
                f"Stage '{stage_id}' from {source} does not exist in process. "
                f"Available stages: {', '.join(available_stages)}"
            )

    if stage_override:
        message = f"Using explicit stage override: '{stage_override}'"
        validate_stage(stage_override, "command-line override")
        return stage_override, message

    config_stage = getattr(process, "stage_prop", None)
    msg = ""
    if config_stage:
        msg = f"Process configured to auto-extract stage from property: {config_stage}"
        extracted_stage = elem.get_property(config_stage)
        if extracted_stage:
            msg += f"\n extracted stage: '{extracted_stage}'"
            validate_stage(extracted_stage, f"element property '{config_stage}'")
            return extracted_stage, msg
        else:
            msg += "\n No property found in element"

    msg += f"\n Falling back to process initial_stage: '{process.initial_stage._id}'"
    return process.initial_stage._id, msg


def evaluate_command(
    ctx: typer.Context,
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    element: Annotated[
        Path | None,
        typer.Option(
            "--element",
            "-e",
            help="Element file for evaluation (JSON/YAML). If omitted, reads from stdin",
        ),
    ] = None,
    stage: Annotated[
        str | None,
        typer.Option(
            "--stage",
            "-s",
            help="Override current stage (default: auto-extract from element or use initial_stage)",
        ),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
    show_schema: Annotated[
        bool,
        typer.Option(
            "--show-schema",
            help="Show expected schema structure for the stage",
        ),
    ] = False,
    cumulative_schema: Annotated[
        bool,
        typer.Option(
            "--cumulative-schema",
            help="Show cumulative schema (all properties from previous stages)",
        ),
    ] = False,
):
    """
    Evaluate an element against a process.

    Stage selection precedence:
    1. --stage/-s flag (highest priority)
    2. Auto-extraction from element (if stage_prop configured)
    3. Process initial_stage (lowest priority)

    Element source:
    - If --element/-e is provided, reads from the specified file
    - If omitted, reads JSON from stdin (useful for piping data)

    Schema hints:
    - Automatically shown when element has INVALID_SCHEMA or ACTION_REQUIRED status
    - Use --show-schema to always display schema hints
    - Use --cumulative-schema to show properties from all previous stages
    """
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode to suppress all non-JSON output
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Load process using context (handles all error reporting and exits on failure)
    process = cli_ctx.load_process_or_exit(source)

    # Load element using context (handles all error reporting and exits on failure)
    element_path = str(element) if element else None
    elem = cli_ctx.load_element_or_exit(element_path)

    # Determine stage and show selection method in verbose mode
    cli_ctx.print_progress("Evaluating element against process...")
    try:
        stage_id, stage_msg = get_element_stage(stage, process, elem)
        cli_ctx.print_verbose(stage_msg)
    except ValueError as e:
        # Stage validation errors are handled by printer for consistent formatting
        if json_output:
            cli_ctx.print_json(data={"error": str(e)})
        else:
            cli_ctx.print_error(str(e))
        raise typer.Exit(1) from e

    # Evaluate element
    try:
        result = process.evaluate(elem, stage_id)
    except Exception as e:
        # Evaluation errors are handled by printer for consistent formatting
        cli_ctx.printer.print_evaluation_error(e)
        raise typer.Exit(1) from e

    # Print results (handles JSON vs normal mode, errors, and formatting)
    cli_ctx.printer.print_evaluation_result(
        process=process,
        result=result,
    )

    # Show schema hint if requested or if evaluation needs help
    if not json_output:
        from stageflow.cli.utils.format import EvaluationFormatter

        stage_result = result["stage_result"]
        should_show_schema = show_schema or stage_result.status in (
            "invalid_schema",
            "action_required",
        )

        if should_show_schema:
            # Get schema for helpful hints
            schema = process.get_schema(stage_id, partial=not cumulative_schema)
            schema_hint = EvaluationFormatter.format_schema_hint(
                schema, stage_id, show_cumulative=cumulative_schema
            )

            if schema_hint:
                cli_ctx.printer.print(schema_hint)
