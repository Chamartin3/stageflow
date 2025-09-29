"""Visualization command for StageFlow CLI."""

from pathlib import Path

import click

from stageflow.cli.utils import (
    handle_error,
    safe_write_file,
    show_progress,
    show_success,
)
from stageflow.process.schema.loaders import load_process


@click.command()
@click.argument("process_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["mermaid", "graphviz", "dot", "text"]),
    default="mermaid",
    help="Visualization format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (default: stdout)",
)
@click.option(
    "--style",
    "-s",
    type=click.Choice(["overview", "detailed", "full"]),
    default="overview",
    help="Detail level for visualization",
)
@click.option(
    "--include-details",
    is_flag=True,
    help="Include gate and lock details (legacy - use --style detailed instead)",
)
@click.option(
    "--include-locks",
    is_flag=True,
    help="Include lock details in stage diagrams",
)
@click.pass_context
def visualize_command(
    ctx: click.Context,
    process_file: Path,
    output_format: str,
    output: Path,
    style: str,
    include_details: bool,
    include_locks: bool,
):
    """
    Generate visualization of a process flow.

    PROCESS_FILE: Path to process definition (YAML/JSON)

    Examples:
        stageflow visualize process.yaml --format=mermaid --output=diagram.md
        stageflow visualize process.yaml --format=graphviz --style=detailed
        stageflow visualize process.yaml --format=dot --output=process.dot
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    try:
        # Load process with progress
        show_progress(f"Loading process from {process_file}", verbose)
        process = load_process(str(process_file))

        # Map legacy include_details to style
        if include_details and style == "overview":
            style = "detailed"

        # Generate visualization based on format
        show_progress(f"Generating {output_format} visualization...", verbose)
        if output_format == "mermaid":
            output_text = _generate_mermaid_visualization(process, style, include_locks)
        elif output_format in ["graphviz", "dot"]:
            output_text = _generate_graphviz_visualization(process, style, include_locks)
        else:  # text format
            output_text = _generate_text_visualization(process, style == "detailed" or include_details)

        # Determine output file extension if output specified without extension
        if output and not output.suffix:
            if output_format == "mermaid":
                output = output.with_suffix(".md")
            elif output_format in ["graphviz", "dot"]:
                output = output.with_suffix(".dot")
            else:
                output = output.with_suffix(".txt")

        # Output result
        if output:
            safe_write_file(output, output_text, verbose)
            show_success(f"{output_format.capitalize()} visualization written to {output}")
        else:
            click.echo(output_text)

    except click.ClickException:
        # Re-raise click exceptions (already properly formatted)
        raise
    except Exception as e:
        handle_error(e, verbose)
        ctx.exit(1)


def _generate_mermaid_visualization(process, style: str, include_locks: bool) -> str:
    """Generate Mermaid diagram visualization."""
    try:
        from stageflow.process.visualization import MermaidDiagramGenerator

        generator = MermaidDiagramGenerator()
        return generator.generate_process_diagram(process, style=style)
    except ImportError:
        return _generate_import_error_message("Mermaid", "visualization")


def _generate_graphviz_visualization(process, style: str, include_locks: bool) -> str:
    """Generate Graphviz DOT visualization."""
    try:
        from stageflow.process.visualization import GraphvizDotGenerator

        generator = GraphvizDotGenerator()
        return generator.generate_process_diagram(process, style=style)
    except ImportError:
        return _generate_import_error_message("Graphviz", "visualization")


def _generate_import_error_message(format_name: str, extras_name: str) -> str:
    """Generate helpful error message for missing visualization dependencies."""
    return f"""
Error: {format_name} visualization not available.

To use {format_name} visualization, ensure the visualization module is properly installed.
If you're seeing this error, it might be due to:
1. Missing visualization dependencies
2. Import issues with the visualization module

Try reinstalling or checking your installation:
    pip install stageflow[{extras_name}]

Falling back to text visualization would require using --format=text
"""


def _generate_text_visualization(process, include_details: bool) -> str:
    """Generate simple text-based visualization."""
    lines = []
    lines.append(f"Process: {process.name}")
    lines.append("=" * (len(process.name) + 10))
    lines.append("")

    for i, stage_name in enumerate(process.stage_order):
        stage = process.get_stage(stage_name)
        if not stage:
            continue

        # Stage header
        prefix = "└─" if i == len(process.stage_order) - 1 else "├─"
        lines.append(f"{prefix} Stage: {stage.name}")

        if include_details and stage.gates:
            for j, gate in enumerate(stage.gates):
                gate_prefix = "   └─" if j == len(stage.gates) - 1 else "   ├─"
                lines.append(f"{gate_prefix} Gate: {gate.name}")

                # Handle new gate structure with components
                if hasattr(gate, 'components') and gate.components:
                    for k, component in enumerate(gate.components):
                        if hasattr(component, 'lock'):
                            lock = component.lock
                            lock_prefix = "      └─" if k == len(gate.components) - 1 else "      ├─"
                            lock_desc = f"{lock.property_path} {lock.lock_type.value}"
                            if hasattr(lock, 'expected_value') and lock.expected_value is not None:
                                lock_desc += f" {lock.expected_value}"
                            lines.append(f"{lock_prefix} {lock_desc}")
                # Handle legacy gate structure with locks attribute
                elif hasattr(gate, 'locks') and gate.locks:
                    for k, lock in enumerate(gate.locks):
                        lock_prefix = "      └─" if k == len(gate.locks) - 1 else "      ├─"
                        lock_desc = f"{lock.property_path} {lock.lock_type.value}"
                        if hasattr(lock, 'expected_value') and lock.expected_value is not None:
                            lock_desc += f" {lock.expected_value}"
                        lines.append(f"{lock_prefix} {lock_desc}")

        lines.append("")

    return "\n".join(lines)
