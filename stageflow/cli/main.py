"""Main CLI entry point for StageFlow."""

import json
from pathlib import Path

import click

from stageflow.cli.utils import (
    handle_error,
    load_element_data,
    safe_write_file,
    show_progress,
    show_success,
)
from stageflow.element import DictElement
from stageflow.schema import load_process


@click.command()
@click.version_option(version="0.1.0", prog_name="stageflow")
@click.option(
    "--process", "-p",
    type=click.Path(exists=True, path_type=Path),
    help="Process file to load and validate (YAML/JSON)"
)
@click.option(
    "--elem", "-e",
    type=click.Path(exists=True, path_type=Path),
    help="Element file for evaluation (JSON)"
)
@click.option(
    "--stage", "-s",
    help="Stage where the element should be validated (optional)"
)
@click.option(
    "--view",
    is_flag=True,
    help="Create a visualization (mermaid by default)"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output file for visualization"
)
@click.option(
    "--json", "json_output",
    is_flag=True,
    help="Return response in JSON format (disables other output)"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(process: Path, elem: Path, stage: str, view: bool, output: Path, json_output: bool, verbose: bool):
    """
    StageFlow: A declarative multi-stage validation framework.

    Examples:
        stageflow -p process.yaml                          # Validate process
        stageflow -p process.yaml -e element.json          # Evaluate element
        stageflow -p process.yaml -e element.json -s start # Evaluate at stage
        stageflow -p process.yaml --view -o diagram.md     # Create visualization
        stageflow -p process.yaml --json                   # JSON output
    """

    if not process:
        if not json_output:
            click.echo("Error: Process file (-p) is required", err=True)
        else:
            click.echo(json.dumps({"error": "Process file (-p) is required"}))
        ctx = click.get_current_context()
        ctx.exit(1)

    try:
        # Load and validate process
        if not json_output and verbose:
            show_progress(f"Loading process from {process}", verbose=True)

        proc = load_process(str(process))

        if not json_output and verbose:
            show_progress("Process loaded successfully", verbose=True)

        # Handle visualization mode
        if view:
            return _handle_visualization(proc, output, json_output, verbose)

        # Handle element evaluation mode
        if elem:
            return _handle_evaluation(proc, elem, stage, json_output, verbose)

        # Default: Process validation and description
        return _handle_process_description(proc, json_output, verbose)

    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}))
        else:
            handle_error(e, verbose)
        ctx = click.get_current_context()
        ctx.exit(1)


def _build_process_description(process):
    """Build process description dictionary."""
    description = {
        "name": process.name,
        "description": getattr(process, 'description', ''),
        "initial_stage": process.initial_stage._id if process.initial_stage else None,
        "final_stage": process.final_stage._id if process.final_stage else None,
        "stages": []
    }

    # Check for consistency issues
    consistency_valid = process.checker.valid if hasattr(process, 'checker') and process.checker else True
    consistency_issues = []
    if hasattr(process, 'checker') and process.checker and hasattr(process.checker, 'issues'):
        consistency_issues = [{"type": str(issue.issue_type), "description": issue.description}
                             for issue in process.checker.issues]

    description["valid"] = consistency_valid
    description["consistency_issues"] = consistency_issues

    # Collect stages in order from initial to final
    visited = set()
    stage_order = []

    def collect_stages(stage_id):
        if stage_id in visited or not stage_id:
            return
        visited.add(stage_id)
        stage_order.append(stage_id)

        stage = process.get_stage(stage_id)
        if stage:
            for gate in stage.gates:
                if hasattr(gate, 'target_stage') and gate.target_stage:
                    collect_stages(gate.target_stage)

    # Start from initial stage
    if process.initial_stage:
        collect_stages(process.initial_stage._id)

    # Add remaining stages
    for stage in process.stages:
        if stage._id not in visited:
            stage_order.append(stage._id)

    # Build stage descriptions
    for stage_id in stage_order:
        stage = process.get_stage(stage_id)
        if stage:
            # Get possible target stages from gates (remove duplicates)
            target_stages = []
            for gate in stage.gates:
                if hasattr(gate, 'target_stage') and gate.target_stage:
                    if gate.target_stage not in target_stages:
                        target_stages.append(gate.target_stage)

            stage_info = {
                "id": stage._id,
                "name": stage.name,
                "expected_properties": list(stage._base_schema.keys()) if stage._base_schema else [],
                "gates": len(stage.gates),
                "target_stages": target_stages,
                "is_final": stage.is_final
            }
            description["stages"].append(stage_info)

    return description


def _handle_process_description(process, json_output: bool, verbose: bool):
    """Handle process validation and description output."""
    description = _build_process_description(process)

    if json_output:
        click.echo(json.dumps(description, indent=2))
    else:
        _print_process_description(description, process)


def _print_process_description(desc, process):
    """Print human-readable process description."""
    # Show process status with appropriate icon
    if desc['valid']:
        status_icon = "✅"
        status_text = "Valid"
    else:
        status_icon = "❌"
        status_text = "Invalid"

    click.echo(f"{status_icon} Process: {desc['name']} ({status_text})")
    if desc['description']:
        click.echo(f"   Description: {desc['description']}")
    click.echo(f"   Initial Stage: {desc['initial_stage']}")
    click.echo(f"   Final Stage: {desc['final_stage']}")
    click.echo(f"   Total Stages: {len(desc['stages'])}")
    click.echo()

    click.echo("Stages:")
    for i, stage in enumerate(desc['stages']):
        prefix = "└─" if i == len(desc['stages']) - 1 else "├─"
        final_marker = " (final)" if stage['is_final'] else ""

        # Show possible target stages instead of gate count
        if stage['target_stages']:
            targets_text = f" → {', '.join(stage['target_stages'])}"
        else:
            targets_text = ""

        click.echo(f"{prefix} {stage['name']}{targets_text}{final_marker}")

        if stage['expected_properties']:
            click.echo(f"   Expected properties: {', '.join(stage['expected_properties'])}")

    # Show consistency issues if any
    if desc['consistency_issues']:
        click.echo()
        click.echo("❌ Consistency Issues:")
        for issue in desc['consistency_issues']:
            click.echo(f"   • {issue['description']}")

        click.echo()
        click.echo("⚠️  This process is not valid for execution due to the above consistency issues.")


def _handle_evaluation(process, elem_path: Path, stage: str, json_output: bool, verbose: bool):
    """Handle element evaluation."""

    if not json_output and verbose:
        show_progress(f"Loading element from {elem_path}", verbose=True)

    # Load element
    element_data = load_element_data(elem_path, verbose)
    element = DictElement(element_data)

    if not json_output and verbose:
        show_progress("Evaluating element against process...", verbose=True)

    # Show process information first, even if evaluation will fail
    if not json_output:
        _print_process_info_for_evaluation(process)
        click.echo()

    # Evaluate
    try:
        result = process.evaluate(element, stage)
    except ValueError as e:
        if "inconsistent process configuration" in str(e):
            if json_output:
                process_description = _build_process_description(process)
                error_result = {
                    "process": process_description,
                    "error": str(e),
                    "evaluation": None
                }
                click.echo(json.dumps(error_result, indent=2))
            else:
                click.echo(f"❌ Error: {str(e)}")
                if verbose:
                    click.echo("Use --verbose for detailed error information")
            ctx = click.get_current_context()
            ctx.exit(1)
        else:
            raise

    if json_output:
        # Include process information in JSON output
        process_description = _build_process_description(process)
        json_result = {
            "process": process_description,
            "evaluation": {
                "stage": result['stage'],
                "status": result['stage_result'].status,
                "regression": result['regression'],
                "actions": [{"description": action.description, "type": action.action_type}
                           for action in result['stage_result'].sugested_action],
                "gate_results": {
                    gate_name: {
                        "passed": gate_result.success,
                        "success_rate": gate_result.success_rate,
                        "failed_locks": len(gate_result.failed),
                        "passed_locks": len(gate_result.passed)
                    }
                    for gate_name, gate_result in result['stage_result'].gate_results.items()
                }
            }
        }
        click.echo(json.dumps(json_result, indent=2))
    else:
        # Human-readable output: process info already shown, just show evaluation result
        _print_evaluation_result(result)


def _print_process_info_for_evaluation(process):
    """Print concise process information before element evaluation."""
    description = _build_process_description(process)

    # Show process status with appropriate icon
    if description['valid']:
        status_icon = "✅"
        status_text = "Valid"
    else:
        status_icon = "❌"
        status_text = "Invalid"

    click.echo("📋 Process Information")
    click.echo(f"{status_icon} Process: {description['name']} ({status_text})")
    if description['description']:
        click.echo(f"   Description: {description['description']}")
    click.echo(f"   Initial Stage: {description['initial_stage']}")
    click.echo(f"   Final Stage: {description['final_stage']}")
    click.echo(f"   Total Stages: {len(description['stages'])}")
    click.echo()

    click.echo("Available Stages:")
    for i, stage in enumerate(description['stages']):
        prefix = "└─" if i == len(description['stages']) - 1 else "├─"
        final_marker = " (final)" if stage['is_final'] else ""

        # Show possible target stages
        if stage['target_stages']:
            targets_text = f" → {', '.join(stage['target_stages'])}"
        else:
            targets_text = ""

        click.echo(f"{prefix} {stage['name']}{targets_text}{final_marker}")

        if stage['expected_properties']:
            click.echo(f"   Expected properties: {', '.join(stage['expected_properties'])}")

    # Show consistency issues if any
    if description['consistency_issues']:
        click.echo()
        click.echo("❌ Consistency Issues:")
        for issue in description['consistency_issues']:
            click.echo(f"   • {issue['description']}")


def _print_evaluation_result(result):
    """Print human-readable evaluation result."""
    stage_result = result['stage_result']
    status = stage_result.status
    current_stage = result['stage']

    # Status with emoji
    status_emoji = {
        'ready': '✅',
        'action_required': '⚠️',
        'invalid_schema': '❌'
    }.get(status, '❓')

    click.echo(f"{status_emoji} Evaluation Result")
    click.echo(f"   Current Stage: {current_stage}")
    click.echo(f"   Status: {status}")

    # Show actions if any
    actions = stage_result.sugested_action
    if actions:
        click.echo("   Required Actions:")
        for action in actions:
            click.echo(f"     • {action.description}")

    # Show next stage if ready for transition - we need to get this from gates
    if status == 'READY_FOR_TRANSITION':
        # Find gates that passed to determine next stages
        passed_gates = [gate_name for gate_name, gate_result in stage_result.gate_results.items()
                       if gate_result.passed]
        if passed_gates:
            click.echo(f"   Passed Gate(s): {', '.join(passed_gates)}")


def _handle_visualization(process, output: Path, json_output: bool, verbose: bool):
    """Handle visualization generation."""
    from stageflow.visualization.mermaid import MermaidDiagramGenerator

    if not output:
        error_msg = "Output file (-o) is required for visualization"
        if json_output:
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(f"Error: {error_msg}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

    if not json_output and verbose:
        show_progress("Generating mermaid visualization...", verbose=True)

    try:
        # Use the visualization module
        generator = MermaidDiagramGenerator()
        diagram = generator.generate_process_diagram(process, style="overview")

        # Ensure .md extension for mermaid
        if not output.suffix:
            output = output.with_suffix(".md")

        safe_write_file(output, diagram, verbose)

        if json_output:
            click.echo(json.dumps({"visualization": str(output), "format": "mermaid"}))
        else:
            show_success(f"Mermaid visualization written to {output}")

    except Exception as e:
        error_msg = f"Visualization generation failed: {str(e)}"
        if json_output:
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(f"Error: {error_msg}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)




def main():
    """Main entry point for the CLI."""
    cli()
