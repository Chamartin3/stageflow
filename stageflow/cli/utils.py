"""CLI utilities for StageFlow."""

import json

import click

from stageflow.core.result import StatusResult


def handle_error(error: Exception, verbose: bool = False):
    """
    Handle and display CLI errors consistently.

    Args:
        error: Exception that occurred
        verbose: Whether to show detailed error information
    """
    if verbose:
        import traceback

        click.echo(f"❌ Error: {str(error)}", err=True)
        click.echo("Traceback:", err=True)
        click.echo(traceback.format_exc(), err=True)
    else:
        click.echo(f"❌ Error: {str(error)}", err=True)
        click.echo("Use --verbose for detailed error information", err=True)


def format_result(result: StatusResult, output_format: str, verbose: bool = False) -> str:
    """
    Format evaluation result for output.

    Args:
        result: StatusResult to format
        output_format: Output format (text, json, yaml)
        verbose: Whether to include verbose details

    Returns:
        Formatted result string
    """
    if output_format == "json":
        return _format_json_result(result, verbose)
    elif output_format == "yaml":
        return _format_yaml_result(result, verbose)
    else:
        return _format_text_result(result, verbose)


def _format_text_result(result: StatusResult, verbose: bool) -> str:
    """Format result as human-readable text."""
    lines = []

    # Status header
    state_emoji = {
        "scoping": "🔍",
        "fulfilling": "⚠️",
        "qualifying": "✅",
        "awaiting": "⏳",
        "advancing": "➡️",
        "regressing": "⬅️",
        "completed": "🎉",
    }

    emoji = state_emoji.get(result.state.value, "•")
    lines.append(f"{emoji} State: {result.state.value.upper()}")

    # Stage information
    if result.current_stage:
        lines.append(f"📍 Current Stage: {result.current_stage}")

    if result.proposed_stage and result.proposed_stage != result.current_stage:
        lines.append(f"🎯 Proposed Stage: {result.proposed_stage}")

    # Actions
    if result.actions:
        lines.append("\n📋 Actions:")
        for action in result.actions:
            lines.append(f"   • {action}")

    # Errors
    if result.errors:
        lines.append("\n❌ Errors:")
        for error in result.errors:
            lines.append(f"   • {error}")

    # Metadata (if verbose)
    if verbose and result.metadata:
        lines.append("\n📊 Metadata:")
        for key, value in result.metadata.items():
            lines.append(f"   {key}: {value}")

    return "\n".join(lines)


def _format_json_result(result: StatusResult, verbose: bool) -> str:
    """Format result as JSON."""
    data = {
        "state": result.state.value,
        "current_stage": result.current_stage,
        "proposed_stage": result.proposed_stage,
        "actions": result.actions,
        "errors": result.errors,
    }

    if verbose:
        data["metadata"] = result.metadata

    return json.dumps(data, indent=2)


def _format_yaml_result(result: StatusResult, verbose: bool) -> str:
    """Format result as YAML."""
    try:
        import io

        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        yaml.default_flow_style = False

        data = {
            "state": result.state.value,
            "current_stage": result.current_stage,
            "proposed_stage": result.proposed_stage,
            "actions": result.actions,
            "errors": result.errors,
        }

        if verbose:
            data["metadata"] = result.metadata

        stream = io.StringIO()
        yaml.dump(data, stream)
        return stream.getvalue()

    except ImportError:
        # Fallback to JSON if YAML not available
        return _format_json_result(result, verbose)


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Confirmation message
        default: Default choice if user just presses enter

    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = click.prompt(message + suffix, default="", show_default=False)

    if not response:
        return default

    return response.lower().startswith("y")


def validate_file_path(path: str, must_exist: bool = True) -> bool:
    """
    Validate file path.

    Args:
        path: File path to validate
        must_exist: Whether file must exist

    Returns:
        True if path is valid
    """
    from pathlib import Path

    try:
        p = Path(path)
        if must_exist:
            return p.exists() and p.is_file()
        else:
            return p.parent.exists() or p.parent == Path(".")
    except (OSError, ValueError):
        return False
