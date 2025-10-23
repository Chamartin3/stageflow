"""
ProcessManager Module

Provides the main unified interface for process management operations.
Coordinates between ProcessRegistry and ProcessEditor instances.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from stageflow.process import Process

from .config import ManagerConfig
from .editor import ProcessEditor
from .registry import ProcessRegistry

logger = logging.getLogger(__name__)


class ProcessManagerError(Exception):
    """Base exception for ProcessManager operations"""
    pass


class ProcessNotFoundError(ProcessManagerError):
    """Raised when a requested process is not found"""
    pass


class ProcessValidationError(ProcessManagerError):
    """Raised when process validation fails"""
    pass


class ProcessSyncError(ProcessManagerError):
    """Raised when process synchronization fails"""
    pass


class ProcessManager:
    """
    Unified coordinator for StageFlow process management operations.

    The ProcessManager serves as the main interface for managing multiple processes,
    coordinating between the ProcessRegistry for file operations and ProcessEditor
    instances for active editing sessions.

    Key capabilities:
    - Load and manage multiple processes from directories
    - Create and manage ProcessEditor instances for active editing
    - Coordinate sync operations between registry and file system
    - Track which processes have pending changes
    - Provide batch operations for multiple processes
    """

    def __init__(self, config: ManagerConfig | None = None):
        """
        Initialize the ProcessManager.

        Args:
            config: Optional ManagerConfig instance. If None, defaults to
                   environment-based configuration.
        """
        self._config = config if config is not None else ManagerConfig.from_env()
        self._registry = ProcessRegistry(self._config)
        self._editors: dict[str, ProcessEditor] = {}
        self._pending_changes: set[str] = set()
        self._last_sync: datetime | None = None


    @property
    def config(self) -> ManagerConfig:
        """Get the current configuration."""
        return self._config

    @property
    def processes_directory(self) -> Path:
        """Get the processes directory path."""
        return self._config.processes_dir

    @property
    def pending_changes(self) -> set[str]:
        """Get set of process names with pending changes."""
        result = self._pending_changes.copy()
        # Also include processes with dirty editors
        for process_name, editor in self._editors.items():
            if editor.is_dirty:
                result.add(process_name)
        return result

    @property
    def last_sync_time(self) -> datetime | None:
        """Get the last synchronization timestamp."""
        return self._last_sync

    def list_processes(self, include_metadata: bool = False) -> list[str] | dict[str, Any]:
        """
        List all processes (both file-based and in-memory).

        Args:
            include_metadata: If True, return metadata for each process

        Returns:
            List of process names or dict with metadata if include_metadata=True
        """
        # Get processes from files
        file_based_processes = set()
        try:
            file_based_processes = set(self._registry.list_processes())
        except Exception:
            # If registry fails, just use empty set
            pass

        # Get processes from active editors (in-memory)
        in_memory_processes = set(self._editors.keys())

        # Combine both sets
        all_process_names = sorted(file_based_processes | in_memory_processes)

        if not include_metadata:
            return all_process_names

        result = {}
        for name in all_process_names:
            try:
                # Try to get metadata from registry first
                if name in file_based_processes:
                    metadata = self._registry.get_process_info(name)
                    result[name] = {
                        **metadata,
                        'has_pending_changes': name in self._pending_changes,
                        'has_active_editor': name in self._editors,
                        'is_file_based': True,
                    }
                else:
                    # In-memory only process
                    result[name] = {
                        'name': name,
                        'has_pending_changes': name in self._pending_changes,
                        'has_active_editor': name in self._editors,
                        'is_file_based': False,
                    }
            except Exception:
                # Skip processes that can't be accessed
                result[name] = {
                    'name': name,
                    'has_pending_changes': name in self._pending_changes,
                    'has_active_editor': name in self._editors,
                    'is_file_based': name in file_based_processes,
                }

        return result

    def process_exists(self, process_name: str) -> bool:
        """Check if a process exists (either in registry or in-memory)."""
        return self._registry.process_exists(process_name) or process_name in self._editors

    def edit_process(self, process_name: str) -> ProcessEditor:
        """Get or create a ProcessEditor for the specified process."""
        if process_name in self._editors:
            return self._editors[process_name]

        # Load process from registry
        process = self._registry.load_process(process_name)
        editor = ProcessEditor(process)
        self._editors[process_name] = editor
        # Don't add to pending changes until actual changes are made
        return editor

    def sync_all(self) -> dict[str, bool]:
        """Sync all modified processes to files."""
        results = {}
        for process_name in self._pending_changes.copy():
            results[process_name] = self.sync(process_name)
        return results

    def sync(self, process_name: str) -> bool:
        """Sync a specific process to file."""
        if process_name not in self._editors:
            return False

        editor = self._editors[process_name]

        # Check if there are actually changes to sync
        has_pending_changes = process_name in self._pending_changes
        has_editor_changes = editor.is_dirty

        if not has_pending_changes and not has_editor_changes:
            return False  # No changes to sync

        try:
            # Save the process using the registry
            self._registry.save_process(process_name, editor.process)
            self._pending_changes.discard(process_name)
            # Mark the editor as clean
            editor.mark_clean()
            self._last_sync = datetime.now()
            return True
        except Exception:
            return False

    def get_modified_processes(self) -> set[str]:
        """Get set of process names with pending changes."""
        result = self._pending_changes.copy()
        # Also include processes with dirty editors
        for process_name, editor in self._editors.items():
            if editor.is_dirty:
                result.add(process_name)
        return result

    def load_process(self, process_name: str) -> Process:
        """
        Load a process by name.

        Args:
            process_name: Name of the process to load

        Returns:
            Process instance

        Raises:
            ProcessNotFoundError: If process not found
        """
        try:
            return self._registry.load_process(process_name)
        except Exception as e:
            raise ProcessNotFoundError(f"Process '{process_name}' not found: {e}") from e

    def get_process_editor(self, process_name: str, create_if_missing: bool = False) -> ProcessEditor:
        """
        Get or create a ProcessEditor for the specified process.

        Args:
            process_name: Name of the process
            create_if_missing: If True, create editor if process doesn't exist

        Returns:
            ProcessEditor instance

        Raises:
            ProcessNotFoundError: If process not found and create_if_missing=False
        """
        if process_name in self._editors:
            return self._editors[process_name]

        # Load process or create new one
        try:
            process = self.load_process(process_name)
        except ProcessNotFoundError:
            if not create_if_missing:
                raise
            # For create_if_missing, we need a valid process, not None
            raise ProcessManagerError(f"Cannot create editor for non-existent process '{process_name}' - process creation not implemented in get_process_editor") from None

        editor = ProcessEditor(process)
        self._editors[process_name] = editor
        return editor

    def create_process(self, process_name: str, process_config: dict[str, Any],
                      save_immediately: bool = True) -> ProcessEditor:
        """
        Create a new process with the given configuration.

        Args:
            process_name: Name for the new process
            process_config: Process configuration dictionary
            save_immediately: If True, save to file immediately

        Returns:
            ProcessEditor instance for the new process

        Raises:
            ProcessManagerError: If process already exists or creation fails
        """
        if self._registry.process_exists(process_name):
            raise ProcessManagerError(f"Process '{process_name}' already exists")

        try:
            # Create process instance from config
            # Cast to ProcessDefinition for type checking
            from typing import cast

            from stageflow.process import ProcessDefinition
            process = Process(cast(ProcessDefinition, process_config))

            # Create editor
            editor = ProcessEditor(process)
            self._editors[process_name] = editor

            # Mark as having pending changes
            self._pending_changes.add(process_name)

            # Save immediately if requested
            if save_immediately:
                self.sync(process_name)

            logger.info(f"Created new process: {process_name}")
            return editor

        except Exception as e:
            logger.error(f"Failed to create process '{process_name}': {e}")
            raise ProcessManagerError(f"Process creation failed: {e}") from e

    def remove_process(self, process_name: str, delete_file: bool = True) -> bool:
        """
        Remove a process from the manager.

        Args:
            process_name: Name of the process to remove
            delete_file: If True, also delete the file from disk

        Returns:
            True if process was removed

        Raises:
            ProcessNotFoundError: If process not found
        """
        if not self._registry.process_exists(process_name):
            raise ProcessNotFoundError(f"Process '{process_name}' not found")

        try:
            # Close editor if active
            if process_name in self._editors:
                del self._editors[process_name]

            # Remove from pending changes
            self._pending_changes.discard(process_name)

            # Delete file if requested
            if delete_file:
                self._registry.delete_process(process_name)

            logger.info(f"Removed process: {process_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove process '{process_name}': {e}")
            raise ProcessManagerError(f"Process removal failed: {e}") from e

    def export_process(self, process_name: str, export_path: Path,
                      format_override: str | None = None) -> Path:
        """
        Export a process to an external file.

        Args:
            process_name: Name of the process to export
            export_path: Target file path for export
            format_override: Optional format override ('yaml' or 'json')

        Returns:
            Path to the exported file

        Raises:
            ProcessNotFoundError: If process not found
            ProcessManagerError: If export fails
        """
        if not self._registry.process_exists(process_name):
            raise ProcessNotFoundError(f"Process '{process_name}' not found")

        try:
            # Load the process
            process = self._registry.load_process(process_name)

            # Determine target format
            if format_override:
                target_format = format_override.lower()
            else:
                # Infer from file extension
                ext = export_path.suffix.lower()
                target_format = 'yaml' if ext in ['.yaml', '.yml'] else 'json'

            # Extract process data
            data_dict = self._registry._extract_process_data(process)

            # Ensure parent directory exists
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            import json

            from ruamel.yaml import YAML

            with open(export_path, 'w', encoding='utf-8') as f:
                if target_format == 'yaml':
                    yaml = YAML(typ='safe', pure=True)
                    yaml.preserve_quotes = True
                    yaml.indent(mapping=2, sequence=4, offset=2)
                    yaml.dump(data_dict, f)
                else:
                    json.dump(data_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported process '{process_name}' to {export_path}")
            return export_path

        except Exception as e:
            logger.error(f"Failed to export process '{process_name}': {e}")
            raise ProcessManagerError(f"Export failed: {e}") from e

    def import_process(self, import_path: Path, process_name: str | None = None,
                      overwrite: bool = False) -> str:
        """
        Import a process from an external file into the registry.

        Args:
            import_path: Path to the process file to import
            process_name: Optional name for the imported process (defaults to filename stem)
            overwrite: If True, overwrite existing process with same name

        Returns:
            Name of the imported process

        Raises:
            ProcessManagerError: If import fails or process already exists
        """
        if not import_path.exists():
            raise ProcessManagerError(f"Import file not found: {import_path}")

        try:
            # Determine process name
            target_name = process_name if process_name else import_path.stem

            # Check if process already exists
            if self._registry.process_exists(target_name) and not overwrite:
                raise ProcessManagerError(
                    f"Process '{target_name}' already exists. Use overwrite=True to replace it."
                )

            # Load process from external file
            from stageflow.schema import load_process
            process = load_process(import_path)

            # Save to registry
            self._registry.save_process(target_name, process)

            logger.info(f"Imported process '{target_name}' from {import_path}")
            return target_name

        except Exception as e:
            logger.error(f"Failed to import process from {import_path}: {e}")
            raise ProcessManagerError(f"Import failed: {e}") from e

    def has_pending_changes(self, process_name: str | None = None) -> bool | dict[str, bool]:
        """
        Check if processes have pending changes.

        Args:
            process_name: Specific process name to check, or None for all

        Returns:
            Boolean for specific process, or dict for all processes
        """
        if process_name is not None:
            # Check both pending changes and dirty editors
            if process_name in self._pending_changes:
                return True
            if process_name in self._editors and self._editors[process_name].is_dirty:
                return True
            return False

        # For all processes, check both pending changes and dirty editors
        result = {}
        for name in self._registry.list_processes():
            has_pending = name in self._pending_changes
            has_dirty_editor = name in self._editors and self._editors[name].is_dirty
            result[name] = has_pending or has_dirty_editor
        return result

    def reload_process(self, process_name: str, force: bool = False) -> bool:
        """
        Reload a process from disk, discarding any pending changes.

        Args:
            process_name: Name of the process to reload
            force: If True, reload even if there are pending changes

        Returns:
            True if reload was successful

        Raises:
            ProcessNotFoundError: If process file not found
            ProcessManagerError: If there are pending changes and force=False
        """
        if not force and process_name in self._pending_changes:
            raise ProcessManagerError(
                f"Process '{process_name}' has pending changes. Use force=True to discard them."
            )

        try:
            # Load process from file using registry
            process = self._registry.load_process(process_name)

            # Update editor if active
            if process_name in self._editors:
                self._editors[process_name] = ProcessEditor(process)

            # Clear pending changes
            self._pending_changes.discard(process_name)

            logger.info(f"Reloaded process '{process_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to reload process '{process_name}': {e}")
            raise ProcessManagerError(f"Reload failed: {e}") from e

    def close_editor(self, process_name: str, save_changes: bool = False) -> bool:
        """
        Close an active editor session.

        Args:
            process_name: Name of the process
            save_changes: If True, save changes before closing

        Returns:
            True if editor was closed
        """
        if process_name not in self._editors:
            return False

        try:
            if save_changes and process_name in self._pending_changes:
                self.sync(process_name)

            del self._editors[process_name]
            logger.info(f"Closed editor for process '{process_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to close editor for '{process_name}': {e}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the process manager state.

        Returns:
            Dictionary with various statistics
        """
        total_processes = len(self._registry.list_processes())
        pending_count = len(self._pending_changes)
        active_editors = len(self._editors)

        return {
            'total_processes': total_processes,
            'pending_changes': pending_count,
            'active_editors': active_editors,
            'processes_directory': str(self._config.processes_dir),
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'config': {
                'default_format': self._config.default_format.value,
                'backup_enabled': self._config.backup_enabled,
                'strict_validation': self._config.strict_validation
            }
        }


    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - sync all pending changes."""
        if self._pending_changes:
            try:
                self.sync_all()
            except Exception as e:
                logger.error(f"Failed to sync pending changes on exit: {e}")

    def __repr__(self) -> str:
        return (f"ProcessManager(processes={len(self._registry.list_processes())}, "
                f"pending={len(self._pending_changes)}, "
                f"editors={len(self._editors)})")
