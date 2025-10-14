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
        return self._pending_changes.copy()

    @property
    def last_sync_time(self) -> datetime | None:
        """Get the last synchronization timestamp."""
        return self._last_sync

    def list_processes(self, include_metadata: bool = False) -> list[str] | dict[str, Any]:
        """
        List all processes in the registry.

        Args:
            include_metadata: If True, return metadata for each process

        Returns:
            List of process names or dict with metadata if include_metadata=True
        """
        process_names = self._registry.list_processes()

        if not include_metadata:
            return process_names

        result = {}
        for name in process_names:
            try:
                metadata = self._registry.get_process_info(name)
                result[name] = {
                    **metadata,
                    'has_pending_changes': name in self._pending_changes,
                    'has_active_editor': name in self._editors,
                }
            except Exception:
                # Skip processes that can't be accessed
                result[name] = {
                    'name': name,
                    'has_pending_changes': name in self._pending_changes,
                    'has_active_editor': name in self._editors,
                }

        return result

    def process_exists(self, process_name: str) -> bool:
        """Check if a process exists in the registry."""
        return self._registry.process_exists(process_name)

    def edit_process(self, process_name: str) -> ProcessEditor:
        """Get or create a ProcessEditor for the specified process."""
        if process_name in self._editors:
            return self._editors[process_name]

        # Load process from registry
        process = self._registry.load_process(process_name)
        editor = ProcessEditor(process)
        self._editors[process_name] = editor
        self._pending_changes.add(process_name)
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

        # For new processes or processes with pending changes, always sync
        # regardless of the editor's dirty flag
        if process_name not in self._pending_changes and not editor.is_dirty:
            return False

        try:
            # Save the process using the registry
            self._registry.save_process(process_name, editor.process)
            self._pending_changes.discard(process_name)
            self._last_sync = datetime.now()
            return True
        except Exception:
            return False

    def get_modified_processes(self) -> set[str]:
        """Get set of process names with pending changes."""
        return self._pending_changes.copy()

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


    def has_pending_changes(self, process_name: str | None = None) -> bool | dict[str, bool]:
        """
        Check if processes have pending changes.

        Args:
            process_name: Specific process name to check, or None for all

        Returns:
            Boolean for specific process, or dict for all processes
        """
        if process_name is not None:
            return process_name in self._pending_changes

        return {name: name in self._pending_changes for name in self._registry.list_processes()}

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
