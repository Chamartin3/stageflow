"""Visualization command for StageFlow CLI."""

from pathlib import Path

import click

from stageflow.cli.utils import handle_error
from stageflow.loaders import load_process


@click.command()
@click.argument("process_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["mermaid", "dot", "text"]),
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
    "--include-details",
    is_flag=True,
    help="Include gate and lock details in visualization",
)
@click.pass_context
def visualize_command(
    ctx: click.Context,
    process_file: Path,
    output_format: str,
    output: Path,
    include_details: bool,
):
    """
    Generate visualization of a process flow.

    PROCESS_FILE: Path to process definition (YAML/JSON)

    Example:
        stageflow visualize process.yaml --format=mermaid --output=diagram.md
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Load process
        if verbose:
            click.echo(f"Loading process from {process_file}")
        process = load_process(str(process_file))

        # Generate visualization based on format
        if output_format == "mermaid":
            try:
                from stageflow.visualization import MermaidGenerator

                generator = MermaidGenerator()
                output_text = generator.generate_process_diagram(process, include_details)
            except ImportError:
                click.echo("Mermaid visualization requires the 'visualization' extras")
                click.echo("Install with: pip install stageflow[visualization]")
                ctx.exit(1)

        elif output_format == "dot":
            try:
                from stageflow.visualization import GraphvizGenerator

                generator = GraphvizGenerator()
                output_text = generator.generate_process_diagram(process, include_details)
            except ImportError:
                click.echo("Graphviz visualization requires the 'visualization' extras")
                click.echo("Install with: pip install stageflow[visualization]")
                ctx.exit(1)

        else:  # text format
            output_text = _generate_text_visualization(process, include_details)

        # Output result
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_text)
            if verbose:
                click.echo(f"Visualization written to {output}")
        else:
            click.echo(output_text)

    except Exception as e:
        handle_error(e, verbose)
        ctx.exit(1)


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
                lines.append(f"{gate_prefix} Gate: {gate.name} ({gate.logic.value})")

                if gate.locks:
                    for k, lock in enumerate(gate.locks):
                        lock_prefix = "      └─" if k == len(gate.locks) - 1 else "      ├─"
                        lock_desc = f"{lock.property_path} {lock.lock_type.value}"
                        if lock.expected_value is not None:
                            lock_desc += f" {lock.expected_value}"
                        lines.append(f"{lock_prefix} {lock_desc}")

        lines.append("")

    return "\n".join(lines)
