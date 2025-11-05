"""CLI utilities package.

This package provides utilities for CLI commands including:
- CLIContext: Context management for commands
- Formatters: Process, Evaluation, and LoadResult formatters
- Decorators: Error handling decorators
- Helper functions: File writing and process description building
"""

from pathlib import Path

import click

from stageflow.cli.utils.context import CLIContext
from stageflow.cli.utils.decorators import handle_cli_errors
from stageflow.cli.utils.format import (
    ActionInfo,
    ConsistencyIssue,
    EvaluationData,
    EvaluationFormatter,
    EvaluationJsonResult,
    GateResultInfo,
    LoadResultFormatter,
    ProcessDescription,
    ProcessFormatter,
    StageInfo,
)
from stageflow.models import ActionDefinition

__all__ = [
    # Context
    "CLIContext",
    # Formatters
    "ProcessFormatter",
    "EvaluationFormatter",
    "LoadResultFormatter",
    # TypedDicts for type hints
    "ProcessDescription",
    "StageInfo",
    "ConsistencyIssue",
    "ActionDefinition",  # From models
    "ActionInfo",
    "EvaluationData",
    "EvaluationJsonResult",
    "GateResultInfo",
    # Decorators
    "handle_cli_errors",
    # Helper functions
    "safe_write_file",
]


def safe_write_file(file_path: Path, content: str, verbose: bool = False) -> None:
    """Safely write content to file with error handling.

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
