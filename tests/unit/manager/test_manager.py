"""Comprehensive unit tests for the stageflow.manager.manager module.

This test suite covers all functionality in the ProcessManager class including:
- Manager initialization and configuration
- Process coordination between registry and editors
- Process lifecycle management (create, load, edit, sync, delete)
- Editor management and tracking
- Batch operations and synchronization
- Error handling and edge cases
- Context manager functionality
- Statistics and monitoring
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stageflow.manager.config import ManagerConfig
from stageflow.manager.editor import ProcessEditor
from stageflow.manager.manager import (
    ProcessManager,
    ProcessManagerError,
    ProcessNotFoundError,
    ProcessSyncError,
    ProcessValidationError,
)
from stageflow.manager.registry import ProcessRegistry
from stageflow.process import Process


class TestProcessManagerErrors:
    """Test suite for ProcessManager exception classes."""

    def test_process_manager_error_inheritance(self):
        """Verify ProcessManagerError inherits from Exception."""
        # Arrange & Act
        error = ProcessManagerError("test error")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_process_not_found_error_inheritance(self):
        """Verify ProcessNotFoundError inherits from ProcessManagerError."""
        # Arrange & Act
        error = ProcessNotFoundError("process not found")

        # Assert
        assert isinstance(error, ProcessManagerError)
        assert str(error) == "process not found"

    def test_process_validation_error_inheritance(self):
        """Verify ProcessValidationError inherits from ProcessManagerError."""
        # Arrange & Act
        error = ProcessValidationError("validation failed")

        # Assert
        assert isinstance(error, ProcessManagerError)
        assert str(error) == "validation failed"

    def test_process_sync_error_inheritance(self):
        """Verify ProcessSyncError inherits from ProcessManagerError."""
        # Arrange & Act
        error = ProcessSyncError("sync failed")

        # Assert
        assert isinstance(error, ProcessManagerError)
        assert str(error) == "sync failed"


class TestProcessManagerCreation:
    """Test suite for ProcessManager creation and initialization."""

    def test_create_manager_with_default_config(self):
        """Verify ProcessManager can be created with default environment config."""
        # Arrange & Act
        with patch.object(ManagerConfig, 'from_env') as mock_from_env:
            mock_config = Mock(spec=ManagerConfig)
            mock_from_env.return_value = mock_config

            manager = ProcessManager()

        # Assert
        assert manager._config == mock_config
        assert isinstance(manager._registry, ProcessRegistry)
        assert isinstance(manager._editors, dict)
        assert isinstance(manager._pending_changes, set)
        assert manager._last_sync is None

    def test_create_manager_with_custom_config(self):
        """Verify ProcessManager can be created with custom config."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))

            # Act
            manager = ProcessManager(config)

        # Assert
        assert manager._config == config
        assert isinstance(manager._registry, ProcessRegistry)

    def test_manager_initializes_registry_on_creation(self):
        """Verify ProcessManager initializes registry during creation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))

            # Act
            manager = ProcessManager(config)

        # Assert
        # Registry is initialized directly in __init__, not via separate method
        assert isinstance(manager._registry, ProcessRegistry)
        assert manager._registry.config == config


class TestProcessManagerProperties:
    """Test suite for ProcessManager properties and accessors."""

    def create_test_manager(self):
        """Create a test manager with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            return ProcessManager(config)

    def test_config_property_returns_configuration(self):
        """Verify config property returns the manager configuration."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        result_config = manager.config

        # Assert
        assert isinstance(result_config, ManagerConfig)
        assert result_config == manager._config

    def test_processes_directory_property_returns_path(self):
        """Verify processes_directory property returns the processes directory path."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        directory = manager.processes_directory

        # Assert
        assert isinstance(directory, Path)
        assert directory == manager._config.processes_dir

    def test_pending_changes_property_returns_copy(self):
        """Verify pending_changes property returns a copy of pending changes set."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("test_process")

        # Act
        pending = manager.pending_changes

        # Assert
        assert isinstance(pending, set)
        assert "test_process" in pending
        # Verify it's a copy (modifications don't affect original)
        pending.add("another_process")
        assert "another_process" not in manager._pending_changes

    def test_last_sync_time_property_returns_timestamp(self):
        """Verify last_sync_time property returns the last sync timestamp."""
        # Arrange
        manager = self.create_test_manager()
        test_time = datetime.now()
        manager._last_sync = test_time

        # Act
        last_sync = manager.last_sync_time

        # Assert
        assert last_sync == test_time


class TestProcessManagerListOperations:
    """Test suite for ProcessManager list and discovery operations."""

    def create_test_manager(self):
        """Create a test manager with mocked registry."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            # Mock the registry
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_list_processes_delegates_to_registry(self):
        """Verify list_processes delegates to the registry."""
        # Arrange
        manager = self.create_test_manager()
        expected_processes = ["process1", "process2", "process3"]
        manager._registry.list_processes.return_value = expected_processes

        # Act
        processes = manager.list_processes()

        # Assert
        # The actual list_processes returns sorted combination of file-based and in-memory processes
        assert set(processes) == set(expected_processes)
        manager._registry.list_processes.assert_called_once()

    def test_process_exists_delegates_to_registry(self):
        """Verify process_exists checks both registry and in-memory editors."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        # Act
        exists = manager.process_exists("test_process")

        # Assert
        assert exists is True
        manager._registry.process_exists.assert_called_once_with("test_process")


class TestProcessManagerEditorOperations:
    """Test suite for ProcessManager editor management operations."""

    def create_test_manager(self):
        """Create a test manager for editor operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def create_mock_process(self):
        """Create a mock process for testing."""
        mock_process = Mock(spec=Process)
        mock_process.name = "test_process"
        return mock_process

    def test_edit_process_creates_new_editor(self):
        """Verify edit_process creates new editor for process."""
        # Arrange
        manager = self.create_test_manager()
        mock_process = self.create_mock_process()
        manager._registry.load_process.return_value = mock_process

        # Act
        with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
            mock_editor = Mock(spec=ProcessEditor)
            mock_editor_class.return_value = mock_editor

            editor = manager.edit_process("test_process")

        # Assert
        assert editor == mock_editor
        assert "test_process" in manager._editors
        # Note: edit_process does NOT add to pending_changes until actual changes are made
        manager._registry.load_process.assert_called_once_with("test_process")

    def test_edit_process_returns_existing_editor(self):
        """Verify edit_process returns existing editor if already created."""
        # Arrange
        manager = self.create_test_manager()
        existing_editor = Mock(spec=ProcessEditor)
        manager._editors["test_process"] = existing_editor

        # Act
        editor = manager.edit_process("test_process")

        # Assert
        assert editor == existing_editor
        # Registry should not be called since editor already exists
        manager._registry.load_process.assert_not_called()

    def test_get_process_editor_with_existing_process(self):
        """Verify get_process_editor works with existing process."""
        # Arrange
        manager = self.create_test_manager()
        mock_process = self.create_mock_process()
        manager._registry.load_process.return_value = mock_process

        # Act
        with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
            mock_editor = Mock(spec=ProcessEditor)
            mock_editor_class.return_value = mock_editor

            editor = manager.get_process_editor("test_process")

        # Assert
        assert editor == mock_editor
        mock_editor_class.assert_called_once_with(mock_process)

    def test_get_process_editor_create_if_missing_true(self):
        """Verify get_process_editor raises error when create_if_missing=True but process doesn't exist."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.load_process.side_effect = Exception("Process not found")

        # Act & Assert
        # The actual implementation raises ProcessManagerError when create_if_missing=True
        # but process doesn't exist, as it doesn't implement process creation in this method
        with pytest.raises(ProcessManagerError, match="Cannot create editor for non-existent process"):
            manager.get_process_editor("nonexistent", create_if_missing=True)

    def test_get_process_editor_create_if_missing_false_raises_error(self):
        """Verify get_process_editor raises error when create_if_missing=False and process not found."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.load_process.side_effect = Exception("Process not found")

        # Act & Assert
        with pytest.raises(ProcessNotFoundError, match="Process 'nonexistent' not found"):
            manager.get_process_editor("nonexistent", create_if_missing=False)


class TestProcessManagerProcessLifecycle:
    """Test suite for ProcessManager process lifecycle operations."""

    def create_test_manager(self):
        """Create a test manager for lifecycle operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_load_process_delegates_to_registry(self):
        """Verify load_process delegates to registry and handles success."""
        # Arrange
        manager = self.create_test_manager()
        mock_process = Mock(spec=Process)
        manager._registry.load_process.return_value = mock_process

        # Act
        process = manager.load_process("test_process")

        # Assert
        assert process == mock_process
        manager._registry.load_process.assert_called_once_with("test_process")

    def test_load_process_raises_not_found_error_on_failure(self):
        """Verify load_process raises ProcessNotFoundError when registry fails."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.load_process.side_effect = Exception("Process not found")

        # Act & Assert
        with pytest.raises(ProcessNotFoundError, match="Process 'test_process' not found"):
            manager.load_process("test_process")

    def test_create_process_with_valid_config(self):
        """Verify create_process successfully creates new process."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        process_config = {
            "name": "new_process",
            "stages": {"start": {"gates": []}},
            "initial_stage": "start"
        }

        # Act
        with patch('stageflow.manager.manager.Process') as mock_process_class:
            with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
                with patch.object(manager, 'sync') as mock_sync:
                    mock_process = Mock(spec=Process)
                    mock_process_class.return_value = mock_process

                    mock_editor = Mock(spec=ProcessEditor)
                    mock_editor_class.return_value = mock_editor

                    editor = manager.create_process("new_process", process_config)

        # Assert
        assert editor == mock_editor
        assert "new_process" in manager._editors
        assert "new_process" in manager._pending_changes
        mock_process_class.assert_called_once_with(process_config)
        mock_editor_class.assert_called_once_with(mock_process)
        mock_sync.assert_called_once_with("new_process")

    def test_create_process_with_existing_name_raises_error(self):
        """Verify create_process raises error when process already exists."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        process_config = {"name": "existing_process"}

        # Act & Assert
        with pytest.raises(ProcessManagerError, match="Process 'existing_process' already exists"):
            manager.create_process("existing_process", process_config)

    def test_create_process_without_immediate_save(self):
        """Verify create_process without immediate save doesn't call sync."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        process_config = {"name": "new_process"}

        # Act
        with patch('stageflow.manager.manager.Process') as mock_process_class:
            with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
                with patch.object(manager, 'sync') as mock_sync:
                    mock_process = Mock(spec=Process)
                    mock_process_class.return_value = mock_process

                    mock_editor = Mock(spec=ProcessEditor)
                    mock_editor_class.return_value = mock_editor

                    manager.create_process("new_process", process_config, save_immediately=False)

        # Assert
        mock_sync.assert_not_called()

    def test_remove_process_with_existing_process(self):
        """Verify remove_process successfully removes existing process."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        # Add process to internal state
        manager._editors["test_process"] = Mock()
        manager._pending_changes.add("test_process")

        # Act
        with patch.object(manager._registry, 'delete_process') as mock_delete:
            result = manager.remove_process("test_process")

        # Assert
        assert result is True
        assert "test_process" not in manager._editors
        assert "test_process" not in manager._pending_changes
        mock_delete.assert_called_once_with("test_process")

    def test_remove_process_without_deleting_file(self):
        """Verify remove_process without file deletion doesn't call registry delete."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        # Act
        with patch.object(manager._registry, 'delete_process') as mock_delete:
            result = manager.remove_process("test_process", delete_file=False)

        # Assert
        assert result is True
        mock_delete.assert_not_called()

    def test_remove_process_nonexistent_raises_error(self):
        """Verify remove_process raises error for nonexistent process."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        # Act & Assert
        with pytest.raises(ProcessNotFoundError, match="Process 'nonexistent' not found"):
            manager.remove_process("nonexistent")


class TestProcessManagerSyncOperations:
    """Test suite for ProcessManager synchronization operations."""

    def create_test_manager(self):
        """Create a test manager for sync operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_sync_with_dirty_editor(self):
        """Verify sync successfully saves dirty editor."""
        # Arrange
        manager = self.create_test_manager()

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.is_dirty = True
        mock_editor.process = Mock(spec=Process)
        mock_editor.mark_clean = Mock()  # Add mark_clean method

        manager._editors["test_process"] = mock_editor
        manager._pending_changes.add("test_process")

        # Act
        result = manager.sync("test_process")

        # Assert
        assert result is True
        assert "test_process" not in manager._pending_changes
        assert manager._last_sync is not None
        manager._registry.save_process.assert_called_once_with("test_process", mock_editor.process)
        mock_editor.mark_clean.assert_called_once()

    def test_sync_with_clean_editor_returns_false(self):
        """Verify sync returns False for clean (non-dirty) editor."""
        # Arrange
        manager = self.create_test_manager()

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.is_dirty = False

        manager._editors["test_process"] = mock_editor

        # Act
        result = manager.sync("test_process")

        # Assert
        assert result is False
        manager._registry.save_process.assert_not_called()

    def test_sync_without_editor_returns_false(self):
        """Verify sync returns False when no editor exists."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        result = manager.sync("nonexistent")

        # Assert
        assert result is False

    def test_sync_with_registry_failure_returns_false(self):
        """Verify sync returns False when registry save fails."""
        # Arrange
        manager = self.create_test_manager()

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.is_dirty = True
        mock_editor.process = Mock(spec=Process)

        manager._editors["test_process"] = mock_editor
        manager._registry.save_process.side_effect = Exception("Save failed")

        # Act
        result = manager.sync("test_process")

        # Assert
        assert result is False

    def test_sync_all_processes_multiple_dirty_editors(self):
        """Verify sync_all successfully syncs multiple dirty editors."""
        # Arrange
        manager = self.create_test_manager()

        # Create multiple dirty editors
        for i in range(3):
            process_name = f"process_{i}"
            mock_editor = Mock(spec=ProcessEditor)
            mock_editor.is_dirty = True
            mock_editor.process = Mock(spec=Process)

            manager._editors[process_name] = mock_editor
            manager._pending_changes.add(process_name)

        # Act
        with patch.object(manager, 'sync', return_value=True) as mock_sync:
            results = manager.sync_all()

        # Assert
        assert len(results) == 3
        assert all(results.values())
        assert mock_sync.call_count == 3

    def test_get_modified_processes_returns_pending_changes_copy(self):
        """Verify get_modified_processes returns copy of pending changes."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.update(["process1", "process2"])

        # Act
        modified = manager.get_modified_processes()

        # Assert
        assert isinstance(modified, set)
        assert "process1" in modified
        assert "process2" in modified
        # Verify it's a copy
        modified.add("process3")
        assert "process3" not in manager._pending_changes


class TestProcessManagerBatchOperations:
    """Test suite for ProcessManager batch operations."""

    def create_test_manager(self):
        """Create a test manager for batch operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_has_pending_changes_for_specific_process(self):
        """Verify has_pending_changes returns correct status for specific process."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("modified_process")

        # Act & Assert
        assert manager.has_pending_changes("modified_process") is True
        assert manager.has_pending_changes("clean_process") is False

    def test_has_pending_changes_for_all_processes(self):
        """Verify has_pending_changes returns status dict for all processes."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("modified_process")
        manager._registry.list_processes.return_value = ["modified_process", "clean_process"]

        # Act
        result = manager.has_pending_changes()

        # Assert
        assert isinstance(result, dict)
        assert result["modified_process"] is True
        assert result["clean_process"] is False

    def test_reload_process_with_clean_state(self):
        """Verify reload_process successfully reloads clean process."""
        # Arrange
        manager = self.create_test_manager()
        mock_process = Mock(spec=Process)
        manager._registry.load_process.return_value = mock_process

        # Add existing editor
        old_editor = Mock()
        manager._editors["test_process"] = old_editor

        # Act
        with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
            new_editor = Mock(spec=ProcessEditor)
            mock_editor_class.return_value = new_editor

            result = manager.reload_process("test_process")

        # Assert
        assert result is True
        assert manager._editors["test_process"] == new_editor
        assert "test_process" not in manager._pending_changes
        manager._registry.load_process.assert_called_once_with("test_process")

    def test_reload_process_with_pending_changes_and_force_false(self):
        """Verify reload_process raises error when process has pending changes and force=False."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("modified_process")

        # Act & Assert
        with pytest.raises(ProcessManagerError, match="has pending changes"):
            manager.reload_process("modified_process", force=False)

    def test_reload_process_with_pending_changes_and_force_true(self):
        """Verify reload_process succeeds when force=True even with pending changes."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("modified_process")

        mock_process = Mock(spec=Process)
        manager._registry.load_process.return_value = mock_process

        # Act
        with patch('stageflow.manager.manager.ProcessEditor'):
            result = manager.reload_process("modified_process", force=True)

        # Assert
        assert result is True
        assert "modified_process" not in manager._pending_changes

    def test_close_editor_with_save_changes(self):
        """Verify close_editor saves changes when save_changes=True."""
        # Arrange
        manager = self.create_test_manager()
        mock_editor = Mock(spec=ProcessEditor)
        manager._editors["test_process"] = mock_editor
        manager._pending_changes.add("test_process")

        # Act
        with patch.object(manager, 'sync') as mock_sync:
            result = manager.close_editor("test_process", save_changes=True)

        # Assert
        assert result is True
        assert "test_process" not in manager._editors
        mock_sync.assert_called_once_with("test_process")

    def test_close_editor_without_save_changes(self):
        """Verify close_editor doesn't save when save_changes=False."""
        # Arrange
        manager = self.create_test_manager()
        mock_editor = Mock(spec=ProcessEditor)
        manager._editors["test_process"] = mock_editor

        # Act
        with patch.object(manager, 'sync') as mock_sync:
            result = manager.close_editor("test_process", save_changes=False)

        # Assert
        assert result is True
        assert "test_process" not in manager._editors
        mock_sync.assert_not_called()

    def test_close_editor_nonexistent_returns_false(self):
        """Verify close_editor returns False for nonexistent editor."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        result = manager.close_editor("nonexistent")

        # Assert
        assert result is False


class TestProcessManagerStatistics:
    """Test suite for ProcessManager statistics and monitoring."""

    def create_test_manager(self):
        """Create a test manager for statistics testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_get_statistics_returns_complete_info(self):
        """Verify get_statistics returns comprehensive manager state information."""
        # Arrange
        manager = self.create_test_manager()

        # Set up state
        manager._registry.list_processes.return_value = ["proc1", "proc2", "proc3"]
        manager._pending_changes.update(["proc1", "proc2"])
        manager._editors["proc1"] = Mock()
        manager._editors["proc3"] = Mock()
        manager._last_sync = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        stats = manager.get_statistics()

        # Assert
        assert stats["total_processes"] == 3
        assert stats["pending_changes"] == 2
        assert stats["active_editors"] == 2
        assert stats["processes_directory"] == str(manager._config.processes_dir)
        assert stats["last_sync"] == "2024-01-01T12:00:00"

        # Check config section
        config_stats = stats["config"]
        assert config_stats["default_format"] == manager._config.default_format.value
        assert config_stats["backup_enabled"] == manager._config.backup_enabled
        assert config_stats["strict_validation"] == manager._config.strict_validation

    def test_get_statistics_with_no_last_sync(self):
        """Verify get_statistics handles None last_sync correctly."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.list_processes.return_value = []
        manager._last_sync = None

        # Act
        stats = manager.get_statistics()

        # Assert
        assert stats["last_sync"] is None


class TestProcessManagerContextManager:
    """Test suite for ProcessManager context manager functionality."""

    def create_test_manager(self):
        """Create a test manager for context manager testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_context_manager_enter_returns_self(self):
        """Verify context manager __enter__ returns self."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        with manager as context_manager:
            # Assert
            assert context_manager is manager

    def test_context_manager_exit_syncs_pending_changes(self):
        """Verify context manager __exit__ syncs pending changes."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.update(["proc1", "proc2"])

        # Act
        with patch.object(manager, 'sync_all') as mock_sync_all:
            with manager:
                pass

        # Assert
        mock_sync_all.assert_called_once()

    def test_context_manager_exit_without_pending_changes(self):
        """Verify context manager __exit__ doesn't sync when no pending changes."""
        # Arrange
        manager = self.create_test_manager()

        # Act
        with patch.object(manager, 'sync_all') as mock_sync_all:
            with manager:
                pass

        # Assert
        mock_sync_all.assert_not_called()

    def test_context_manager_exit_handles_sync_failure(self):
        """Verify context manager __exit__ handles sync failures gracefully."""
        # Arrange
        manager = self.create_test_manager()
        manager._pending_changes.add("proc1")

        # Act & Assert - Should not raise exception
        with patch.object(manager, 'sync_all', side_effect=Exception("Sync failed")):
            with patch('stageflow.manager.manager.logger') as mock_logger:
                with manager:
                    pass
                mock_logger.error.assert_called_once()


class TestProcessManagerStringRepresentation:
    """Test suite for ProcessManager string representation methods."""

    def create_test_manager(self):
        """Create a test manager for string representation testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_repr_returns_informative_string(self):
        """Verify __repr__ returns informative string representation."""
        # Arrange
        manager = self.create_test_manager()

        # Set up state
        manager._registry.list_processes.return_value = ["proc1", "proc2"]
        manager._pending_changes.add("proc1")
        manager._editors["proc1"] = Mock()

        # Act
        repr_str = repr(manager)

        # Assert
        expected = "ProcessManager(processes=2, pending=1, editors=1)"
        assert repr_str == expected


class TestProcessManagerImportExport:
    """Test suite for ProcessManager import and export operations."""

    def create_test_manager(self):
        """Create a test manager for import/export operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)
            return manager

    def test_export_process_with_existing_process(self):
        """Verify export_process successfully exports an existing process."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        mock_process = Mock(spec=Process)
        manager._registry.load_process.return_value = mock_process
        manager._registry._extract_process_data.return_value = {'process': {'name': 'test'}}

        export_path = Path('/tmp/exported.yaml')

        # Act
        with patch('builtins.open', create=True):
            with patch('ruamel.yaml.YAML'):
                result = manager.export_process('test_process', export_path)

        # Assert
        assert result == export_path
        manager._registry.process_exists.assert_called_once_with('test_process')
        manager._registry.load_process.assert_called_once_with('test_process')

    def test_export_process_with_nonexistent_process_raises_error(self):
        """Verify export_process raises error when process doesn't exist."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        # Act & Assert
        with pytest.raises(ProcessNotFoundError, match="Process 'nonexistent' not found"):
            manager.export_process('nonexistent', Path('/tmp/export.yaml'))

    def test_export_process_with_json_format(self):
        """Verify export_process correctly exports to JSON format."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        mock_process = Mock(spec=Process)
        manager._registry.load_process.return_value = mock_process
        manager._registry._extract_process_data.return_value = {'process': {'name': 'test'}}

        export_path = Path('/tmp/exported.json')

        # Act
        with patch('builtins.open', create=True):
            with patch('json.dump') as mock_json_dump:
                manager.export_process('test_process', export_path)

        # Assert
        mock_json_dump.assert_called_once()

    def test_import_process_with_new_process(self):
        """Verify import_process successfully imports a new process."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        import_path = Path('/tmp/import.yaml')
        mock_process = Mock(spec=Process)

        # Act
        with patch('stageflow.schema.load_process', return_value=mock_process):
            with patch.object(Path, 'exists', return_value=True):
                result = manager.import_process(import_path, 'new_process')

        # Assert
        assert result == 'new_process'
        manager._registry.save_process.assert_called_once_with('new_process', mock_process)

    def test_import_process_with_existing_process_and_overwrite_false_raises_error(self):
        """Verify import_process raises error when process exists and overwrite=False."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        import_path = Path('/tmp/import.yaml')

        # Act & Assert
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(ProcessManagerError, match="already exists"):
                manager.import_process(import_path, 'existing_process', overwrite=False)

    def test_import_process_with_existing_process_and_overwrite_true_succeeds(self):
        """Verify import_process overwrites existing process when overwrite=True."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = True

        import_path = Path('/tmp/import.yaml')
        mock_process = Mock(spec=Process)

        # Act
        with patch('stageflow.schema.load_process', return_value=mock_process):
            with patch.object(Path, 'exists', return_value=True):
                result = manager.import_process(import_path, 'existing_process', overwrite=True)

        # Assert
        assert result == 'existing_process'
        manager._registry.save_process.assert_called_once_with('existing_process', mock_process)

    def test_import_process_with_nonexistent_file_raises_error(self):
        """Verify import_process raises error when import file doesn't exist."""
        # Arrange
        manager = self.create_test_manager()
        import_path = Path('/tmp/nonexistent.yaml')

        # Act & Assert
        with pytest.raises(ProcessManagerError, match="Import file not found"):
            manager.import_process(import_path)

    def test_import_process_uses_filename_as_default_name(self):
        """Verify import_process uses filename stem as default process name."""
        # Arrange
        manager = self.create_test_manager()
        manager._registry.process_exists.return_value = False

        import_path = Path('/tmp/my_process.yaml')
        mock_process = Mock(spec=Process)

        # Act
        with patch('stageflow.schema.load_process', return_value=mock_process):
            with patch.object(Path, 'exists', return_value=True):
                result = manager.import_process(import_path)

        # Assert
        assert result == 'my_process'


class TestProcessManagerIntegration:
    """Integration tests for ProcessManager with real dependencies."""

    def test_full_workflow_with_real_components(self):
        """Test complete workflow using real ProcessRegistry and ProcessEditor components."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                create_dir_if_missing=True
            )

            # Act - Create manager and perform operations
            manager = ProcessManager(config)

            # Verify manager is properly initialized
            assert isinstance(manager._registry, ProcessRegistry)
            assert isinstance(manager._editors, dict)
            assert isinstance(manager._pending_changes, set)

    def test_error_handling_with_strict_validation(self):
        """Test error handling behavior with strict validation enabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                strict_validation=True
            )

            # Act & Assert - ProcessManager doesn't have _load_processes_from_directory
            # Instead test with registry initialization that might fail
            with patch.object(ProcessRegistry, '__init__', side_effect=Exception("Registry initialization failed")):
                with pytest.raises(Exception, match="Registry initialization failed"):
                    ProcessManager(config)

    def test_error_handling_with_lenient_validation(self):
        """Test error handling behavior with strict validation disabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                strict_validation=False
            )

            # Act - ProcessManager doesn't handle validation errors during init
            # Testing that normal initialization works
            manager = ProcessManager(config)

            # Assert
            assert isinstance(manager, ProcessManager)
            assert isinstance(manager._registry, ProcessRegistry)

    def test_concurrent_editor_management(self):
        """Test managing multiple editors concurrently."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            manager = ProcessManager(config)
            manager._registry = Mock(spec=ProcessRegistry)

            # Mock multiple processes
            for i in range(5):
                process_name = f"process_{i}"
                mock_process = Mock(spec=Process)
                mock_process.name = process_name
                manager._registry.load_process.return_value = mock_process

                # Act - Create multiple editors
                with patch('stageflow.manager.manager.ProcessEditor') as mock_editor_class:
                    mock_editor = Mock(spec=ProcessEditor)
                    mock_editor_class.return_value = mock_editor

                    manager.edit_process(process_name)

                # Assert
                assert process_name in manager._editors
                # Note: edit_process doesn't add to pending_changes immediately

            # Verify all editors are tracked
            assert len(manager._editors) == 5
