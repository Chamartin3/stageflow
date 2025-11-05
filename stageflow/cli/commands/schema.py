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

    Examples:

        # Generate cumulative schema to stdout
        stageflow process schema process.yaml review

        # Generate stage-specific schema
        stageflow process schema process.yaml review --stage-specific

        # Save to file
        stageflow process schema process.yaml review -o schema.yaml

        # Get JSON output for processing
        stageflow process schema process.yaml review --json
    """
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode to suppress all non-JSON output
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Load process using context (handles all error reporting and exits on failure)
    process = cli_ctx.load_process_or_exit(source)

    # Generate schema
    schema_type_str = "stage-specific" if stage_specific else "cumulative"
    cli_ctx.print_progress(
        f"Generating {schema_type_str} schema for stage '{target_stage}'..."
    )

    try:
        generator = SchemaGenerator(process)

        if stage_specific:
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
            cli_ctx.console.print(schema_content)
        else:
            # Human-readable output
            cli_ctx.console.print(schema_content)
