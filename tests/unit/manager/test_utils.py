"""Comprehensive unit tests for the stageflow.manager.utils module.

This test suite covers all functionality in the manager utils module including:
- CLI management utility functions
- Operation result types and handling
- Process management operations
- Validation utilities
- Error handling and edge cases
"""

import json
from unittest.mock import Mock

from stageflow.manager.editor import ProcessEditor
from stageflow.manager.manager import ProcessManager
from stageflow.manager.utils import (
    ManageOperationResult,
    OperationResultType,
    add_stage_to_process,
    list_all_processes,
    remove_stage_from_process,
    sync_all_processes,
    sync_process,
    validate_process_operations,
)


class TestOperationResultType:
    """Test suite for OperationResultType enum."""

    def test_operation_result_type_values(self):
        """Verify OperationResultType has correct string values."""
        # Arrange & Act & Assert
        assert OperationResultType.SUCCESS == "success"
        assert OperationResultType.NO_CHANGES == "no_changes"
        assert OperationResultType.NOT_FOUND == "not_found"
        assert OperationResultType.INVALID_JSON == "invalid_json"
        assert OperationResultType.INVALID_CONFIG == "invalid_config"
        assert OperationResultType.CONSISTENCY_FAILED == "consistency_failed"
        assert OperationResultType.OPERATION_FAILED == "operation_failed"
        assert OperationResultType.VALIDATION_FAILED == "validation_failed"

    def test_operation_result_type_membership(self):
        """Verify OperationResultType enum membership."""
        # Arrange & Act
        result_types = list(OperationResultType)

        # Assert
        assert len(result_types) == 8
        expected_types = [
            OperationResultType.SUCCESS,
            OperationResultType.NO_CHANGES,
            OperationResultType.NOT_FOUND,
            OperationResultType.INVALID_JSON,
            OperationResultType.INVALID_CONFIG,
            OperationResultType.CONSISTENCY_FAILED,
            OperationResultType.OPERATION_FAILED,
            OperationResultType.VALIDATION_FAILED
        ]
        for expected_type in expected_types:
            assert expected_type in result_types


class TestManageOperationResult:
    """Test suite for ManageOperationResult dataclass."""

    def test_create_operation_result_with_minimal_parameters(self):
        """Verify ManageOperationResult can be created with minimal parameters."""
        # Arrange & Act
        result = ManageOperationResult(OperationResultType.SUCCESS)

        # Assert
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data is None
        assert result.custom_message is None

    def test_create_operation_result_with_all_parameters(self):
        """Verify ManageOperationResult can be created with all parameters."""
        # Arrange
        test_data = {"test": "data"}
        custom_message = "Custom test message"

        # Act
        result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=test_data,
            custom_message=custom_message
        )

        # Assert
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data == test_data
        assert result.custom_message == custom_message

    def test_success_property_returns_true_for_success_types(self):
        """Verify success property returns True for success and no_changes types."""
        # Arrange & Act
        success_result = ManageOperationResult(OperationResultType.SUCCESS)
        no_changes_result = ManageOperationResult(OperationResultType.NO_CHANGES)

        # Assert
        assert success_result.success is True
        assert no_changes_result.success is True

    def test_success_property_returns_false_for_error_types(self):
        """Verify success property returns False for error types."""
        # Arrange
        error_types = [
            OperationResultType.NOT_FOUND,
            OperationResultType.INVALID_JSON,
            OperationResultType.INVALID_CONFIG,
            OperationResultType.CONSISTENCY_FAILED,
            OperationResultType.OPERATION_FAILED,
            OperationResultType.VALIDATION_FAILED
        ]

        # Act & Assert
        for error_type in error_types:
            result = ManageOperationResult(error_type)
            assert result.success is False, f"Failed for {error_type}"

    def test_message_property_returns_custom_message_when_provided(self):
        """Verify message property returns custom message when provided."""
        # Arrange
        custom_message = "Custom test message"
        result = ManageOperationResult(
            OperationResultType.SUCCESS,
            custom_message=custom_message
        )

        # Act
        message = result.message

        # Assert
        assert message == custom_message

    def test_message_property_returns_default_message_for_success(self):
        """Verify message property returns default message for success type."""
        # Arrange
        result = ManageOperationResult(OperationResultType.SUCCESS)

        # Act
        message = result.message

        # Assert
        assert message == "Operation completed successfully"

    def test_message_property_returns_default_messages_for_all_types(self):
        """Verify message property returns correct default messages for all types."""
        # Arrange
        expected_messages = {
            OperationResultType.SUCCESS: "Operation completed successfully",
            OperationResultType.NO_CHANGES: "No changes to save",
            OperationResultType.NOT_FOUND: "Process not found",
            OperationResultType.INVALID_JSON: "Invalid JSON configuration",
            OperationResultType.INVALID_CONFIG: "Invalid stage configuration",
            OperationResultType.CONSISTENCY_FAILED: "Process consistency check failed",
            OperationResultType.OPERATION_FAILED: "Operation failed",
            OperationResultType.VALIDATION_FAILED: "Validation failed"
        }

        # Act & Assert
        for result_type, expected_message in expected_messages.items():
            result = ManageOperationResult(result_type)
            assert result.message == expected_message

    def test_with_context_appends_context_to_message(self):
        """Verify with_context appends context to the message."""
        # Arrange
        result = ManageOperationResult(OperationResultType.SUCCESS)
        context = "additional context"

        # Act
        message_with_context = result.with_context(context)

        # Assert
        expected = "Operation completed successfully: additional context"
        assert message_with_context == expected

    def test_with_context_returns_base_message_without_context(self):
        """Verify with_context returns base message when no context provided."""
        # Arrange
        result = ManageOperationResult(OperationResultType.SUCCESS)

        # Act
        message_without_context = result.with_context("")

        # Assert
        assert message_without_context == "Operation completed successfully"

    def test_with_context_uses_custom_message_as_base(self):
        """Verify with_context uses custom message as base when provided."""
        # Arrange
        custom_message = "Custom message"
        result = ManageOperationResult(
            OperationResultType.SUCCESS,
            custom_message=custom_message
        )
        context = "with context"

        # Act
        message_with_context = result.with_context(context)

        # Assert
        expected = "Custom message: with context"
        assert message_with_context == expected


class TestListAllProcesses:
    """Test suite for list_all_processes utility function."""

    def create_mock_manager(self):
        """Create a mock manager for testing."""
        return Mock(spec=ProcessManager)

    def test_list_all_processes_success(self):
        """Verify list_all_processes returns success result with process list."""
        # Arrange
        manager = self.create_mock_manager()
        test_processes = ["process1", "process2", "process3"]
        manager.list_processes.return_value = test_processes

        # Act
        result = list_all_processes(manager)

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data == test_processes
        assert "Found 3 processes" in result.message

    def test_list_all_processes_empty_list(self):
        """Verify list_all_processes handles empty process list."""
        # Arrange
        manager = self.create_mock_manager()
        manager.list_processes.return_value = []

        # Act
        result = list_all_processes(manager)

        # Assert
        assert result.success is True
        assert result.data == []
        assert "Found 0 processes" in result.message

    def test_list_all_processes_manager_exception(self):
        """Verify list_all_processes handles manager exceptions."""
        # Arrange
        manager = self.create_mock_manager()
        manager.list_processes.side_effect = Exception("Manager error")

        # Act
        result = list_all_processes(manager)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Failed to list processes: Manager error" in result.message


class TestSyncAllProcesses:
    """Test suite for sync_all_processes utility function."""

    def create_mock_manager(self):
        """Create a mock manager for testing."""
        return Mock(spec=ProcessManager)

    def test_sync_all_processes_all_success(self):
        """Verify sync_all_processes with all processes syncing successfully."""
        # Arrange
        manager = self.create_mock_manager()
        sync_results = {"process1": True, "process2": True, "process3": True}
        manager.sync_all.return_value = sync_results

        # Act
        result = sync_all_processes(manager)

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data == sync_results
        assert "Synced 3/3 processes" in result.message

    def test_sync_all_processes_partial_success(self):
        """Verify sync_all_processes with partial success."""
        # Arrange
        manager = self.create_mock_manager()
        sync_results = {"process1": True, "process2": False, "process3": True}
        manager.sync_all.return_value = sync_results

        # Act
        result = sync_all_processes(manager)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert result.data == sync_results
        assert "Synced 2/3 processes" in result.message

    def test_sync_all_processes_no_pending_changes(self):
        """Verify sync_all_processes when no processes have pending changes."""
        # Arrange
        manager = self.create_mock_manager()
        manager.sync_all.return_value = {}

        # Act
        result = sync_all_processes(manager)

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.NO_CHANGES
        assert result.data == {}
        assert "No processes have pending changes" in result.message

    def test_sync_all_processes_manager_exception(self):
        """Verify sync_all_processes handles manager exceptions."""
        # Arrange
        manager = self.create_mock_manager()
        manager.sync_all.side_effect = Exception("Sync error")

        # Act
        result = sync_all_processes(manager)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Failed to sync processes: Sync error" in result.message


class TestAddStageToProcess:
    """Test suite for add_stage_to_process utility function."""

    def create_mock_manager(self):
        """Create a mock manager for testing."""
        return Mock(spec=ProcessManager)

    def create_valid_stage_config(self):
        """Create a valid stage configuration for testing."""
        return {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_properties": {},
            "is_final": False
        }

    def test_add_stage_to_process_success(self):
        """Verify add_stage_to_process adds stage successfully."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.add_stage.return_value = True
        manager.edit_process.return_value = mock_editor

        stage_config = self.create_valid_stage_config()
        stage_config_json = json.dumps(stage_config)

        # Act
        result = add_stage_to_process(manager, "test_process", stage_config_json)

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data["stage_id"] == "test_stage"
        assert result.data["process_name"] == "test_process"
        assert "Stage 'test_stage' added to 'test_process'" in result.message

    def test_add_stage_to_process_nonexistent_process(self):
        """Verify add_stage_to_process handles nonexistent process."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = False

        stage_config_json = json.dumps(self.create_valid_stage_config())

        # Act
        result = add_stage_to_process(manager, "nonexistent", stage_config_json)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.NOT_FOUND
        assert "Process 'nonexistent' not found" in result.message

    def test_add_stage_to_process_invalid_json(self):
        """Verify add_stage_to_process handles invalid JSON."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        invalid_json = "{ invalid json }"

        # Act
        result = add_stage_to_process(manager, "test_process", invalid_json)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.INVALID_JSON

    def test_add_stage_to_process_missing_name_field(self):
        """Verify add_stage_to_process handles missing name field."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        config_without_name = {"description": "Stage without name"}
        stage_config_json = json.dumps(config_without_name)

        # Act
        result = add_stage_to_process(manager, "test_process", stage_config_json)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.INVALID_CONFIG
        assert "must include 'name' field" in result.message

    def test_add_stage_to_process_editor_failure(self):
        """Verify add_stage_to_process handles editor add_stage failure."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.add_stage.return_value = False
        manager.edit_process.return_value = mock_editor

        stage_config_json = json.dumps(self.create_valid_stage_config())

        # Act
        result = add_stage_to_process(manager, "test_process", stage_config_json)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.CONSISTENCY_FAILED
        assert "Failed to add stage 'test_stage'" in result.message

    def test_add_stage_to_process_exception_handling(self):
        """Verify add_stage_to_process handles unexpected exceptions."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.side_effect = Exception("Unexpected error")

        stage_config_json = json.dumps(self.create_valid_stage_config())

        # Act
        result = add_stage_to_process(manager, "test_process", stage_config_json)

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Error adding stage: Unexpected error" in result.message


class TestRemoveStageFromProcess:
    """Test suite for remove_stage_from_process utility function."""

    def create_mock_manager(self):
        """Create a mock manager for testing."""
        return Mock(spec=ProcessManager)

    def test_remove_stage_from_process_success(self):
        """Verify remove_stage_from_process removes stage successfully."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.remove_stage.return_value = True
        manager.edit_process.return_value = mock_editor

        # Act
        result = remove_stage_from_process(manager, "test_process", "test_stage")

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data["stage_name"] == "test_stage"
        assert result.data["process_name"] == "test_process"
        assert "Stage 'test_stage' removed from 'test_process'" in result.message

    def test_remove_stage_from_process_nonexistent_process(self):
        """Verify remove_stage_from_process handles nonexistent process."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = False

        # Act
        result = remove_stage_from_process(manager, "nonexistent", "test_stage")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.NOT_FOUND
        assert "Process 'nonexistent' not found" in result.message

    def test_remove_stage_from_process_editor_failure(self):
        """Verify remove_stage_from_process handles editor remove_stage failure."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True

        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.remove_stage.return_value = False
        manager.edit_process.return_value = mock_editor

        # Act
        result = remove_stage_from_process(manager, "test_process", "test_stage")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.CONSISTENCY_FAILED
        assert "Failed to remove stage 'test_stage'" in result.message

    def test_remove_stage_from_process_exception_handling(self):
        """Verify remove_stage_from_process handles unexpected exceptions."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.side_effect = Exception("Unexpected error")

        # Act
        result = remove_stage_from_process(manager, "test_process", "test_stage")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Error removing stage: Unexpected error" in result.message


class TestSyncProcess:
    """Test suite for sync_process utility function."""

    def create_mock_manager(self):
        """Create a mock manager for testing."""
        return Mock(spec=ProcessManager)

    def test_sync_process_success_with_changes(self):
        """Verify sync_process successfully syncs process with changes."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True
        manager.get_modified_processes.return_value = {"test_process"}
        manager.sync.return_value = True

        # Act
        result = sync_process(manager, "test_process")

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS
        assert result.data["process_name"] == "test_process"
        assert "Process 'test_process' saved" in result.message

    def test_sync_process_success_no_changes(self):
        """Verify sync_process handles successful sync with no changes."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True
        manager.get_modified_processes.return_value = set()
        manager.sync.return_value = True

        # Act
        result = sync_process(manager, "test_process")

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.NO_CHANGES
        assert result.data["process_name"] == "test_process"
        assert "No changes to save for 'test_process'" in result.message

    def test_sync_process_nonexistent_process(self):
        """Verify sync_process handles nonexistent process."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = False

        # Act
        result = sync_process(manager, "nonexistent")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.NOT_FOUND
        assert "Process 'nonexistent' not found" in result.message

    def test_sync_process_sync_failure(self):
        """Verify sync_process handles sync failure."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.return_value = True
        manager.get_modified_processes.return_value = {"test_process"}
        manager.sync.return_value = False

        # Act
        result = sync_process(manager, "test_process")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Failed to sync 'test_process'" in result.message

    def test_sync_process_exception_handling(self):
        """Verify sync_process handles unexpected exceptions."""
        # Arrange
        manager = self.create_mock_manager()
        manager.process_exists.side_effect = Exception("Unexpected error")

        # Act
        result = sync_process(manager, "test_process")

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.OPERATION_FAILED
        assert "Error syncing process: Unexpected error" in result.message


class TestValidateProcessOperations:
    """Test suite for validate_process_operations utility function."""

    def test_validate_process_operations_no_process_specific_ops(self):
        """Verify validation passes when no process-specific operations are requested."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage=None,
            remove_stage=None,
            sync_flag=False
        )

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS

    def test_validate_process_operations_with_process_name_and_ops(self):
        """Verify validation passes when process name is provided with operations."""
        # Arrange & Act
        result = validate_process_operations(
            process_name="test_process",
            add_stage='{"name": "test"}',
            remove_stage="test_stage",
            sync_flag=True
        )

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS

    def test_validate_process_operations_add_stage_without_process_name(self):
        """Verify validation fails when add_stage is provided without process name."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage='{"name": "test"}',
            remove_stage=None,
            sync_flag=False
        )

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.VALIDATION_FAILED
        assert "--process required for process-specific operations" in result.message

    def test_validate_process_operations_remove_stage_without_process_name(self):
        """Verify validation fails when remove_stage is provided without process name."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage=None,
            remove_stage="test_stage",
            sync_flag=False
        )

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.VALIDATION_FAILED
        assert "--process required for process-specific operations" in result.message

    def test_validate_process_operations_sync_flag_without_process_name(self):
        """Verify validation fails when sync_flag is True without process name."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage=None,
            remove_stage=None,
            sync_flag=True
        )

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.VALIDATION_FAILED
        assert "--process required for process-specific operations" in result.message

    def test_validate_process_operations_multiple_ops_without_process_name(self):
        """Verify validation fails when multiple operations are provided without process name."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage='{"name": "test"}',
            remove_stage="test_stage",
            sync_flag=True
        )

        # Assert
        assert result.success is False
        assert result.result_type == OperationResultType.VALIDATION_FAILED
        assert "--process required for process-specific operations" in result.message

    def test_validate_process_operations_empty_string_operations(self):
        """Verify validation treats empty strings as no operation."""
        # Arrange & Act
        result = validate_process_operations(
            process_name=None,
            add_stage="",
            remove_stage="",
            sync_flag=False
        )

        # Assert
        assert result.success is True
        assert result.result_type == OperationResultType.SUCCESS


class TestUtilityFunctionsIntegration:
    """Integration tests for utility functions working together."""

    def create_mock_manager_with_processes(self):
        """Create a mock manager with sample processes."""
        manager = Mock(spec=ProcessManager)

        # Mock process list
        manager.list_processes.return_value = ["process1", "process2"]

        # Mock process existence checks
        manager.process_exists.side_effect = lambda name: name in ["process1", "process2"]

        # Mock modified processes
        manager.get_modified_processes.return_value = {"process1"}

        # Mock sync operations
        manager.sync.return_value = True
        manager.sync_all.return_value = {"process1": True, "process2": True}

        # Mock editor operations
        mock_editor = Mock(spec=ProcessEditor)
        mock_editor.add_stage.return_value = True
        mock_editor.remove_stage.return_value = True
        manager.edit_process.return_value = mock_editor

        return manager

    def test_full_workflow_list_add_sync(self):
        """Test a complete workflow: list processes, add stage, sync."""
        # Arrange
        manager = self.create_mock_manager_with_processes()
        stage_config = {"name": "new_stage", "description": "New stage"}
        stage_config_json = json.dumps(stage_config)

        # Act - List processes
        list_result = list_all_processes(manager)

        # Act - Add stage
        add_result = add_stage_to_process(manager, "process1", stage_config_json)

        # Act - Sync process
        sync_result = sync_process(manager, "process1")

        # Assert
        assert list_result.success is True
        assert len(list_result.data) == 2

        assert add_result.success is True
        assert add_result.data["stage_id"] == "new_stage"

        assert sync_result.success is True
        assert sync_result.data["process_name"] == "process1"

    def test_error_handling_workflow(self):
        """Test error handling in a workflow with failures."""
        # Arrange
        manager = Mock(spec=ProcessManager)
        manager.process_exists.return_value = False

        # Act - Try to add stage to nonexistent process
        add_result = add_stage_to_process(manager, "nonexistent", '{"name": "test"}')

        # Act - Try to remove stage from nonexistent process
        remove_result = remove_stage_from_process(manager, "nonexistent", "test_stage")

        # Act - Try to sync nonexistent process
        sync_result = sync_process(manager, "nonexistent")

        # Assert
        assert add_result.success is False
        assert add_result.result_type == OperationResultType.NOT_FOUND

        assert remove_result.success is False
        assert remove_result.result_type == OperationResultType.NOT_FOUND

        assert sync_result.success is False
        assert sync_result.result_type == OperationResultType.NOT_FOUND

    def test_validation_and_operation_workflow(self):
        """Test validation followed by operations."""
        # Arrange
        manager = self.create_mock_manager_with_processes()

        # Act - Validate operations with process name
        validation_result = validate_process_operations(
            process_name="process1",
            add_stage='{"name": "test"}',
            remove_stage=None,
            sync_flag=True
        )

        # Act - If validation passes, perform operations
        if validation_result.success:
            add_result = add_stage_to_process(manager, "process1", '{"name": "test"}')
            sync_result = sync_process(manager, "process1")
        else:
            add_result = None
            sync_result = None

        # Assert
        assert validation_result.success is True
        assert add_result is not None
        assert add_result.success is True
        assert sync_result is not None
        assert sync_result.success is True

    def test_validation_failure_prevents_operations(self):
        """Test that validation failure prevents operations from proceeding."""
        # Arrange
        manager = self.create_mock_manager_with_processes()

        # Act - Validate operations without process name
        validation_result = validate_process_operations(
            process_name=None,
            add_stage='{"name": "test"}',
            remove_stage=None,
            sync_flag=False
        )

        # Assert validation failed
        assert validation_result.success is False
        assert validation_result.result_type == OperationResultType.VALIDATION_FAILED

        # Operations should not be performed when validation fails
        # This demonstrates proper workflow control
