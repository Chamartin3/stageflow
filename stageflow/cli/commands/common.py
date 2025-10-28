"""Common utilities shared across CLI commands."""

import typer

from stageflow.cli.utils import show_progress
from stageflow.manager import ManagerConfig, ProcessRegistry
from stageflow.schema import load_process_graceful


class SourceType:
    """Source type for process loading."""

    FILE = "file"
    REGISTRY = "registry"


def detect_source_type(source: str) -> str:
    """Detect whether source is file path or registry reference."""
    if source.startswith("@"):
        return SourceType.REGISTRY
    else:
        return SourceType.FILE


def load_process_from_source(source: str, verbose: bool = False):
    """Load process from either file or registry source."""
    source_type = detect_source_type(source)

    if source_type == SourceType.FILE:
        if verbose:
            show_progress(f"Loading process from file: {source}", verbose=True)
        return load_process_graceful(source)

    elif source_type == SourceType.REGISTRY:
        process_name = source[1:]  # Remove @ prefix
        if verbose:
            show_progress(
                f"Loading process from registry: {process_name}", verbose=True
            )

        try:
            config = ManagerConfig.from_env()
            registry = ProcessRegistry(config)

            process_file_path = registry.get_process_file_path(process_name)
            if not process_file_path or not process_file_path.exists():
                raise typer.BadParameter(
                    f"Process '{process_name}' not found in registry"
                )

            return load_process_graceful(process_file_path)
        except Exception as e:
            raise typer.BadParameter(
                f"Failed to load process from registry: {e}"
            ) from e
