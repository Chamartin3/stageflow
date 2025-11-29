"""Schema command for generating JSON schemas from process definitions."""

from pathlib import Path
from typing import Annotated

import typer

from stageflow.cli.utils import safe_write_file
from stageflow.elements.schema import SchemaGenerator


def schema_command(
    ctx: typer.Context,
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    target_stage: Annotated[str, typer.Argument(help="Target stage name")],
    stage_specific: Annotated[
        bool,
        typer.Option(
            "--stage-specific",
            "-s",
            help="Generate schema for specific stage only (default: cumulative)",
        ),
    ] = False,
    gate: Annotated[
        str | None,
        typer.Option(
            "--gate",
            "-g",
            help="Generate final schema for specific gate (includes fields + gate lock properties)",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (default: stdout)"),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Generate JSON Schema for a process stage.

    By default, generates a cumulative schema including all properties from
    the initial stage to the target stage. Use --stage-specific to generate
    a schema for only the target stage.

    Use --gate to generate a final schema for exiting via a specific gate,
    which includes initial fields plus properties evaluated by the gate's locks.

    Examples:

        # Generate cumulative schema to stdout
        stageflow process schema process.yaml review

        # Generate stage-specific schema
        stageflow process schema process.yaml review --stage-specific

        # Generate initial schema (fields only) for stage
        stageflow process schema process.yaml checkout --stage-specific

        # Generate final schema for specific gate
        stageflow process schema process.yaml checkout --gate verify_payment

        # Save to file
        stageflow process schema process.yaml review -o schema.yaml

        # Get JSON output for processing
        stageflow process schema process.yaml review --json
    """
    # Access CLI context
    cli_ctx = ctx.obj

    # When outputting to stdout (no output file), treat as machine-parseable mode
    # to suppress warnings/progress that would corrupt the parseable output
    stdout_mode = output is None
    cli_ctx.json_mode = json_output or stdout_mode
    cli_ctx.printer.json_mode = json_output or stdout_mode

    # Load process using context (handles all error reporting and exits on failure)
    process = cli_ctx.load_process_or_exit(source)

    # Determine schema type
    if gate:
        schema_type_str = f"final (gate: {gate})"
    elif stage_specific:
        schema_type_str = "stage-specific"
    else:
        schema_type_str = "cumulative"

    cli_ctx.print_progress(
        f"Generating {schema_type_str} schema for stage '{target_stage}'..."
    )

    try:
        generator = SchemaGenerator(process)

        if gate:
            # Generate final schema for specific gate
            stage_schema = generator.generate_final_schema(target_stage, gate)
            schema_dict = generator.stage_schema_to_json_schema(stage_schema)
        elif stage_specific:
            schema_dict = generator.generate_stage_schema(target_stage)
        else:
            schema_dict = generator.generate_cumulative_schema(target_stage)

        # Convert to appropriate format
        if json_output:
            schema_content = generator.to_json(schema_dict)
        else:
            schema_content = generator.to_yaml(schema_dict)

    except ValueError as e:
        cli_ctx.printer.print_error(str(e))
        raise typer.Exit(1) from e
    except Exception as e:
        cli_ctx.printer.print_error(f"Schema generation failed: {e}")
        raise typer.Exit(1) from e

    # Output schema
    if output:
        # Write to file
        try:
            # Ensure appropriate extension
            if not output.suffix:
                ext = ".json" if json_output else ".yaml"
                output = output.with_suffix(ext)

            safe_write_file(output, schema_content, verbose=False)

            if not json_output:
                cli_ctx.printer.print_schema_success(
                    output_path=str(output),
                    stage=target_stage,
                    schema_type=schema_type_str,
                )
        except Exception as e:
            cli_ctx.printer.print_error(f"Failed to write schema: {e}")
            raise typer.Exit(1) from e
    else:
        # Output to stdout
        if json_output:
            # Machine-readable JSON output
            cli_ctx.console.print(schema_content, highlight=False, markup=False)
        else:
            # Human-readable output - disable Rich formatting to preserve YAML structure
            cli_ctx.console.print(schema_content, highlight=False, markup=False)
