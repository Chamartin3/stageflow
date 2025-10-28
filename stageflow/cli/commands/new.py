"""New command for creating process files from templates."""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from ruamel.yaml import YAML

from stageflow.cli.utils import show_success
from stageflow.templates import ProcessTemplate, generate_process_from_template

console = Console()


def new_command(
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
    # Show help if no file path provided
    if file_path is None:
        console.print("\n[yellow]Usage:[/yellow] stageflow new [OPTIONS] FILE_PATH\n")
        console.print(
            "Create a new process file from template (always generates YAML).\n"
        )
        console.print("[cyan]Arguments:[/cyan]")
        console.print(
            "  FILE_PATH  File path for new process (will add .yaml if missing) [required]\n"
        )
        console.print("[cyan]Options:[/cyan]")
        available_templates = "|".join(ProcessTemplate.list_templates())
        console.print(
            f"  --template, -t  Template type ({available_templates}) [default: basic]"
        )
        console.print("  --json          Output in JSON format")
        console.print("  --help          Show this message\n")
        console.print("[cyan]Examples:[/cyan]")
        console.print("  stageflow new process.yaml")
        console.print("  stageflow new process              # Creates process.yaml")
        console.print("  stageflow new approval --template approval")
        raise typer.Exit(0)

    try:
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

        if target_path.exists():
            raise typer.BadParameter(f"File '{target_path}' already exists")

        process_name = target_path.stem

        if not ProcessTemplate.is_valid(template):
            available = ", ".join(ProcessTemplate.list_templates())
            raise typer.BadParameter(
                f"Invalid template '{template}'. Available: {available}"
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

        if json_output:
            result = {
                "message": f"Process '{process_name}' created successfully",
                "file_path": str(target_path),
                "template": template,
                "stages": len(process_schema["stages"]),
            }
            console.print_json(data=result)
        else:
            show_success(f"Process '{process_name}' created at {target_path}")
            console.print(f"   Template: {template}")
            console.print(f"   Stages: {len(process_schema['stages'])}")
            console.print(
                f"\n💡 Use 'stageflow view {target_path}' to view the new process"
            )

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
