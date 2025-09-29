"""CLI utilities for StageFlow."""

import json
from pathlib import Path
from typing import Any

import click

from stageflow.process.result import StatusResult


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
    # Use StatusResult.to_dict() for proper serialization of complex objects
    data = result.to_dict()

    # Filter to include only relevant fields for JSON output
    filtered_data = {
        "state": data["state"],
        "current_stage": data["current_stage"],
        "proposed_stage": data["proposed_stage"],
        "actions": data["actions"],
        "errors": data["errors"],
    }

    if verbose:
        filtered_data["metadata"] = data["metadata"]

    return json.dumps(filtered_data, indent=2)


def _format_yaml_result(result: StatusResult, verbose: bool) -> str:
    """Format result as YAML."""
    try:
        import io

        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        yaml.default_flow_style = False

        # Use StatusResult.to_dict() for proper serialization of complex objects
        data = result.to_dict()

        # Filter to include only relevant fields for YAML output
        filtered_data = {
            "state": data["state"],
            "current_stage": data["current_stage"],
            "proposed_stage": data["proposed_stage"],
            "actions": data["actions"],
            "errors": data["errors"],
        }

        if verbose:
            filtered_data["metadata"] = data["metadata"]

        stream = io.StringIO()
        yaml.dump(filtered_data, stream)
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
    try:
        p = Path(path)
        if must_exist:
            return p.exists() and p.is_file()
        else:
            return p.parent.exists() or p.parent == Path(".")
    except (OSError, ValueError):
        return False


def load_element_data(file_path: Path, verbose: bool = False) -> dict[str, Any]:
    """
    Load element data from JSON file with enhanced error handling.

    Args:
        file_path: Path to JSON file
        verbose: Whether to show detailed error information

    Returns:
        Parsed element data

    Raises:
        click.ClickException: If file loading fails
    """
    if not file_path.exists():
        raise click.ClickException(f"Element file not found: {file_path}")

    if not file_path.is_file():
        raise click.ClickException(f"Element path is not a file: {file_path}")

    try:
        if verbose:
            click.echo(f"Loading element data from {file_path}")

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise click.ClickException(f"Element data must be a JSON object, got {type(data).__name__}")

        return data

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in element file {file_path}: {e.msg}"
        if hasattr(e, 'lineno'):
            error_msg += f" at line {e.lineno}, column {e.colno}"
        raise click.ClickException(error_msg)

    except UnicodeDecodeError as e:
        raise click.ClickException(f"Encoding error reading {file_path}: {e}")

    except PermissionError:
        raise click.ClickException(f"Permission denied reading {file_path}")

    except Exception as e:
        if verbose:
            import traceback
            click.echo(f"Unexpected error loading {file_path}:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Failed to load element file {file_path}: {e}")


def detect_file_format(file_path: Path) -> str:
    """
    Detect file format based on extension and content.

    Args:
        file_path: Path to file

    Returns:
        Format string ('yaml', 'json', or 'unknown')
    """
    suffix = file_path.suffix.lower()

    if suffix in ['.yml', '.yaml']:
        return 'yaml'
    elif suffix in ['.json']:
        return 'json'

    # Try to detect by content if extension is ambiguous
    try:
        with open(file_path, encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('{') or first_line.startswith('['):
                return 'json'
            elif first_line and not first_line.startswith('{'):
                return 'yaml'
    except Exception:
        pass

    return 'unknown'


def safe_write_file(file_path: Path, content: str, verbose: bool = False) -> None:
    """
    Safely write content to file with error handling.

    Args:
        file_path: Path to output file
        content: Content to write
        verbose: Whether to show detailed information

    Raises:
        click.ClickException: If writing fails
    """
    try:
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            click.echo(f"Writing output to {file_path}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if verbose:
            click.echo(f"Successfully wrote {len(content)} characters to {file_path}")

    except PermissionError:
        raise click.ClickException(f"Permission denied writing to {file_path}")

    except OSError as e:
        raise click.ClickException(f"Failed to write to {file_path}: {e}")

    except Exception as e:
        if verbose:
            import traceback
            click.echo(f"Unexpected error writing to {file_path}:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Failed to write file {file_path}: {e}")


def show_progress(message: str, verbose: bool = False) -> None:
    """
    Show progress message if verbose mode is enabled.

    Args:
        message: Progress message to show
        verbose: Whether verbose mode is enabled
    """
    if verbose:
        click.echo(f"🔄 {message}")


def show_success(message: str) -> None:
    """
    Show success message with green checkmark.

    Args:
        message: Success message to show
    """
    click.echo(f"✅ {message}", color="green")


def show_warning(message: str) -> None:
    """
    Show warning message with yellow warning icon.

    Args:
        message: Warning message to show
    """
    click.echo(f"⚠️  {message}", color="yellow")


def show_error(message: str) -> None:
    """
    Show error message with red X icon.

    Args:
        message: Error message to show
    """
    click.echo(f"❌ {message}", color="red", err=True)


def validate_output_format(format_name: str, supported_formats: list[str]) -> str:
    """
    Validate output format and provide suggestions if invalid.

    Args:
        format_name: Format name to validate
        supported_formats: List of supported format names

    Returns:
        Validated format name

    Raises:
        click.ClickException: If format is not supported
    """
    if format_name in supported_formats:
        return format_name

    # Provide suggestions for common typos
    suggestions = []
    for fmt in supported_formats:
        if format_name.lower() in fmt.lower() or fmt.lower() in format_name.lower():
            suggestions.append(fmt)

    error_msg = f"Unsupported format '{format_name}'. Supported formats: {', '.join(supported_formats)}"
    if suggestions:
        error_msg += f". Did you mean: {', '.join(suggestions)}?"

    raise click.ClickException(error_msg)
