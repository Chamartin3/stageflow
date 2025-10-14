"""Comprehensive unit tests for the stageflow.manager.config module.

This test suite covers all functionality in the ManagerConfig class including:
- Configuration creation and validation
- Environment variable configuration
- Dictionary-based configuration
- File path handling and directory creation
- Error handling and edge cases
- Type safety and validation
"""

import os
import pytest
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from stageflow.manager.config import (
    ManagerConfig,
    ConfigValidationError,
    ProcessFileFormat,
    ManagerConfigDict
)


class TestProcessFileFormat:
    """Test suite for ProcessFileFormat enum."""

    def test_process_file_format_values(self):
        """Verify ProcessFileFormat has correct string values."""
        # Arrange & Act & Assert
        assert ProcessFileFormat.YAML == "yaml"
        assert ProcessFileFormat.JSON == "json"
        assert ProcessFileFormat.AUTO == "auto"

    def test_process_file_format_membership(self):
        """Verify ProcessFileFormat enum membership."""
        # Arrange & Act
        formats = list(ProcessFileFormat)

        # Assert
        assert len(formats) == 3
        assert ProcessFileFormat.YAML in formats
        assert ProcessFileFormat.JSON in formats
        assert ProcessFileFormat.AUTO in formats


class TestConfigValidationError:
    """Test suite for ConfigValidationError exception."""

    def test_config_validation_error_inheritance(self):
        """Verify ConfigValidationError inherits from Exception."""
        # Arrange & Act
        error = ConfigValidationError("test error")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_config_validation_error_with_message(self):
        """Verify ConfigValidationError can be created with custom message."""
        # Arrange
        message = "Custom validation error message"

        # Act
        error = ConfigValidationError(message)

        # Assert
        assert str(error) == message


class TestManagerConfigCreation:
    """Test suite for ManagerConfig creation and initialization."""

    def test_create_config_with_minimal_parameters(self):
        """Verify ManagerConfig can be created with minimal parameters."""
        # Arrange
        processes_dir = Path("/tmp/test_processes")

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(processes_dir=processes_dir)

        # Assert
        assert config.processes_dir == processes_dir
        assert config.default_format == ProcessFileFormat.YAML
        assert config.create_dir_if_missing is True
        assert config.backup_enabled is False
        assert config.backup_dir is None
        assert config.max_backups == 5
        assert config.strict_validation is True
        assert config.auto_fix_permissions is True

    def test_create_config_with_all_parameters(self):
        """Verify ManagerConfig can be created with all parameters."""
        # Arrange
        processes_dir = Path("/tmp/test_processes")
        backup_dir = Path("/tmp/test_backups")

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.JSON,
                    create_dir_if_missing=False,
                    backup_enabled=True,
                    backup_dir=backup_dir,
                    max_backups=10,
                    strict_validation=False,
                    auto_fix_permissions=False
                )

        # Assert
        assert config.processes_dir == processes_dir
        assert config.default_format == ProcessFileFormat.JSON
        assert config.create_dir_if_missing is False
        assert config.backup_enabled is True
        assert config.backup_dir == backup_dir
        assert config.max_backups == 10
        assert config.strict_validation is False
        assert config.auto_fix_permissions is False

    def test_config_is_frozen_dataclass(self):
        """Verify ManagerConfig is a frozen dataclass."""
        # Arrange
        processes_dir = Path("/tmp/test_processes")

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(processes_dir=processes_dir)

        # Assert
        with pytest.raises((AttributeError, FrozenInstanceError), match="cannot assign to field|can't set attribute"):
            config.processes_dir = Path("/different/path")


class TestManagerConfigFromEnv:
    """Test suite for ManagerConfig.from_env() class method."""

    def test_from_env_with_default_values(self):
        """Verify from_env creates config with default values when no env vars set."""
        # Arrange
        env_vars = {}

        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig.from_env()

        # Assert
        assert config.processes_dir == Path('./processes').resolve()
        assert config.default_format == ProcessFileFormat.YAML
        assert config.create_dir_if_missing is True
        assert config.backup_enabled is False
        assert config.backup_dir is None
        assert config.max_backups == 5
        assert config.strict_validation is True
        assert config.auto_fix_permissions is True

    def test_from_env_with_custom_prefix(self):
        """Verify from_env works with custom environment prefix."""
        # Arrange
        env_vars = {
            'CUSTOM_PROCESSES_DIR': '/custom/processes',
            'CUSTOM_DEFAULT_FORMAT': 'json',
            'CUSTOM_CREATE_DIR': 'false',
            'CUSTOM_BACKUP_ENABLED': 'true',
            'CUSTOM_BACKUP_DIR': '/custom/backups',
            'CUSTOM_MAX_BACKUPS': '7',
            'CUSTOM_STRICT_VALIDATION': 'false',
            'CUSTOM_AUTO_FIX_PERMISSIONS': 'false'
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig.from_env(env_prefix='CUSTOM_')

        # Assert
        assert config.processes_dir == Path('/custom/processes').resolve()
        assert config.default_format == ProcessFileFormat.JSON
        assert config.create_dir_if_missing is False
        assert config.backup_enabled is True
        assert config.backup_dir == Path('/custom/backups').resolve()
        assert config.max_backups == 7
        assert config.strict_validation is False
        assert config.auto_fix_permissions is False

    def test_from_env_with_all_stageflow_vars(self):
        """Verify from_env works with all STAGEFLOW_ environment variables."""
        # Arrange
        env_vars = {
            'STAGEFLOW_PROCESSES_DIR': '/stage/processes',
            'STAGEFLOW_DEFAULT_FORMAT': 'auto',
            'STAGEFLOW_CREATE_DIR': 'true',
            'STAGEFLOW_BACKUP_ENABLED': 'yes',
            'STAGEFLOW_BACKUP_DIR': '/stage/backups',
            'STAGEFLOW_MAX_BACKUPS': '3',
            'STAGEFLOW_STRICT_VALIDATION': '1',
            'STAGEFLOW_AUTO_FIX_PERMISSIONS': 'true'
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig.from_env()

        # Assert
        assert config.processes_dir == Path('/stage/processes').resolve()
        assert config.default_format == ProcessFileFormat.AUTO
        assert config.create_dir_if_missing is True
        assert config.backup_enabled is True
        assert config.backup_dir == Path('/stage/backups').resolve()
        assert config.max_backups == 3
        assert config.strict_validation is True
        assert config.auto_fix_permissions is True

    def test_from_env_boolean_parsing_variations(self):
        """Verify from_env correctly parses boolean values in various formats."""
        # Test true values
        for true_val in ['true', 'TRUE', '1', 'yes', 'YES']:
            env_vars = {'STAGEFLOW_CREATE_DIR': true_val}
            with patch.dict(os.environ, env_vars, clear=True):
                with patch.object(ManagerConfig, '_validate_config'):
                    with patch.object(ManagerConfig, '_setup_directories'):
                        config = ManagerConfig.from_env()
                assert config.create_dir_if_missing is True, f"Failed for true value: {true_val}"

        # Test false values
        for false_val in ['false', 'FALSE', '0', 'no', 'NO', 'other']:
            env_vars = {'STAGEFLOW_CREATE_DIR': false_val}
            with patch.dict(os.environ, env_vars, clear=True):
                with patch.object(ManagerConfig, '_validate_config'):
                    with patch.object(ManagerConfig, '_setup_directories'):
                        config = ManagerConfig.from_env()
                assert config.create_dir_if_missing is False, f"Failed for false value: {false_val}"

    def test_from_env_invalid_format_falls_back_to_yaml(self):
        """Verify from_env falls back to YAML for invalid format values."""
        # Arrange
        env_vars = {'STAGEFLOW_DEFAULT_FORMAT': 'invalid_format'}

        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig.from_env()

        # Assert
        assert config.default_format == ProcessFileFormat.YAML

    def test_from_env_with_custom_fallback_dir(self):
        """Verify from_env uses custom fallback directory when provided."""
        # Arrange
        custom_fallback = '/custom/fallback'

        # Act
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig.from_env(fallback_dir=custom_fallback)

        # Assert
        assert config.processes_dir == Path(custom_fallback).resolve()


class TestManagerConfigFromDict:
    """Test suite for ManagerConfig.from_dict() class method."""

    def test_from_dict_with_minimal_config(self):
        """Verify from_dict works with minimal configuration."""
        # Arrange
        config_dict: ManagerConfigDict = {
            'processes_dir': '/test/processes'
        }

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig.from_dict(config_dict)

        # Assert
        assert config.processes_dir == Path('/test/processes').resolve()
        assert config.default_format == ProcessFileFormat.YAML
        assert config.create_dir_if_missing is True

    def test_from_dict_with_complete_config(self):
        """Verify from_dict works with complete configuration."""
        # Arrange
        config_dict: ManagerConfigDict = {
            'processes_dir': '/complete/processes',
            'default_format': 'json',
            'create_dir_if_missing': False,
            'backup_enabled': True,
            'backup_dir': '/complete/backups',
            'max_backups': 8,
            'strict_validation': False,
            'auto_fix_permissions': False
        }

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig.from_dict(config_dict)

        # Assert
        assert config.processes_dir == Path('/complete/processes').resolve()
        assert config.default_format == ProcessFileFormat.JSON
        assert config.create_dir_if_missing is False
        assert config.backup_enabled is True
        assert config.backup_dir == Path('/complete/backups').resolve()
        assert config.max_backups == 8
        assert config.strict_validation is False
        assert config.auto_fix_permissions is False

    def test_from_dict_with_invalid_format_raises_error(self):
        """Verify from_dict raises ConfigValidationError for invalid format."""
        # Arrange
        config_dict: ManagerConfigDict = {
            'processes_dir': '/test/processes',
            'default_format': 'invalid_format'
        }

        # Act & Assert
        with pytest.raises(ConfigValidationError, match="Invalid default_format: invalid_format"):
            ManagerConfig.from_dict(config_dict)

    def test_from_dict_with_negative_max_backups_raises_error(self):
        """Verify from_dict raises ConfigValidationError for negative max_backups."""
        # Arrange
        config_dict: ManagerConfigDict = {
            'processes_dir': '/test/processes',
            'max_backups': -1
        }

        # Act & Assert
        with pytest.raises(ConfigValidationError, match="max_backups must be non-negative"):
            ManagerConfig.from_dict(config_dict)

    def test_from_dict_with_empty_dict_uses_defaults(self):
        """Verify from_dict works with empty dictionary using defaults."""
        # Arrange
        config_dict: ManagerConfigDict = {}

        # Act
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig.from_dict(config_dict)

        # Assert
        assert config.processes_dir == Path('./processes').resolve()
        assert config.default_format == ProcessFileFormat.YAML


class TestManagerConfigValidation:
    """Test suite for ManagerConfig validation methods."""

    def test_validate_config_with_valid_configuration(self):
        """Verify _validate_config passes with valid configuration."""
        # Arrange
        processes_dir = Path("/tmp/test_processes")

        # Act & Assert - Should not raise any exceptions
        with patch.object(ManagerConfig, '_setup_directories'):
            config = ManagerConfig(processes_dir=processes_dir)
        # Validation is called in __post_init__

    def test_validate_config_with_empty_processes_dir_raises_error(self):
        """Verify _validate_config raises error for empty processes_dir."""
        # Arrange & Act & Assert
        with pytest.raises(ConfigValidationError, match="processes_dir cannot be empty"):
            with patch.object(ManagerConfig, '_setup_directories'):
                # Use object.__setattr__ to bypass frozen dataclass to test validation
                config = ManagerConfig.__new__(ManagerConfig)
                object.__setattr__(config, 'processes_dir', None)
                config._validate_config()

    def test_validate_config_with_backup_enabled_sets_default_backup_dir(self):
        """Verify _validate_config sets default backup_dir when backup enabled but no dir set."""
        # Arrange
        processes_dir = Path("/tmp/test_processes")

        # Act
        with patch.object(ManagerConfig, '_setup_directories'):
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True,
                backup_dir=None
            )

        # Assert
        assert config.backup_dir == processes_dir / '.backups'

    def test_validate_config_with_negative_max_backups_raises_error(self):
        """Verify _validate_config raises error for negative max_backups."""
        # Arrange & Act & Assert
        with pytest.raises(ConfigValidationError, match="max_backups must be non-negative"):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig.__new__(ManagerConfig)
                object.__setattr__(config, 'processes_dir', Path("/tmp/test"))
                object.__setattr__(config, 'max_backups', -1)
                object.__setattr__(config, 'default_format', ProcessFileFormat.YAML)
                object.__setattr__(config, 'backup_enabled', False)
                config._validate_config()

    def test_validate_config_with_invalid_format_type_raises_error(self):
        """Verify _validate_config raises error for invalid format type."""
        # Arrange & Act & Assert
        with pytest.raises(ConfigValidationError, match="Invalid default_format"):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig.__new__(ManagerConfig)
                object.__setattr__(config, 'processes_dir', Path("/tmp/test"))
                object.__setattr__(config, 'max_backups', 5)
                object.__setattr__(config, 'default_format', "invalid_format")
                object.__setattr__(config, 'backup_enabled', False)
                config._validate_config()


class TestManagerConfigDirectorySetup:
    """Test suite for ManagerConfig directory setup functionality."""

    def test_setup_directories_creates_processes_dir(self):
        """Verify _setup_directories creates processes directory when create_dir_if_missing is True."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "new_processes"

            # Act
            with patch.object(ManagerConfig, '_validate_config'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    create_dir_if_missing=True
                )

            # Assert
            assert processes_dir.exists()
            assert processes_dir.is_dir()

    def test_setup_directories_does_not_create_when_disabled(self):
        """Verify _setup_directories does not create directory when create_dir_if_missing is False."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "should_not_exist"

            # Act
            with patch.object(ManagerConfig, '_validate_config'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    create_dir_if_missing=False
                )

            # Assert
            assert not processes_dir.exists()

    def test_setup_directories_creates_backup_dir_when_enabled(self):
        """Verify _setup_directories creates backup directory when backup is enabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "processes"
            backup_dir = Path(tmp_dir) / "backups"

            # Act
            with patch.object(ManagerConfig, '_validate_config'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    backup_enabled=True,
                    backup_dir=backup_dir,
                    create_dir_if_missing=True
                )

            # Assert
            assert backup_dir.exists()
            assert backup_dir.is_dir()

    def test_setup_directories_fixes_permissions_when_enabled(self):
        """Verify _setup_directories attempts to fix permissions when auto_fix_permissions is True."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "processes"

            # Act
            with patch.object(ManagerConfig, '_validate_config'):
                with patch('os.access', return_value=False):
                    with patch('os.chmod') as mock_chmod:
                        config = ManagerConfig(
                            processes_dir=processes_dir,
                            auto_fix_permissions=True,
                            create_dir_if_missing=True
                        )

            # Assert
            mock_chmod.assert_called_once_with(processes_dir, 0o755)

    def test_setup_directories_ignores_permission_errors(self):
        """Verify _setup_directories ignores PermissionError when fixing permissions."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "processes"

            # Act & Assert - Should not raise exception
            with patch.object(ManagerConfig, '_validate_config'):
                with patch('os.access', return_value=False):
                    with patch('os.chmod', side_effect=PermissionError("Permission denied")):
                        config = ManagerConfig(
                            processes_dir=processes_dir,
                            auto_fix_permissions=True,
                            create_dir_if_missing=True
                        )

    def test_setup_directories_raises_error_on_oserror(self):
        """Verify _setup_directories raises ConfigValidationError on OSError."""
        # Arrange
        processes_dir = Path("/invalid/path/that/cannot/be/created")

        # Act & Assert
        with pytest.raises(ConfigValidationError, match="Failed to create processes directory"):
            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(Path, 'mkdir', side_effect=OSError("Cannot create directory")):
                    config = ManagerConfig(
                        processes_dir=processes_dir,
                        create_dir_if_missing=True
                    )


class TestManagerConfigFilePaths:
    """Test suite for ManagerConfig file path handling methods."""

    def test_get_process_file_path_with_yaml_format(self):
        """Verify get_process_file_path returns correct path for YAML format."""
        # Arrange
        processes_dir = Path("/tmp/processes")
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.YAML
                )

        # Act
        file_path = config.get_process_file_path("test_process")

        # Assert
        assert file_path == processes_dir / "test_process.yaml"

    def test_get_process_file_path_with_json_format(self):
        """Verify get_process_file_path returns correct path for JSON format."""
        # Arrange
        processes_dir = Path("/tmp/processes")
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.JSON
                )

        # Act
        file_path = config.get_process_file_path("test_process")

        # Assert
        assert file_path == processes_dir / "test_process.json"

    def test_get_process_file_path_with_format_override(self):
        """Verify get_process_file_path respects format override parameter."""
        # Arrange
        processes_dir = Path("/tmp/processes")
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.YAML
                )

        # Act
        file_path = config.get_process_file_path("test_process", ProcessFileFormat.JSON)

        # Assert
        assert file_path == processes_dir / "test_process.json"

    def test_get_process_file_path_with_auto_format_existing_yaml(self):
        """Verify get_process_file_path with AUTO format finds existing YAML file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            existing_file = processes_dir / "test_process.yaml"
            existing_file.touch()

            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig(processes_dir=processes_dir)

            # Act
            file_path = config.get_process_file_path("test_process", ProcessFileFormat.AUTO)

            # Assert
            assert file_path == existing_file

    def test_get_process_file_path_with_auto_format_existing_json(self):
        """Verify get_process_file_path with AUTO format finds existing JSON file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            existing_file = processes_dir / "test_process.json"
            existing_file.touch()

            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig(processes_dir=processes_dir)

            # Act
            file_path = config.get_process_file_path("test_process", ProcessFileFormat.AUTO)

            # Assert
            assert file_path == existing_file

    def test_get_process_file_path_with_auto_format_no_existing_defaults_yaml(self):
        """Verify get_process_file_path with AUTO format defaults to YAML when no file exists."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)

            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig(processes_dir=processes_dir)

            # Act
            file_path = config.get_process_file_path("test_process", ProcessFileFormat.AUTO)

            # Assert
            assert file_path == processes_dir / "test_process.yaml"

    def test_get_backup_path_with_backup_enabled(self):
        """Verify get_backup_path returns correct backup path when backup is enabled."""
        # Arrange
        backup_dir = Path("/tmp/backups")
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=Path("/tmp/processes"),
                    backup_enabled=True,
                    backup_dir=backup_dir
                )

        # Act
        backup_path = config.get_backup_path("test_process", "20240101_120000")

        # Assert
        assert backup_path == backup_dir / "test_process_20240101_120000.yaml"

    def test_get_backup_path_with_backup_disabled_raises_error(self):
        """Verify get_backup_path raises error when backup is disabled."""
        # Arrange
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=Path("/tmp/processes"),
                    backup_enabled=False
                )

        # Act & Assert
        with pytest.raises(ConfigValidationError, match="Backup not enabled"):
            config.get_backup_path("test_process", "20240101_120000")

    def test_get_backup_path_with_no_backup_dir_raises_error(self):
        """Verify get_backup_path raises error when backup is enabled but no backup_dir set."""
        # Arrange
        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=Path("/tmp/processes"),
                    backup_enabled=True,
                    backup_dir=None
                )

        # Act & Assert
        with pytest.raises(ConfigValidationError, match="Backup not enabled"):
            config.get_backup_path("test_process", "20240101_120000")


class TestManagerConfigUtilityMethods:
    """Test suite for ManagerConfig utility methods."""

    def test_is_valid_processes_dir_with_valid_directory(self):
        """Verify is_valid_processes_dir returns True for valid, accessible directory."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)

            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig(processes_dir=processes_dir)

            # Act
            result = config.is_valid_processes_dir()

            # Assert
            assert result is True

    def test_is_valid_processes_dir_with_nonexistent_directory(self):
        """Verify is_valid_processes_dir returns False for nonexistent directory."""
        # Arrange
        processes_dir = Path("/nonexistent/directory")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(processes_dir=processes_dir)

        # Act
        result = config.is_valid_processes_dir()

        # Assert
        assert result is False

    def test_is_valid_processes_dir_with_file_instead_of_directory(self):
        """Verify is_valid_processes_dir returns False when path points to a file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "not_a_directory.txt"
            file_path.touch()

            with patch.object(ManagerConfig, '_validate_config'):
                with patch.object(ManagerConfig, '_setup_directories'):
                    config = ManagerConfig(processes_dir=file_path)

            # Act
            result = config.is_valid_processes_dir()

            # Assert
            assert result is False

    def test_is_valid_processes_dir_with_permission_error(self):
        """Verify is_valid_processes_dir returns False when OSError occurs."""
        # Arrange
        processes_dir = Path("/tmp/test")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(processes_dir=processes_dir)

        # Act
        with patch('os.access', side_effect=OSError("Permission denied")):
            result = config.is_valid_processes_dir()

        # Assert
        assert result is False

    def test_to_dict_conversion(self):
        """Verify to_dict correctly converts configuration to typed dictionary."""
        # Arrange
        processes_dir = Path("/tmp/processes")
        backup_dir = Path("/tmp/backups")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.JSON,
                    create_dir_if_missing=False,
                    backup_enabled=True,
                    backup_dir=backup_dir,
                    max_backups=7,
                    strict_validation=False,
                    auto_fix_permissions=False
                )

        # Act
        result_dict = config.to_dict()

        # Assert
        expected_dict: ManagerConfigDict = {
            'processes_dir': str(processes_dir),
            'default_format': 'json',
            'create_dir_if_missing': False,
            'backup_enabled': True,
            'backup_dir': str(backup_dir),
            'max_backups': 7,
            'strict_validation': False,
            'auto_fix_permissions': False
        }
        assert result_dict == expected_dict

    def test_to_dict_with_none_backup_dir(self):
        """Verify to_dict handles None backup_dir correctly."""
        # Arrange
        processes_dir = Path("/tmp/processes")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    backup_enabled=False,
                    backup_dir=None
                )

        # Act
        result_dict = config.to_dict()

        # Assert
        assert result_dict['backup_dir'] is None

    def test_str_representation(self):
        """Verify __str__ returns expected string representation."""
        # Arrange
        processes_dir = Path("/tmp/processes")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.JSON
                )

        # Act
        str_repr = str(config)

        # Assert
        expected = f"ManagerConfig(processes_dir='{processes_dir}', format=json)"
        assert str_repr == expected

    def test_repr_representation(self):
        """Verify __repr__ returns expected representation."""
        # Arrange
        processes_dir = Path("/tmp/processes")

        with patch.object(ManagerConfig, '_validate_config'):
            with patch.object(ManagerConfig, '_setup_directories'):
                config = ManagerConfig(
                    processes_dir=processes_dir,
                    default_format=ProcessFileFormat.AUTO,
                    backup_enabled=True
                )

        # Act
        repr_str = repr(config)

        # Assert
        expected = (f"ManagerConfig(processes_dir={processes_dir!r}, "
                   f"default_format={ProcessFileFormat.AUTO!r}, "
                   f"backup_enabled=True)")
        assert repr_str == expected


class TestManagerConfigIntegration:
    """Integration tests for ManagerConfig with real file system operations."""

    def test_full_workflow_with_temporary_directory(self):
        """Test complete workflow with real directory creation and validation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            processes_dir = base_dir / "processes"
            backup_dir = base_dir / "backups"

            # Act - Create config that should create directories
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True,
                backup_dir=backup_dir,
                create_dir_if_missing=True
            )

            # Assert - Directories should be created
            assert processes_dir.exists()
            assert backup_dir.exists()
            assert config.is_valid_processes_dir()

            # Test file path methods
            yaml_path = config.get_process_file_path("test", ProcessFileFormat.YAML)
            json_path = config.get_process_file_path("test", ProcessFileFormat.JSON)
            backup_path = config.get_backup_path("test", "20240101_120000")

            assert yaml_path == processes_dir / "test.yaml"
            assert json_path == processes_dir / "test.json"
            assert backup_path == backup_dir / "test_20240101_120000.yaml"

    def test_environment_variable_integration(self):
        """Test integration with environment variables and real directories."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_vars = {
                'STAGEFLOW_PROCESSES_DIR': str(Path(tmp_dir) / "env_processes"),
                'STAGEFLOW_DEFAULT_FORMAT': 'json',
                'STAGEFLOW_BACKUP_ENABLED': 'true',
                'STAGEFLOW_BACKUP_DIR': str(Path(tmp_dir) / "env_backups"),
                'STAGEFLOW_CREATE_DIR': 'true'
            }

            # Act
            with patch.dict(os.environ, env_vars, clear=True):
                config = ManagerConfig.from_env()

            # Assert
            assert config.processes_dir.exists()
            assert config.backup_dir.exists()
            assert config.default_format == ProcessFileFormat.JSON
            assert config.backup_enabled is True
            assert config.is_valid_processes_dir()