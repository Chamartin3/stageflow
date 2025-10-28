"""CLI utilities for StageFlow."""

from pathlib import Path

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

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        if verbose:
            click.echo(f"Successfully wrote {len(content)} characters to {file_path}")

    except PermissionError as e:
        raise click.ClickException(f"Permission denied writing to {file_path}") from e

    except OSError as e:
        raise click.ClickException(f"Failed to write to {file_path}: {e}") from e

    except Exception as e:
        if verbose:
            import traceback

            click.echo(f"Unexpected error writing to {file_path}:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Failed to write file {file_path}: {e}") from e


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
