"""
Manager Utilities Module

Provides utility functions for CLI and manager operations.
"""

import warnings
from pathlib import Path
from typing import Any

from stageflow.process import Process
from stageflow.templates import ProcessTemplate, generate_process_from_template


def backup_process_file(source_path: Path, backup_dir: Path, process_name: str) -> Path:
    """
    Create a backup of a process file.

    Args:
        source_path: Path to the source process file
        backup_dir: Directory to store backups
        process_name: Name of the process

    Returns:
        Path to the created backup file
    """
    # TODO: Implement process file backup
    raise NotImplementedError("backup_process_file is not yet implemented")


def cleanup_old_backups(backup_dir: Path, process_name: str, max_backups: int) -> int:
    """
    Clean up old backup files, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backup files
        process_name: Name of the process
        max_backups: Maximum number of backups to keep

    Returns:
        Number of backup files removed
    """
    # TODO: Implement backup cleanup
    raise NotImplementedError("cleanup_old_backups is not yet implemented")


def validate_process_name(name: str) -> bool:
    """
    Validate that a process name is safe for use as a filename.

    Args:
        name: Process name to validate

    Returns:
        True if name is valid, False otherwise
    """
    # TODO: Implement process name validation
    raise NotImplementedError("validate_process_name is not yet implemented")


def sanitize_process_name(name: str) -> str:
    """
    Sanitize a process name to make it safe for use as a filename.

    Args:
        name: Process name to sanitize

    Returns:
        Sanitized process name
    """
    # TODO: Implement process name sanitization
    raise NotImplementedError("sanitize_process_name is not yet implemented")


def detect_file_format(path: Path) -> str:
    """
    Detect the format of a process file based on its extension and content.

    Args:
        path: Path to the process file

    Returns:
        Detected format ('yaml' or 'json')
    """
    # TODO: Implement file format detection
    raise NotImplementedError("detect_file_format is not yet implemented")


def get_process_files(directory: Path, recursive: bool = False) -> list[Path]:
    """
    Get all process files in a directory.

    Args:
        directory: Directory to search
        recursive: Whether to search recursively

    Returns:
        List of process file paths
    """
    # TODO: Implement process file discovery
    raise NotImplementedError("get_process_files is not yet implemented")


def format_process_summary(process: Process) -> dict[str, Any]:
    """
    Format a process summary for display.

    Args:
        process: Process to summarize

    Returns:
        Formatted summary dictionary
    """
    # TODO: Implement process summary formatting
    raise NotImplementedError("format_process_summary is not yet implemented")


def format_validation_results(results: dict[str, Any]) -> str:
    """
    Format validation results for human-readable display.

    Args:
        results: Validation results dictionary

    Returns:
        Formatted validation results string
    """
    # TODO: Implement validation results formatting
    raise NotImplementedError("format_validation_results is not yet implemented")


def generate_timestamp() -> str:
    """
    Generate a timestamp string for file naming.

    Returns:
        Timestamp string in ISO format suitable for filenames
    """
    # TODO: Implement timestamp generation
    raise NotImplementedError("generate_timestamp is not yet implemented")


def check_file_permissions(path: Path, required_permissions: str = "rw") -> bool:
    """
    Check if a file has the required permissions.

    Args:
        path: Path to the file
        required_permissions: Required permissions ('r', 'w', 'rw')

    Returns:
        True if file has required permissions, False otherwise
    """
    # TODO: Implement permission checking
    raise NotImplementedError("check_file_permissions is not yet implemented")


def ensure_directory_exists(path: Path, create_parents: bool = True) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path
        create_parents: Whether to create parent directories

    Returns:
        True if directory exists or was created, False otherwise
    """
    # TODO: Implement directory creation
    raise NotImplementedError("ensure_directory_exists is not yet implemented")


def get_file_size_human(path: Path) -> str:
    """
    Get human-readable file size.

    Args:
        path: Path to the file

    Returns:
        Human-readable file size string
    """
    # TODO: Implement human-readable file size
    raise NotImplementedError("get_file_size_human is not yet implemented")


def compare_process_versions(process1: Process, process2: Process) -> dict[str, Any]:
    """
    Compare two process versions and return differences.

    Args:
        process1: First process
        process2: Second process

    Returns:
        Dictionary containing comparison results
    """
    # TODO: Implement process comparison
    raise NotImplementedError("compare_process_versions is not yet implemented")


# ============================================================================
# DEPRECATED: Template functionality has moved to stageflow.templates module
# ============================================================================
# The following constants and functions are deprecated and maintained only
# for backward compatibility. Use the new stageflow.templates module instead:
#
#   from stageflow.templates import ProcessTemplate, generate_process_from_template
#
# Migration examples:
#   OLD: generate_default_process_schema("myprocess", "basic")
#   NEW: generate_process_from_template("myprocess", ProcessTemplate.BASIC)
#
#   OLD: if template in PROCESS_TEMPLATES:
#   NEW: if ProcessTemplate.is_valid(template):
# ============================================================================

# Deprecated constant - use ProcessTemplate.get_default().value instead
DEFAULT_TEMPLATE = "basic"

# Deprecated constant - use ProcessTemplate.list_templates() instead
PROCESS_TEMPLATES = {
    template.value: f"Template '{template.value}' (use stageflow.templates.ProcessTemplate instead)"
    for template in ProcessTemplate
}


def generate_default_process_schema(
    process_name: str, template_type: str = DEFAULT_TEMPLATE
) -> dict[str, Any]:
    """
    Generate a default process schema based on template type.

    .. deprecated::
        Use :func:`stageflow.templates.generate_process_from_template` instead.
        This function is maintained for backward compatibility only.

    Args:
        process_name: Name for the new process
        template_type: Template type name (default: "basic")

    Returns:
        Complete process schema dictionary

    Example:
        >>> # Deprecated usage
        >>> schema = generate_default_process_schema("myprocess", "basic")
        >>>
        >>> # New recommended usage
        >>> from stageflow.templates import generate_process_from_template, ProcessTemplate
        >>> schema = generate_process_from_template("myprocess", ProcessTemplate.BASIC)
    """
    warnings.warn(
        "generate_default_process_schema is deprecated. "
        "Use stageflow.templates.generate_process_from_template instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    return generate_process_from_template(process_name, template_type)
