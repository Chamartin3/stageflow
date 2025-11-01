"""Common utilities shared across CLI commands."""

import typer

from stageflow.cli.utils import show_progress
from stageflow.process import Process
from stageflow.schema import ProcessLoader, ProcessSourceType, ProcessWithErrors


def load_process_from_source(
    source: str, verbose: bool = False
) -> Process | ProcessWithErrors:
    """
    Load process from either file or registry source.

    This is a convenience wrapper around ProcessLoader for CLI commands
    that need to handle typer-specific error reporting.

    Args:
        source: File path or registry reference (prefixed with '@')
        verbose: Whether to show progress messages

    Returns:
        Process instance if valid, ProcessWithErrors if invalid

    Raises:
        typer.BadParameter: If loading fails
    """
    try:
        # Use verbose mode with custom progress handler
        if verbose:
            loader = VerboseProcessLoader()
        else:
            loader = ProcessLoader()

        return loader.load(source, graceful=True)

    except Exception as e:
        raise typer.BadParameter(f"Failed to load process: {e}") from e


class VerboseProcessLoader(ProcessLoader):
    """ProcessLoader subclass that integrates with CLI's rich formatting."""

    def __init__(self):
        super().__init__(verbose=True)

    def _show_progress(self, message: str) -> None:
        """Override to use CLI's show_progress with rich formatting."""
        show_progress(message, verbose=True)


def detect_source_type(source: str) -> ProcessSourceType:
    """
    Detect whether source is file path or registry reference.

    Args:
        source: Source string to analyze

    Returns:
        ProcessSourceType enum value (FILE or REGISTRY)
    """
    loader = ProcessLoader()
    return loader.detect_source_type(source)
