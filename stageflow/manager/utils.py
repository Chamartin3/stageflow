"""
Manager Utilities Module

Provides utility functions for CLI and manager operations.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from stageflow.process import Process

if TYPE_CHECKING:
    from .manager import ProcessManager


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
    pass


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
    pass


def validate_process_name(name: str) -> bool:
    """
    Validate that a process name is safe for use as a filename.

    Args:
        name: Process name to validate

    Returns:
        True if name is valid, False otherwise
    """
    # TODO: Implement process name validation
    pass


def sanitize_process_name(name: str) -> str:
    """
    Sanitize a process name to make it safe for use as a filename.

    Args:
        name: Process name to sanitize

    Returns:
        Sanitized process name
    """
    # TODO: Implement process name sanitization
    pass


def detect_file_format(path: Path) -> str:
    """
    Detect the format of a process file based on its extension and content.

    Args:
        path: Path to the process file

    Returns:
        Detected format ('yaml' or 'json')
    """
    # TODO: Implement file format detection
    pass


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
    pass


def format_process_summary(process: Process) -> dict[str, Any]:
    """
    Format a process summary for display.

    Args:
        process: Process to summarize

    Returns:
        Formatted summary dictionary
    """
    # TODO: Implement process summary formatting
    pass


def format_validation_results(results: dict[str, Any]) -> str:
    """
    Format validation results for human-readable display.

    Args:
        results: Validation results dictionary

    Returns:
        Formatted validation results string
    """
    # TODO: Implement validation results formatting
    pass


def generate_timestamp() -> str:
    """
    Generate a timestamp string for file naming.

    Returns:
        Timestamp string in ISO format suitable for filenames
    """
    # TODO: Implement timestamp generation
    pass


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
    pass


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
    pass


def get_file_size_human(path: Path) -> str:
    """
    Get human-readable file size.

    Args:
        path: Path to the file

    Returns:
        Human-readable file size string
    """
    # TODO: Implement human-readable file size
    pass


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
    pass


# CLI Management Utility Functions
# These functions provide the exact interface specified in the proposal (lines 418-640)

class OperationResultType(StrEnum):
    """Standard operation result types with default messages"""
    SUCCESS = "success"
    NO_CHANGES = "no_changes"
    NOT_FOUND = "not_found"
    INVALID_JSON = "invalid_json"
    INVALID_CONFIG = "invalid_config"
    CONSISTENCY_FAILED = "consistency_failed"
    OPERATION_FAILED = "operation_failed"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class ManageOperationResult:
    """Simplified operation result with default messages"""
    result_type: OperationResultType
    data: Any = None
    custom_message: str = None

    @property
    def success(self) -> bool:
        """Check if operation was successful"""
        return self.result_type in [OperationResultType.SUCCESS, OperationResultType.NO_CHANGES]

    @property
    def message(self) -> str:
        """Get formatted message with context"""
        if self.custom_message:
            return self.custom_message

        # Default messages based on result type
        messages = {
            OperationResultType.SUCCESS: "Operation completed successfully",
            OperationResultType.NO_CHANGES: "No changes to save",
            OperationResultType.NOT_FOUND: "Process not found",
            OperationResultType.INVALID_JSON: "Invalid JSON configuration",
            OperationResultType.INVALID_CONFIG: "Invalid stage configuration",
            OperationResultType.CONSISTENCY_FAILED: "Process consistency check failed",
            OperationResultType.OPERATION_FAILED: "Operation failed",
            OperationResultType.VALIDATION_FAILED: "Validation failed"
        }
        return messages.get(self.result_type, "Unknown result")

    def with_context(self, context: str) -> str:
        """Get message with additional context"""
        base_message = self.custom_message or self.message
        return f"{base_message}: {context}" if context else base_message


def list_all_processes(manager) -> ManageOperationResult:
    """List all available processes"""
    try:
        processes = manager.list_processes()
        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data=processes,
            custom_message=f"Found {len(processes)} processes"
        )
    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Failed to list processes: {e}"
        )


def sync_all_processes(manager) -> ManageOperationResult:
    """Sync all modified processes"""
    try:
        results = manager.sync_all()
        if not results:
            return ManageOperationResult(
                result_type=OperationResultType.NO_CHANGES,
                data={},
                custom_message="No processes have pending changes"
            )

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        result_type = OperationResultType.SUCCESS if success_count == total_count else OperationResultType.OPERATION_FAILED

        return ManageOperationResult(
            result_type=result_type,
            data=results,
            custom_message=f"Synced {success_count}/{total_count} processes"
        )
    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Failed to sync processes: {e}"
        )


def add_stage_to_process(manager, process_name: str, stage_config_json: str) -> ManageOperationResult:
    """Add stage to specified process"""
    try:
        # Check if process exists via manager (which uses registry)
        if not manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.NOT_FOUND,
                custom_message=f"Process '{process_name}' not found"
            )

        # Parse JSON configuration
        try:
            config = json.loads(stage_config_json)
        except json.JSONDecodeError:
            return ManageOperationResult(result_type=OperationResultType.INVALID_JSON)

        # Validate stage configuration
        if 'name' not in config:
            return ManageOperationResult(
                result_type=OperationResultType.INVALID_CONFIG,
                custom_message="Stage configuration must include 'name' field"
            )

        stage_id = config['name']

        # Get editor and add stage (manager loads via registry)
        editor = manager.edit_process(process_name)
        add_result = editor.add_stage(stage_id, config)

        # Check if editor operation failed
        if add_result is False:
            return ManageOperationResult(
                result_type=OperationResultType.CONSISTENCY_FAILED,
                custom_message=f"Failed to add stage '{stage_id}' to '{process_name}'"
            )

        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data={"stage_id": stage_id, "process_name": process_name},
            custom_message=f"Stage '{stage_id}' added to '{process_name}' (not saved)"
        )

    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error adding stage: {e}"
        )


def remove_stage_from_process(manager, process_name: str, stage_name: str) -> ManageOperationResult:
    """Remove stage from specified process"""
    try:
        # Check if process exists via manager (which uses registry)
        if not manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.NOT_FOUND,
                custom_message=f"Process '{process_name}' not found"
            )

        # Get editor (manager loads via registry)
        editor = manager.edit_process(process_name)
        remove_result = editor.remove_stage(stage_name)

        # Check if editor operation failed
        if remove_result is False:
            return ManageOperationResult(
                result_type=OperationResultType.CONSISTENCY_FAILED,
                custom_message=f"Failed to remove stage '{stage_name}' from '{process_name}'"
            )

        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data={"stage_name": stage_name, "process_name": process_name},
            custom_message=f"Stage '{stage_name}' removed from '{process_name}' (not saved)"
        )
    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error removing stage: {e}"
        )


def sync_process(manager, process_name: str) -> ManageOperationResult:
    """Sync specific process to file via registry"""
    try:
        # Check if process exists via manager (which uses registry)
        if not manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.NOT_FOUND,
                custom_message=f"Process '{process_name}' not found"
            )

        # Check if there are changes before syncing
        modified_processes = manager.get_modified_processes()
        has_changes = process_name in modified_processes

        # If no changes, return NO_CHANGES immediately
        if not has_changes:
            return ManageOperationResult(
                result_type=OperationResultType.NO_CHANGES,
                data={"process_name": process_name},
                custom_message=f"No changes to save for '{process_name}'"
            )

        # Manager handles sync via registry
        sync_result = manager.sync(process_name)
        if sync_result:
            return ManageOperationResult(
                result_type=OperationResultType.SUCCESS,
                data={"process_name": process_name},
                custom_message=f"Process '{process_name}' saved"
            )
        else:
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message=f"Failed to sync '{process_name}'"
            )
    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error syncing process: {e}"
        )


def create_new_process(manager: "ProcessManager", process_name: str, process_definition_json: str) -> ManageOperationResult:
    """Create a new process from JSON definition"""
    try:
        # Check if process already exists
        if manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message=f"Process '{process_name}' already exists"
            )

        # Parse JSON definition
        try:
            definition = json.loads(process_definition_json)
        except json.JSONDecodeError:
            return ManageOperationResult(result_type=OperationResultType.INVALID_JSON)

        # Validate required fields
        if 'name' not in definition:
            definition['name'] = process_name

        if 'stages' not in definition:
            return ManageOperationResult(
                result_type=OperationResultType.INVALID_CONFIG,
                custom_message="Process definition must include 'stages' field"
            )

        # Create the new process through the manager (it handles validation)
        manager.create_process(process_name, definition)

        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data={"process_name": process_name, "stages": len(definition['stages'])},
            custom_message=f"Process '{process_name}' created with {len(definition['stages'])} stages"
        )

    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error creating process: {e}"
        )


def validate_process_operations(process_name: str | None, add_stage: str | None,
                              remove_stage: str | None, sync_flag: bool,
                              create_definition: str | None = None,
                              use_default_schema: bool = False,
                              create_default: bool = False,
                              edit_process: bool = False,
                              create_flag: bool = False) -> ManageOperationResult:
    """Validate that process-specific operations have required --process flag"""
    process_specific_ops = [add_stage, remove_stage, sync_flag]
    has_process_ops = any(op for op in process_specific_ops if op)

    # Create operation requires --process flag
    if create_definition and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required when using --create"
        )

    # Default schema operation requires --process flag
    if use_default_schema and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required when using --default-schema"
        )

    # Create default operation requires --process flag
    if create_default and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required when using --create-default"
        )

    # Edit operation requires --process flag
    if edit_process and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required when using --edit"
        )

    # Create flag operation requires --process flag
    if create_flag and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required when using --create"
        )

    if has_process_ops and not process_name:
        return ManageOperationResult(
            result_type=OperationResultType.VALIDATION_FAILED,
            custom_message="--process required for process-specific operations"
        )

    return ManageOperationResult(result_type=OperationResultType.SUCCESS)


def generate_default_process_schema(process_name: str, template_type: str = "basic") -> dict[str, Any]:
    """Generate a default process schema based on template type"""

    templates = {
        "basic": {
            "name": process_name,
            "description": f"Basic {process_name} workflow",
            "stages": {
                "start": {
                    "name": "Start",
                    "description": "Initial stage",
                    "schema": {
                        "required_fields": ["id"]
                    },
                    "gates": [{
                        "name": "to_end",
                        "description": "Proceed to end",
                        "target_stage": "end",
                        "locks": [{"exists": "id"}]
                    }]
                },
                "end": {
                    "name": "End",
                    "description": "Final stage",
                    "schema": {
                        "required_fields": []
                    },
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "start",
            "final_stage": "end"
        },

        "approval": {
            "name": process_name,
            "description": f"{process_name} approval workflow",
            "stages": {
                "submitted": {
                    "name": "Submitted",
                    "description": "Content submitted for approval",
                    "schema": {
                        "required_fields": ["title", "content", "author"]
                    },
                    "gates": [{
                        "name": "review_complete",
                        "description": "Review completed",
                        "target_stage": "completed",
                        "locks": [
                            {"exists": "review.status"},
                            {"exists": "review.reviewer"}
                        ]
                    }]
                },
                "completed": {
                    "name": "Review Completed",
                    "description": "Review process completed",
                    "schema": {
                        "required_fields": ["review.status", "review.reviewer", "completed_at"]
                    },
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "submitted",
            "final_stage": "completed"
        },

        "onboarding": {
            "name": process_name,
            "description": f"{process_name} user onboarding workflow",
            "stages": {
                "registration": {
                    "name": "Registration",
                    "description": "User registration stage",
                    "schema": {
                        "required_fields": ["email", "password"]
                    },
                    "gates": [{
                        "name": "email_verified",
                        "description": "Email verification completed",
                        "target_stage": "profile_setup",
                        "locks": [
                            {"exists": "email"},
                            {"exists": "email_verified_at"}
                        ]
                    }]
                },
                "profile_setup": {
                    "name": "Profile Setup",
                    "description": "Complete user profile",
                    "schema": {
                        "required_fields": ["profile.first_name", "profile.last_name"]
                    },
                    "gates": [{
                        "name": "profile_complete",
                        "description": "Profile completed",
                        "target_stage": "active",
                        "locks": [
                            {"exists": "profile.first_name"},
                            {"exists": "profile.last_name"}
                        ]
                    }]
                },
                "active": {
                    "name": "Active User",
                    "description": "Active user account",
                    "schema": {
                        "required_fields": ["activated_at"]
                    },
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "registration",
            "final_stage": "active"
        }
    }

    return templates.get(template_type, templates["basic"])


def create_process_with_default_schema(manager: "ProcessManager", process_name: str, template_type: str = "basic") -> ManageOperationResult:
    """Create a new process using a default schema template"""
    try:
        # Check if process already exists
        if manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message=f"Process '{process_name}' already exists"
            )

        # Generate default schema
        schema = generate_default_process_schema(process_name, template_type)

        # Create the process
        manager.create_process(process_name, schema)

        stage_count = len(schema['stages'])
        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data={"process_name": process_name, "template_type": template_type, "stages": stage_count},
            custom_message=f"Process '{process_name}' created using '{template_type}' template with {stage_count} stages"
        )

    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error creating process with default schema: {e}"
        )


def edit_process_file(manager: "ProcessManager", process_name: str) -> ManageOperationResult:
    """Open a process file in the default text editor"""
    try:
        # Check if process exists
        if not manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.NOT_FOUND,
                custom_message=f"Process '{process_name}' not found"
            )

        # Get the process file path through the registry
        process_file_path = manager._registry.get_process_file_path(process_name)

        if not process_file_path.exists():
            return ManageOperationResult(
                result_type=OperationResultType.NOT_FOUND,
                custom_message=f"Process file for '{process_name}' not found at {process_file_path}"
            )

        # Determine which editor to use
        editor = os.environ.get('EDITOR') or os.environ.get('VISUAL')

        # Fallback editors in order of preference
        if not editor:
            fallback_editors = ['nano', 'vim', 'vi', 'emacs', 'code', 'gedit']
            for fallback in fallback_editors:
                try:
                    subprocess.run(['which', fallback], capture_output=True, check=True)
                    editor = fallback
                    break
                except subprocess.CalledProcessError:
                    continue

        if not editor:
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message="No text editor found. Set EDITOR environment variable or install nano/vim/vi"
            )

        # Open the file in the editor
        try:
            result = subprocess.run([editor, str(process_file_path)], check=True)

            return ManageOperationResult(
                result_type=OperationResultType.SUCCESS,
                data={"process_name": process_name, "editor": editor, "file_path": str(process_file_path)},
                custom_message=f"Opened '{process_name}' process file in {editor}"
            )

        except subprocess.CalledProcessError as e:
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message=f"Failed to open editor {editor}: {e}"
            )

        except KeyboardInterrupt:
            return ManageOperationResult(
                result_type=OperationResultType.SUCCESS,
                data={"process_name": process_name, "editor": editor},
                custom_message=f"Editor session completed for '{process_name}'"
            )

    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error opening process file for editing: {e}"
        )


def create_process_with_default(manager: "ProcessManager", process_name: str) -> ManageOperationResult:
    """Create a new process using the universal default schema"""
    try:
        # Check if process already exists
        if manager.process_exists(process_name):
            return ManageOperationResult(
                result_type=OperationResultType.OPERATION_FAILED,
                custom_message=f"Process '{process_name}' already exists"
            )

        # Generate default schema - use 'basic' as the universal default
        schema = generate_default_process_schema(process_name, "basic")

        # Create the process
        manager.create_process(process_name, schema)

        stage_count = len(schema['stages'])
        return ManageOperationResult(
            result_type=OperationResultType.SUCCESS,
            data={"process_name": process_name, "stages": stage_count},
            custom_message=f"Process '{process_name}' created with default schema ({stage_count} stages)"
        )

    except Exception as e:
        return ManageOperationResult(
            result_type=OperationResultType.OPERATION_FAILED,
            custom_message=f"Error creating process with default schema: {e}"
        )


