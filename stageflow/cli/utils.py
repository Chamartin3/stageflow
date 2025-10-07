"""CLI utilities for StageFlow."""

import json
from pathlib import Path
from typing import Any

import click


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
    click.echo(f"✅ {message}")
