"""Docs command for generating process documentation."""

from pathlib import Path
from typing import Annotated

import typer

from stageflow.cli.utils import safe_write_file
from stageflow.models import ProcessSourceType
from stageflow.visualization.documentation import ProcessDocumentGenerator


def docs_command(
    ctx: typer.Context,
    source: Annotated[
        str, typer.Argument(help="Process source (file path or @registry_name)")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file or directory path")
    ] = None,
    split: Annotated[
        bool, typer.Option("--split", help="Split output into separate files per stage")
    ] = False,
    templates: Annotated[
        Path | None, typer.Option("--templates", "-t", help="Custom templates directory")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Generate comprehensive process documentation."""
    cli_ctx = ctx.obj

    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Load process
    process = cli_ctx.load_process_or_exit(source)

    # Determine output path
    if not output:
        source_type = cli_ctx.loader.detect_source_type(source)
        if source_type == ProcessSourceType.REGISTRY:
            process_name = source[1:]
            output = Path(f"{process_name}_docs.md") if not split else Path(f"{process_name}_docs")
        else:
            source_path = Path(source)
            output = source_path.with_suffix(".docs.md") if not split else source_path.with_suffix(".docs")

    # Generate documentation
    cli_ctx.print_progress("Generating documentation...")
    try:
        generator = ProcessDocumentGenerator(templates_dir=templates)

        if split:
            # Split mode - generate multiple files
            output.mkdir(parents=True, exist_ok=True)
            (output / "stages").mkdir(exist_ok=True)

            files = generator.generate_split(process, output)
            for file_path, content in files.items():
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                safe_write_file(Path(file_path), content, verbose=False)

            if json_output:
                cli_ctx.printer.print_json({
                    "status": "success",
                    "output_dir": str(output),
                    "files": list(files.keys()),
                })
            else:
                typer.echo(f"✅ Documentation generated: {len(files)} files in {output}/")
        else:
            # Single file mode
            if not output.suffix:
                output = output.with_suffix(".md")

            content = generator.generate(process)
            safe_write_file(output, content, verbose=False)

            if json_output:
                cli_ctx.printer.print_json({"status": "success", "output": str(output)})
            else:
                typer.echo(f"✅ Documentation generated: {output}")

    except Exception as e:
        cli_ctx.printer.print_error(f"Documentation generation failed: {e}")
        raise typer.Exit(1) from e
