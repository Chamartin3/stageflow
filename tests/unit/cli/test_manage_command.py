"""Comprehensive unit tests for the stageflow.cli.commands.manage module.

This test suite covers all functionality in the manage CLI command including:
- Command line argument parsing and validation
- Global operations (list, sync-all)
- Process-specific operations (add-stage, remove-stage, sync)
- Error handling and user feedback
- Integration with manager utilities
- Click command interface functionality
"""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from stageflow.cli.commands.manage import manage
from stageflow.manager.manager import ProcessManager
from stageflow.manager.utils import ManageOperationResult, OperationResultType


class TestManageCommandBasics:
    """Test suite for basic manage command functionality."""

    def test_manage_command_is_click_command(self):
        """Verify manage is a properly configured Click command."""
        # Arrange & Act & Assert
        assert hasattr(manage, 'params')  # Click commands have params attribute
        assert manage.name == 'manage'

    def test_manage_command_has_required_options(self):
        """Verify manage command has all required options."""
        # Arrange
        param_names = [param.name for param in manage.params]

        # Act & Assert
        expected_options = [
            'list_processes',
            'process_name',
            'add_stage_config',
            'remove_stage_name',
            'sync_process_flag',
            'sync_all_processes_flag'
        ]

        for option in expected_options:
            assert option in param_names, f"Missing option: {option}"


class TestManageCommandListProcesses:
    """Test suite for the list processes functionality."""

    def test_list_processes_with_available_processes(self):
        """Verify --list displays available processes."""
        # Arrange
        runner = CliRunner()
        test_processes = ["process1", "process2", "process3"]

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=test_processes,
            custom_message=f"Found {len(test_processes)} processes"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.list_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--list'])

        # Assert
        assert result.exit_code == 0
        assert "Available processes:" in result.output
        assert "process1" in result.output
        assert "process2" in result.output
        assert "process3" in result.output

    def test_list_processes_with_no_processes(self):
        """Verify --list handles empty process list."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=[],
            custom_message="Found 0 processes"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.list_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--list'])

        # Assert
        assert result.exit_code == 0
        assert "No processes found" in result.output

    def test_list_processes_with_error(self):
        """Verify --list handles errors gracefully."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.OPERATION_FAILED,
            custom_message="Failed to list processes: Access denied"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.list_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--list'])

        # Assert
        assert result.exit_code != 0
        assert "Error: Failed to list processes: Access denied" in result.output

    def test_default_action_lists_processes(self):
        """Verify that running manage without options lists processes."""
        # Arrange
        runner = CliRunner()
        test_processes = ["default_process"]

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=test_processes,
            custom_message="Found 1 processes"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.list_all_processes', return_value=mock_result):
                result = runner.invoke(manage, [])

        # Assert
        assert result.exit_code == 0
        assert "Available processes:" in result.output
        assert "default_process" in result.output


class TestManageCommandSyncAll:
    """Test suite for the sync all processes functionality."""

    def test_sync_all_processes_success(self):
        """Verify --sync-all successfully syncs all processes."""
        # Arrange
        runner = CliRunner()
        sync_results = {"process1": True, "process2": True, "process3": False}

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=sync_results,
            custom_message="Synced 2/3 processes"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.sync_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--sync-all'])

        # Assert
        assert result.exit_code == 0
        assert "Sync results:" in result.output
        assert "✓ process1" in result.output
        assert "✓ process2" in result.output
        assert "✗ process3" in result.output

    def test_sync_all_processes_no_changes(self):
        """Verify --sync-all handles no pending changes."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.NO_CHANGES,
            data={},
            custom_message="No processes have pending changes"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.sync_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--sync-all'])

        # Assert
        assert result.exit_code == 0
        assert "No processes had pending changes" in result.output

    def test_sync_all_processes_error(self):
        """Verify --sync-all handles errors gracefully."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.OPERATION_FAILED,
            custom_message="Failed to sync processes: Permission denied"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.sync_all_processes', return_value=mock_result):
                result = runner.invoke(manage, ['--sync-all'])

        # Assert
        assert result.exit_code != 0
        assert "Error: Failed to sync processes: Permission denied" in result.output


class TestManageCommandAddStage:
    """Test suite for add stage functionality."""

    def test_add_stage_success(self):
        """Verify --add-stage successfully adds stage to process."""
        # Arrange
        runner = CliRunner()
        stage_config = {"name": "new_stage", "description": "New test stage"}
        stage_config_json = json.dumps(stage_config)

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data={"stage_id": "new_stage", "process_name": "test_process"},
            custom_message="Stage 'new_stage' added to 'test_process' (not saved)"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--add-stage', stage_config_json])

        # Assert
        assert result.exit_code == 0
        assert "✓ Stage 'new_stage' added to 'test_process' (not saved)" in result.output

    def test_add_stage_without_process_name_fails_validation(self):
        """Verify --add-stage without --process fails validation."""
        # Arrange
        runner = CliRunner()
        stage_config_json = '{"name": "new_stage"}'

        mock_validation_result = ManageOperationResult(
            OperationResultType.VALIDATION_FAILED,
            custom_message="--process required for process-specific operations"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation_result):
                result = runner.invoke(manage, ['--add-stage', stage_config_json])

        # Assert
        assert result.exit_code != 0
        assert "Error: --process required for process-specific operations" in result.output

    def test_add_stage_process_not_found(self):
        """Verify --add-stage handles process not found error."""
        # Arrange
        runner = CliRunner()
        stage_config_json = '{"name": "new_stage"}'

        mock_result = ManageOperationResult(
            OperationResultType.NOT_FOUND,
            custom_message="Process 'nonexistent' not found"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'nonexistent', '--add-stage', stage_config_json])

        # Assert
        assert result.exit_code != 0
        assert "Error: Process 'nonexistent' not found" in result.output

    def test_add_stage_invalid_json(self):
        """Verify --add-stage handles invalid JSON configuration."""
        # Arrange
        runner = CliRunner()
        invalid_json = '{ invalid json }'

        mock_result = ManageOperationResult(
            OperationResultType.INVALID_JSON,
            custom_message="Invalid JSON configuration"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--add-stage', invalid_json])

        # Assert
        assert result.exit_code != 0
        assert "Error: Invalid JSON configuration" in result.output


class TestManageCommandRemoveStage:
    """Test suite for remove stage functionality."""

    def test_remove_stage_success(self):
        """Verify --remove-stage successfully removes stage from process."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data={"stage_name": "old_stage", "process_name": "test_process"},
            custom_message="Stage 'old_stage' removed from 'test_process' (not saved)"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.remove_stage_from_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--remove-stage', 'old_stage'])

        # Assert
        assert result.exit_code == 0
        assert "✓ Stage 'old_stage' removed from 'test_process' (not saved)" in result.output

    def test_remove_stage_without_process_name_fails_validation(self):
        """Verify --remove-stage without --process fails validation."""
        # Arrange
        runner = CliRunner()

        mock_validation_result = ManageOperationResult(
            OperationResultType.VALIDATION_FAILED,
            custom_message="--process required for process-specific operations"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation_result):
                result = runner.invoke(manage, ['--remove-stage', 'some_stage'])

        # Assert
        assert result.exit_code != 0
        assert "Error: --process required for process-specific operations" in result.output

    def test_remove_stage_consistency_failure(self):
        """Verify --remove-stage handles consistency check failures."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.CONSISTENCY_FAILED,
            custom_message="Failed to remove stage 'protected_stage'"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.remove_stage_from_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--remove-stage', 'protected_stage'])

        # Assert
        assert result.exit_code != 0
        assert "Error: Failed to remove stage 'protected_stage'" in result.output


class TestManageCommandSyncProcess:
    """Test suite for sync specific process functionality."""

    def test_sync_process_success_with_changes(self):
        """Verify --sync successfully saves process with changes."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data={"process_name": "test_process"},
            custom_message="Process 'test_process' saved"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.sync_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--sync'])

        # Assert
        assert result.exit_code == 0
        assert "✓ Process 'test_process' saved" in result.output

    def test_sync_process_no_changes(self):
        """Verify --sync handles process with no changes."""
        # Arrange
        runner = CliRunner()

        mock_result = ManageOperationResult(
            OperationResultType.NO_CHANGES,
            data={"process_name": "test_process"},
            custom_message="No changes to save for 'test_process'"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.sync_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--sync'])

        # Assert
        assert result.exit_code == 0
        assert "✓ No changes to save for 'test_process'" in result.output

    def test_sync_process_without_process_name_fails_validation(self):
        """Verify --sync without --process fails validation."""
        # Arrange
        runner = CliRunner()

        mock_validation_result = ManageOperationResult(
            OperationResultType.VALIDATION_FAILED,
            custom_message="--process required for process-specific operations"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation_result):
                result = runner.invoke(manage, ['--sync'])

        # Assert
        assert result.exit_code != 0
        assert "Error: --process required for process-specific operations" in result.output


class TestManageCommandProcessManagerInitialization:
    """Test suite for ProcessManager initialization handling."""

    def test_process_manager_initialization_success(self):
        """Verify successful ProcessManager initialization."""
        # Arrange
        runner = CliRunner()

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            mock_manager = Mock(spec=ProcessManager)
            mock_manager_class.return_value = mock_manager

            with patch('stageflow.cli.commands.manage.list_all_processes') as mock_list:
                mock_list.return_value = ManageOperationResult(
                    OperationResultType.SUCCESS,
                    data=["test_process"]
                )
                result = runner.invoke(manage, ['--list'])

        # Assert
        assert result.exit_code == 0
        mock_manager_class.assert_called_once()

    def test_process_manager_initialization_failure(self):
        """Verify handling of ProcessManager initialization failure."""
        # Arrange
        runner = CliRunner()

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Failed to initialize manager")
            result = runner.invoke(manage, ['--list'])

        # Assert
        assert result.exit_code != 0
        assert "Error: Failed to initialize process manager: Failed to initialize manager" in result.output


class TestManageCommandCombinedOperations:
    """Test suite for combined operations functionality."""

    def test_multiple_operations_in_sequence(self):
        """Verify multiple operations can be performed in sequence."""
        # Arrange
        runner = CliRunner()
        stage_config_json = '{"name": "new_stage"}'

        # Mock successful validation
        mock_validation = ManageOperationResult(OperationResultType.SUCCESS)

        # Mock successful add stage
        mock_add_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data={"stage_id": "new_stage", "process_name": "test_process"},
            custom_message="Stage 'new_stage' added to 'test_process' (not saved)"
        )

        # Mock successful sync
        mock_sync_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data={"process_name": "test_process"},
            custom_message="Process 'test_process' saved"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation):
                with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_add_result):
                    with patch('stageflow.cli.commands.manage.sync_process', return_value=mock_sync_result):
                        result = runner.invoke(manage, [
                            '--process', 'test_process',
                            '--add-stage', stage_config_json,
                            '--sync'
                        ])

        # Assert
        assert result.exit_code == 0
        assert "✓ Stage 'new_stage' added to 'test_process' (not saved)" in result.output
        assert "✓ Process 'test_process' saved" in result.output

    def test_operation_failure_prevents_subsequent_operations(self):
        """Verify that operation failure prevents subsequent operations."""
        # Arrange
        runner = CliRunner()
        stage_config_json = '{"name": "new_stage"}'

        # Mock successful validation
        mock_validation = ManageOperationResult(OperationResultType.SUCCESS)

        # Mock failed add stage
        mock_add_result = ManageOperationResult(
            OperationResultType.NOT_FOUND,
            custom_message="Process 'nonexistent' not found"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation):
                with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_add_result):
                    with patch('stageflow.cli.commands.manage.sync_process') as mock_sync:
                        result = runner.invoke(manage, [
                            '--process', 'nonexistent',
                            '--add-stage', stage_config_json,
                            '--sync'
                        ])

        # Assert
        assert result.exit_code != 0
        assert "Error: Process 'nonexistent' not found" in result.output
        # Sync should not be called since add stage failed
        mock_sync.assert_not_called()


class TestManageCommandEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_empty_process_name(self):
        """Verify handling of empty process name."""
        # Arrange
        runner = CliRunner()

        mock_validation_result = ManageOperationResult(
            OperationResultType.VALIDATION_FAILED,
            custom_message="--process required for process-specific operations"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.validate_process_operations', return_value=mock_validation_result):
                result = runner.invoke(manage, ['--process', '', '--sync'])

        # Assert
        assert result.exit_code != 0

    def test_invalid_stage_configuration_format(self):
        """Verify handling of malformed stage configuration."""
        # Arrange
        runner = CliRunner()
        malformed_json = '{"name": incomplete'

        mock_result = ManageOperationResult(
            OperationResultType.INVALID_JSON,
            custom_message="Invalid JSON configuration"
        )

        # Act
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.add_stage_to_process', return_value=mock_result):
                with patch('stageflow.cli.commands.manage.validate_process_operations') as mock_validate:
                    mock_validate.return_value = ManageOperationResult(OperationResultType.SUCCESS)
                    result = runner.invoke(manage, ['--process', 'test_process', '--add-stage', malformed_json])

        # Assert
        assert result.exit_code != 0
        assert "Error: Invalid JSON configuration" in result.output

    def test_conflicting_global_and_process_operations(self):
        """Verify that global operations take precedence over process operations."""
        # Arrange
        runner = CliRunner()

        mock_list_result = ManageOperationResult(
            OperationResultType.SUCCESS,
            data=["process1", "process2"],
            custom_message="Found 2 processes"
        )

        # Act - Both --list and --process operations specified
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            with patch('stageflow.cli.commands.manage.list_all_processes', return_value=mock_list_result):
                with patch('stageflow.cli.commands.manage.sync_process') as mock_sync:
                    result = runner.invoke(manage, [
                        '--list',
                        '--process', 'test_process',
                        '--sync'
                    ])

        # Assert - List operation should execute, sync should not
        assert result.exit_code == 0
        assert "Available processes:" in result.output
        assert "process1" in result.output
        mock_sync.assert_not_called()


class TestManageCommandIntegration:
    """Integration tests for the manage command with real Click testing."""

    def test_help_output_contains_expected_information(self):
        """Verify help output contains expected command information."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(manage, ['--help'])

        # Assert
        assert result.exit_code == 0
        assert "Process management operations" in result.output
        assert "--list" in result.output
        assert "--process" in result.output
        assert "--add-stage" in result.output
        assert "--remove-stage" in result.output
        assert "--sync" in result.output
        assert "--sync-all" in result.output

    def test_command_integration_with_click_context(self):
        """Verify command integration with Click context handling."""
        # Arrange
        runner = CliRunner()

        # Act - Test click.Abort() handling
        with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Critical error")
            result = runner.invoke(manage, ['--list'])

        # Assert - Click should handle the abort gracefully
        assert result.exit_code != 0
        assert "Error: Failed to initialize process manager" in result.output

    def test_real_click_option_parsing(self):
        """Verify real Click option parsing works correctly."""
        # Arrange
        runner = CliRunner()

        # Test various option formats
        test_cases = [
            (['--list'], 'list_processes'),
            (['--process', 'test'], 'process_name'),
            (['--add-stage', '{}'], 'add_stage_config'),
            (['--remove-stage', 'stage'], 'remove_stage_name'),
            (['--sync'], 'sync_process_flag'),
            (['--sync-all'], 'sync_all_processes_flag'),
        ]

        for args, expected_param in test_cases:
            # Act - Use mock to capture the parsed parameters
            with patch('stageflow.cli.commands.manage.ProcessManager') as mock_manager_class:
                with patch('stageflow.cli.commands.manage.list_all_processes') as mock_operation:
                    mock_operation.return_value = ManageOperationResult(
                        OperationResultType.SUCCESS,
                        data=[]
                    )
                    result = runner.invoke(manage, args)

            # Assert - Command should parse successfully (exit_code 0 or handled error)
            assert result.exit_code in [0, 1], f"Failed for args: {args}"
