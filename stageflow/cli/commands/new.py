"""New command for creating process files from templates."""

import os
from pathlib import Path
from typing import Annotated

import typer
from ruamel.yaml import YAML

from stageflow.templates import ProcessTemplate, generate_process_from_template


def new_command(
    ctx: typer.Context,
    file_path: Annotated[
        str | None, typer.Argument(help="File path for new process")
    ] = None,
    template: Annotated[
        str, typer.Option("--template", "-t", help="Template type")
    ] = "basic",
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Create a new process file from template."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode to suppress all non-JSON output
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Show help if no file path provided
    if file_path is None:
        cli_ctx.console.print(
            "\n[yellow]Usage:[/yellow] stageflow new [OPTIONS] FILE_PATH\n"
        )
        cli_ctx.console.print(
            "Create a new process file from template (always generates YAML).\n"
        )
        cli_ctx.console.print("[cyan]Arguments:[/cyan]")
        cli_ctx.console.print(
            "  FILE_PATH  File path for new process (will add .yaml if missing) [required]\n"
        )
        cli_ctx.console.print("[cyan]Options:[/cyan]")
        available_templates = "|".join(ProcessTemplate.list_templates())
        cli_ctx.console.print(
            f"  --template, -t  Template type ({available_templates}) [default: basic]"
        )
        cli_ctx.console.print("  --json          Output in JSON format")
        cli_ctx.console.print("  --help          Show this message\n")
        cli_ctx.console.print("[cyan]Examples:[/cyan]")
        cli_ctx.console.print("  stageflow new process.yaml")
        cli_ctx.console.print(
            "  stageflow new process              # Creates process.yaml"
        )
        cli_ctx.console.print("  stageflow new approval --template approval")
        raise typer.Exit(0)

    # Get the actual working directory from environment variable if set by wrapper
    # This ensures relative paths are resolved from where the user ran the command
    actual_cwd = os.environ.get("STAGEFLOW_ACTUAL_CWD")
    if actual_cwd and not Path(file_path).is_absolute():
        target_path = Path(actual_cwd) / file_path
    else:
        target_path = Path(file_path)

    # Ensure the file has a .yaml extension
    if target_path.suffix.lower() not in [".yaml", ".yml"]:
        target_path = target_path.with_suffix(".yaml")

    # Validate target path doesn't exist
    if target_path.exists():
        error_msg = f"File '{target_path}' already exists"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1)

    process_name = target_path.stem

    # Validate template
    if not ProcessTemplate.is_valid(template):
        available = ", ".join(ProcessTemplate.list_templates())
        error_msg = f"Invalid template '{template}'. Available: {available}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1)

    # Generate process from template
    try:
        cli_ctx.print_progress(
            f"Creating process '{process_name}' from template '{template}'..."
        )
        process_schema = generate_process_from_template(process_name, template)
        file_content = {"process": process_schema}

        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Always write as YAML
        yaml_obj = YAML()
        yaml_obj.indent(mapping=2, sequence=4, offset=2)
        yaml_obj.preserve_quotes = True
        with target_path.open("w") as f:
            yaml_obj.dump(file_content, f)

        # Print success (handles JSON vs normal mode and formatting)
        cli_ctx.printer.print_process_created(
            process_name=process_name,
            file_path=str(target_path),
            template=template,
            stages_count=len(process_schema["stages"]),
        )

    except Exception as e:
        # Handle unexpected errors during process creation
        error_msg = f"Failed to create process: {e}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1) from e
