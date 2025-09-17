"""Process validation command for StageFlow CLI."""

from pathlib import Path

import click

from stageflow.cli.utils import handle_error
from stageflow.process.schema.loaders import load_process
from stageflow.process.validation import ProcessValidator


@click.command()
@click.argument("process_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["error", "warning", "info"]),
    default="warning",
    help="Minimum severity level to report",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (default: stdout)",
)
@click.pass_context
def validate_command(
    ctx: click.Context,
    process_file: Path,
    output_format: str,
    severity: str,
    output: Path,
):
    """
    Validate a process definition for structural and semantic issues.

    PROCESS_FILE: Path to process definition (YAML/JSON)

    Example:
        stageflow validate process.yaml --severity=warning
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Load process
        if verbose:
            click.echo(f"Loading process from {process_file}")
        process = load_process(str(process_file))

        # Validate process
        if verbose:
            click.echo("Validating process structure...")
        validator = ProcessValidator()
        result = validator.validate_process(process)

        # Filter by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        min_severity = severity_order[severity]

        filtered_messages = [
            msg
            for msg in result.messages
            if severity_order.get(msg.severity.value, 2) <= min_severity
        ]

        # Format output
        if output_format == "json":
            import json

            output_data = {
                "process_name": result.process_name,
                "summary": {
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "info": result.info,
                },
                "messages": [
                    {
                        "severity": msg.severity.value,
                        "code": msg.code,
                        "message": msg.message,
                        "location": msg.location,
                        "suggestion": msg.suggestion,
                    }
                    for msg in filtered_messages
                ],
            }
            output_text = json.dumps(output_data, indent=2)
        else:
            # Text format
            lines = []
            lines.append(f"Process: {result.process_name}")
            lines.append(f"Summary: {result.errors} errors, {result.warnings} warnings, {result.info} info")
            lines.append("")

            if not filtered_messages:
                lines.append("✅ No issues found at specified severity level")
            else:
                for msg in filtered_messages:
                    severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
                    icon = severity_icon.get(msg.severity.value, "•")
                    lines.append(f"{icon} {msg.severity.value.upper()}: {msg.message}")
                    lines.append(f"   Location: {msg.location}")
                    if msg.suggestion:
                        lines.append(f"   Suggestion: {msg.suggestion}")
                    lines.append("")

            output_text = "\n".join(lines)

        # Output result
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_text)
            if verbose:
                click.echo(f"Validation report written to {output}")
        else:
            click.echo(output_text)

        # Exit with error code if validation failed
        if result.has_errors:
            ctx.exit(1)

    except Exception as e:
        handle_error(e, verbose)
        ctx.exit(1)
