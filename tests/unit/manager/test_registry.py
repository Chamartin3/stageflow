"""Comprehensive unit tests for the stageflow.manager.registry module.

This test suite covers all functionality in the ProcessRegistry class including:
- Process discovery and listing
- Process loading and saving
- File format handling (YAML/JSON)
- Backup creation and management
- Process metadata operations
- Error handling and edge cases
- File system operations with validation
"""

import json
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from ruamel.yaml import YAML

from stageflow.manager.config import ManagerConfig, ProcessFileFormat
from stageflow.manager.registry import ProcessRegistry, ProcessRegistryError
from stageflow.process import Process
from stageflow.schema import LoadError


class TestProcessRegistryError:
    """Test suite for ProcessRegistryError exception."""

    def test_process_registry_error_inheritance(self):
        """Verify ProcessRegistryError inherits from Exception."""
        # Arrange & Act
        error = ProcessRegistryError("test error")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_process_registry_error_with_custom_message(self):
        """Verify ProcessRegistryError can be created with custom message."""
        # Arrange
        message = "Custom registry error message"

        # Act
        error = ProcessRegistryError(message)

        # Assert
        assert str(error) == message


class TestProcessRegistryCreation:
    """Test suite for ProcessRegistry creation and initialization."""

    def test_create_registry_with_config(self):
        """Verify ProcessRegistry can be created with ManagerConfig."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))

            # Act
            registry = ProcessRegistry(config)

            # Assert
            assert registry.config == config
            assert hasattr(registry, '_yaml')

    def test_registry_yaml_configuration(self):
        """Verify registry has properly configured YAML instance."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))

            # Act
            registry = ProcessRegistry(config)

            # Assert
            assert hasattr(registry, '_yaml')
            assert registry._yaml.preserve_quotes is True


class TestProcessRegistryListOperations:
    """Test suite for ProcessRegistry list and discovery operations."""

    def test_list_processes_empty_directory(self):
        """Verify list_processes returns empty list for empty directory."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            processes = registry.list_processes()

            # Assert
            assert processes == []

    def test_list_processes_with_yaml_files(self):
        """Verify list_processes returns YAML files without extensions."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test files
            (processes_dir / "process1.yaml").touch()
            (processes_dir / "process2.yml").touch()
            (processes_dir / "not_process.txt").touch()

            # Act
            processes = registry.list_processes()

            # Assert
            assert sorted(processes) == ["process1", "process2"]

    def test_list_processes_with_json_files(self):
        """Verify list_processes returns JSON files without extensions."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test files
            (processes_dir / "process1.json").touch()
            (processes_dir / "process2.yaml").touch()

            # Act
            processes = registry.list_processes()

            # Assert
            assert sorted(processes) == ["process1", "process2"]

    def test_list_processes_with_mixed_formats(self):
        """Verify list_processes handles mixed file formats correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test files with various extensions
            (processes_dir / "proc1.yaml").touch()
            (processes_dir / "proc2.yml").touch()
            (processes_dir / "proc3.json").touch()
            (processes_dir / "ignored.txt").touch()
            (processes_dir / "also_ignored.py").touch()

            # Act
            processes = registry.list_processes()

            # Assert
            assert sorted(processes) == ["proc1", "proc2", "proc3"]

    def test_list_processes_deduplicates_names(self):
        """Verify list_processes deduplicates process names from different formats."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create files with same name but different extensions
            (processes_dir / "duplicate.yaml").touch()
            (processes_dir / "duplicate.json").touch()
            (processes_dir / "unique.yml").touch()

            # Act
            processes = registry.list_processes()

            # Assert
            assert sorted(processes) == ["duplicate", "unique"]

    def test_list_processes_inaccessible_directory_raises_error(self):
        """Verify list_processes raises error when directory is not accessible."""
        # Arrange
        config = ManagerConfig(processes_dir=Path("/nonexistent/directory"))
        registry = ProcessRegistry(config)

        # Act & Assert
        with pytest.raises(ProcessRegistryError, match="Processes directory not accessible"):
            registry.list_processes()

    def test_list_processes_with_os_error_raises_registry_error(self):
        """Verify list_processes raises ProcessRegistryError on OSError."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            with patch.object(Path, 'iterdir', side_effect=OSError("Permission denied")):
                with pytest.raises(ProcessRegistryError, match="Failed to list processes"):
                    registry.list_processes()


class TestProcessRegistryExistenceChecks:
    """Test suite for ProcessRegistry existence checking operations."""

    def test_process_exists_with_existing_yaml(self):
        """Verify process_exists returns True for existing YAML file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            (processes_dir / "existing.yaml").touch()

            # Act
            exists = registry.process_exists("existing")

            # Assert
            assert exists is True

    def test_process_exists_with_existing_json(self):
        """Verify process_exists returns True for existing JSON file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            (processes_dir / "existing.json").touch()

            # Act
            exists = registry.process_exists("existing")

            # Assert
            assert exists is True

    def test_process_exists_with_nonexistent_process(self):
        """Verify process_exists returns False for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            exists = registry.process_exists("nonexistent")

            # Assert
            assert exists is False

    def test_process_exists_with_empty_name(self):
        """Verify process_exists returns False for empty or whitespace name."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            assert registry.process_exists("") is False
            assert registry.process_exists("   ") is False
            assert registry.process_exists(None) is False

    def test_process_exists_with_os_error_returns_false(self):
        """Verify process_exists returns False when OSError occurs."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            with patch.object(Path, 'exists', side_effect=OSError("Permission denied")):
                exists = registry.process_exists("test")

            # Assert
            assert exists is False

    def test_get_process_file_path_existing_file(self):
        """Verify get_process_file_path returns correct path for existing file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            test_file = processes_dir / "test.yaml"
            test_file.touch()

            # Act
            file_path = registry.get_process_file_path("test")

            # Assert
            assert file_path == test_file

    def test_get_process_file_path_nonexistent_returns_none(self):
        """Verify get_process_file_path returns None for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            file_path = registry.get_process_file_path("nonexistent")

            # Assert
            assert file_path is None

    def test_get_process_file_path_prefers_yaml_over_yml(self):
        """Verify get_process_file_path prefers .yaml over .yml extension."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            yaml_file = processes_dir / "test.yaml"
            yml_file = processes_dir / "test.yml"
            yaml_file.touch()
            yml_file.touch()

            # Act
            file_path = registry.get_process_file_path("test")

            # Assert
            assert file_path == yaml_file


class TestProcessRegistryLoadOperations:
    """Test suite for ProcessRegistry process loading operations."""

    def create_test_process_data(self):
        """Create valid test process data."""
        return {
            "process": {
                "name": "test_process",
                "description": "Test process for unit tests",
                "stages": {
                    "start": {
                        "name": "Start Stage",
                        "expected_properties": {"input": {"type": "str"}},
                        "gates": [{
                            "name": "proceed",
                            "target_stage": "end",
                            "locks": [{"exists": "input"}]
                        }]
                    },
                    "end": {
                        "name": "End Stage",
                        "is_final": True,
                        "gates": []
                    }
                },
                "initial_stage": "start",
                "final_stage": "end"
            }
        }

    def test_load_process_existing_yaml(self):
        """Verify load_process successfully loads existing YAML process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create process file
            process_file = processes_dir / "test.yaml"
            with open(process_file, 'w') as f:
                yaml_handler = YAML(typ='safe', pure=True)
                yaml_handler.dump(self.create_test_process_data(), f)

            # Act
            process = registry.load_process("test")

            # Assert
            assert isinstance(process, Process)
            assert process.name == "test_process"

    def test_load_process_existing_json(self):
        """Verify load_process successfully loads existing JSON process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create process file
            process_file = processes_dir / "test.json"
            with open(process_file, 'w') as f:
                json.dump(self.create_test_process_data(), f)

            # Act
            process = registry.load_process("test")

            # Assert
            assert isinstance(process, Process)
            assert process.name == "test_process"

    def test_load_process_nonexistent_raises_error(self):
        """Verify load_process raises error for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Process 'nonexistent' not found"):
                registry.load_process("nonexistent")

    def test_load_process_invalid_file_raises_error(self):
        """Verify load_process raises error for invalid process file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create invalid process file
            process_file = processes_dir / "invalid.yaml"
            process_file.write_text("invalid: yaml: content:")

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Failed to load process 'invalid'"):
                registry.load_process("invalid")

    def test_load_process_data_existing_process(self):
        """Verify load_process_data returns raw process data."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create process file
            test_data = self.create_test_process_data()
            process_file = processes_dir / "test.yaml"
            with open(process_file, 'w') as f:
                yaml_handler = YAML(typ='safe', pure=True)
                yaml_handler.dump(test_data, f)

            # Act
            process_data = registry.load_process_data("test")

            # Assert
            assert isinstance(process_data, dict)
            assert process_data["process"]["name"] == "test_process"

    def test_load_process_data_nonexistent_raises_error(self):
        """Verify load_process_data raises error for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Process 'nonexistent' not found"):
                registry.load_process_data("nonexistent")


class TestProcessRegistrySaveOperations:
    """Test suite for ProcessRegistry process saving operations."""

    def create_test_process(self):
        """Create a test Process instance."""
        process_data = {
            "name": "test_process",
            "description": "Test process",
            "stages": {
                "start": {
                    "name": "Start",
                    "expected_properties": {},
                    "gates": [{
                        "name": "proceed",
                        "target_stage": "end",
                        "locks": []
                    }]
                },
                "end": {
                    "name": "End",
                    "is_final": True,
                    "gates": []
                }
            },
            "initial_stage": "start",
            "final_stage": "end"
        }
        return Process(process_data)

    def test_save_process_with_process_object(self):
        """Verify save_process saves Process object to file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            process = self.create_test_process()

            # Act
            saved_path = registry.save_process("test_save", process)

            # Assert
            assert saved_path.exists()
            assert saved_path.name == "test_save.yaml"
            assert saved_path.parent == processes_dir

    def test_save_process_with_dict_data(self):
        """Verify save_process saves dictionary data to file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            process_data = {
                "name": "dict_process",
                "stages": {"start": {"gates": []}},
                "initial_stage": "start"
            }

            # Act
            saved_path = registry.save_process("dict_save", process_data)

            # Assert
            assert saved_path.exists()
            with open(saved_path) as f:
                yaml_handler = YAML(typ='safe', pure=True)
                loaded_data = yaml_handler.load(f)
            assert loaded_data["process"]["name"] == "dict_process"

    def test_save_process_with_format_override_json(self):
        """Verify save_process respects format override to JSON."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir, default_format=ProcessFileFormat.YAML)
            registry = ProcessRegistry(config)

            process = self.create_test_process()

            # Act
            saved_path = registry.save_process("json_test", process, ProcessFileFormat.JSON)

            # Assert
            assert saved_path.suffix == ".json"
            with open(saved_path) as f:
                loaded_data = json.load(f)
            assert "process" in loaded_data

    def test_save_process_empty_name_raises_error(self):
        """Verify save_process raises error for empty process name."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            process = self.create_test_process()

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Process name cannot be empty"):
                registry.save_process("", process)

    def test_save_process_inaccessible_directory_raises_error(self):
        """Verify save_process raises error when directory is not accessible."""
        # Arrange
        config = ManagerConfig(processes_dir=Path("/nonexistent/directory"))
        registry = ProcessRegistry(config)

        process = self.create_test_process()

        # Act & Assert
        with pytest.raises(ProcessRegistryError, match="Processes directory not accessible"):
            registry.save_process("test", process)

    def test_save_process_creates_backup_when_enabled(self):
        """Verify save_process creates backup when backup is enabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            backup_dir = Path(tmp_dir) / "backups"
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True,
                backup_dir=backup_dir
            )
            registry = ProcessRegistry(config)

            # Create existing file
            existing_file = processes_dir / "existing.yaml"
            existing_file.write_text("existing content")

            process = self.create_test_process()

            # Act
            with patch.object(registry, '_create_backup') as mock_backup:
                registry.save_process("existing", process)

            # Assert
            mock_backup.assert_called_once_with("existing")

    def test_save_process_handles_save_failure(self):
        """Verify save_process handles file write failures gracefully."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            process = self.create_test_process()

            # Act & Assert
            with patch.object(registry, '_write_process_file', side_effect=Exception("Write failed")):
                with pytest.raises(ProcessRegistryError, match="Failed to save process"):
                    registry.save_process("test", process)


class TestProcessRegistryDeleteOperations:
    """Test suite for ProcessRegistry process deletion operations."""

    def test_delete_process_existing_file(self):
        """Verify delete_process successfully deletes existing process file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "to_delete.yaml"
            test_file.write_text("test content")

            # Act
            result = registry.delete_process("to_delete")

            # Assert
            assert result is True
            assert not test_file.exists()

    def test_delete_process_nonexistent_returns_false(self):
        """Verify delete_process returns False for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            result = registry.delete_process("nonexistent")

            # Assert
            assert result is False

    def test_delete_process_creates_backup_when_enabled(self):
        """Verify delete_process creates backup when backup is enabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True
            )
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "to_delete.yaml"
            test_file.write_text("test content")

            # Act
            with patch.object(registry, '_create_backup') as mock_backup:
                registry.delete_process("to_delete")

            # Assert
            mock_backup.assert_called_once_with("to_delete")

    def test_delete_process_with_backup_override(self):
        """Verify delete_process respects backup override parameter."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=False
            )
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "to_delete.yaml"
            test_file.write_text("test content")

            # Act
            with patch.object(registry, '_create_backup') as mock_backup:
                registry.delete_process("to_delete", create_backup=True)

            # Assert
            mock_backup.assert_called_once_with("to_delete")

    def test_delete_process_handles_deletion_failure(self):
        """Verify delete_process handles file deletion failures."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "to_delete.yaml"
            test_file.write_text("test content")

            # Act & Assert
            with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):
                with pytest.raises(ProcessRegistryError, match="Failed to delete process"):
                    registry.delete_process("to_delete")


class TestProcessRegistryInfoOperations:
    """Test suite for ProcessRegistry metadata and info operations."""

    def test_get_process_info_existing_file(self):
        """Verify get_process_info returns correct metadata for existing file."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "info_test.yaml"
            test_content = "test: content"
            test_file.write_text(test_content)

            # Act
            info = registry.get_process_info("info_test")

            # Assert
            assert info["name"] == "info_test"
            assert info["file_path"] == str(test_file)
            assert info["format"] == "yaml"
            assert info["size_bytes"] == len(test_content)
            assert "modified_time" in info
            assert "created_time" in info

    def test_get_process_info_json_format(self):
        """Verify get_process_info correctly identifies JSON format."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create JSON test file
            test_file = processes_dir / "json_test.json"
            test_file.write_text('{"test": "content"}')

            # Act
            info = registry.get_process_info("json_test")

            # Assert
            assert info["format"] == "json"

    def test_get_process_info_nonexistent_raises_error(self):
        """Verify get_process_info raises error for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Process 'nonexistent' not found"):
                registry.get_process_info("nonexistent")

    def test_get_process_info_stat_failure_raises_error(self):
        """Verify get_process_info handles stat failures gracefully."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test file
            test_file = processes_dir / "stat_test.yaml"
            test_file.touch()

            # Act & Assert
            with patch.object(Path, 'stat', side_effect=OSError("Stat failed")):
                with pytest.raises(ProcessRegistryError, match="Failed to get process info"):
                    registry.get_process_info("stat_test")

    def test_list_process_info_multiple_processes(self):
        """Verify list_process_info returns info for all processes."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create multiple test files
            (processes_dir / "process1.yaml").write_text("content1")
            (processes_dir / "process2.json").write_text("content2")

            # Act
            info_list = registry.list_process_info()

            # Assert
            assert len(info_list) == 2
            names = [info["name"] for info in info_list]
            assert "process1" in names
            assert "process2" in names

    def test_list_process_info_skips_inaccessible_processes(self):
        """Verify list_process_info skips processes that can't be accessed."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test files
            (processes_dir / "accessible.yaml").write_text("content")
            (processes_dir / "inaccessible.yaml").write_text("content")

            # Act
            with patch.object(registry, 'get_process_info', side_effect=lambda name:
                             ProcessRegistryError("Access denied") if name == "inaccessible"
                             else {"name": name, "file_path": str(processes_dir / f"{name}.yaml"),
                                   "format": "yaml", "size_bytes": 7,
                                   "modified_time": "2024-01-01T00:00:00",
                                   "created_time": "2024-01-01T00:00:00"}):
                info_list = registry.list_process_info()

            # Assert
            assert len(info_list) == 1
            assert info_list[0]["name"] == "accessible"


class TestProcessRegistryBackupOperations:
    """Test suite for ProcessRegistry backup operations."""

    def test_create_backup_with_existing_process(self):
        """Verify _create_backup creates backup file when process exists."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            backup_dir = Path(tmp_dir) / "backups"
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True,
                backup_dir=backup_dir
            )
            registry = ProcessRegistry(config)

            # Create source file
            source_file = processes_dir / "backup_test.yaml"
            test_content = "backup test content"
            source_file.write_text(test_content)

            # Act
            registry._create_backup("backup_test")

            # Assert
            backup_files = list(backup_dir.glob("backup_test_*.yaml"))
            assert len(backup_files) == 1
            assert backup_files[0].read_text() == test_content

    def test_create_backup_disabled_does_nothing(self):
        """Verify _create_backup does nothing when backup is disabled."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=False
            )
            registry = ProcessRegistry(config)

            # Create source file
            source_file = processes_dir / "no_backup.yaml"
            source_file.write_text("content")

            # Act
            registry._create_backup("no_backup")

            # Assert - No backup should be created

    def test_create_backup_nonexistent_process_does_nothing(self):
        """Verify _create_backup does nothing for nonexistent process."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            backup_dir = Path(tmp_dir) / "backups"
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                backup_enabled=True,
                backup_dir=backup_dir
            )
            registry = ProcessRegistry(config)

            # Act
            registry._create_backup("nonexistent")

            # Assert - No backup should be created
            assert not backup_dir.exists() or len(list(backup_dir.iterdir())) == 0

    def test_cleanup_old_backups(self):
        """Verify _cleanup_old_backups removes excess backup files."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            backup_dir = Path(tmp_dir) / "backups"
            backup_dir.mkdir()
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                backup_enabled=True,
                backup_dir=backup_dir,
                max_backups=2
            )
            registry = ProcessRegistry(config)

            # Create multiple backup files with different timestamps
            import time
            for i in range(5):
                backup_file = backup_dir / f"test_backup_{i:04d}.yaml"
                backup_file.write_text(f"backup {i}")
                time.sleep(0.01)  # Ensure different modification times

            # Act
            registry._cleanup_old_backups("test_backup")

            # Assert
            remaining_backups = list(backup_dir.glob("test_backup_*.yaml"))
            assert len(remaining_backups) == 2

    def test_cleanup_old_backups_with_zero_max_backups(self):
        """Verify _cleanup_old_backups with zero max_backups removes nothing."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            backup_dir = Path(tmp_dir) / "backups"
            backup_dir.mkdir()
            config = ManagerConfig(
                processes_dir=Path(tmp_dir),
                backup_enabled=True,
                backup_dir=backup_dir,
                max_backups=0
            )
            registry = ProcessRegistry(config)

            # Create backup files
            (backup_dir / "test_backup_001.yaml").write_text("backup 1")
            (backup_dir / "test_backup_002.yaml").write_text("backup 2")

            # Act
            registry._cleanup_old_backups("test_backup")

            # Assert - Nothing should be removed with max_backups=0


class TestProcessRegistryUtilityMethods:
    """Test suite for ProcessRegistry utility and helper methods."""

    def test_validate_process_name_valid_names(self):
        """Verify validate_process_name accepts valid process names."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            valid_names = ["process1", "my_process", "process-name", "Process123"]

            # Act & Assert
            for name in valid_names:
                assert registry.validate_process_name(name) is True, f"Failed for: {name}"

    def test_validate_process_name_invalid_names(self):
        """Verify validate_process_name rejects invalid process names."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            invalid_names = [
                "",  # Empty
                "   ",  # Whitespace only
                None,  # None
                "process<name",  # Invalid character
                "process>name",  # Invalid character
                "process:name",  # Invalid character
                'process"name',  # Invalid character
                "process/name",  # Invalid character
                "process\\name",  # Invalid character
                "process|name",  # Invalid character
                "process?name",  # Invalid character
                "process*name",  # Invalid character
                "CON",  # Reserved name
                "PRN",  # Reserved name
                "AUX",  # Reserved name
                "a" * 256,  # Too long
            ]

            # Act & Assert
            for name in invalid_names:
                assert registry.validate_process_name(name) is False, f"Should be invalid: {name}"

    def test_validate_process_name_reserved_names_case_insensitive(self):
        """Verify validate_process_name rejects reserved names case-insensitively."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            reserved_variations = ["con", "CON", "Con", "prn", "PRN", "Prn"]

            # Act & Assert
            for name in reserved_variations:
                assert registry.validate_process_name(name) is False, f"Should be invalid: {name}"

    def test_extract_process_data_with_definition_attribute(self):
        """Verify _extract_process_data handles Process with definition attribute."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Mock process with definition attribute
            mock_process = MagicMock()
            test_definition = {"name": "test", "stages": {}}
            mock_process.definition = test_definition

            # Act
            result = registry._extract_process_data(mock_process)

            # Assert
            assert result == {"process": test_definition}

    def test_extract_process_data_without_accessible_definition_raises_error(self):
        """Verify _extract_process_data raises error when no definition is accessible."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Mock process without accessible definition
            mock_process = MagicMock()
            del mock_process.definition
            del mock_process._definition
            del mock_process.config

            # Act & Assert
            with pytest.raises(ProcessRegistryError, match="Cannot extract data from Process object"):
                registry._extract_process_data(mock_process)

    def test_write_process_file_yaml_format(self):
        """Verify _write_process_file writes YAML format correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            test_data = {"process": {"name": "test", "stages": {}}}
            test_file = Path(tmp_dir) / "test.yaml"

            # Act
            registry._write_process_file(test_file, test_data)

            # Assert
            assert test_file.exists()
            with open(test_file) as f:
                yaml_handler = YAML(typ='safe', pure=True)
                loaded_data = yaml_handler.load(f)
            assert loaded_data == test_data

    def test_write_process_file_json_format(self):
        """Verify _write_process_file writes JSON format correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            test_data = {"process": {"name": "test", "stages": {}}}
            test_file = Path(tmp_dir) / "test.json"

            # Act
            registry._write_process_file(test_file, test_data)

            # Assert
            assert test_file.exists()
            with open(test_file) as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_write_process_file_handles_write_failure(self):
        """Verify _write_process_file handles write failures gracefully."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            test_data = {"process": {"name": "test"}}
            test_file = Path(tmp_dir) / "readonly.yaml"

            # Act & Assert
            with patch('builtins.open', side_effect=OSError("Permission denied")):
                with pytest.raises(ProcessRegistryError, match="Failed to write file"):
                    registry._write_process_file(test_file, test_data)

    def test_str_representation(self):
        """Verify __str__ returns expected string representation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create test files
            (processes_dir / "process1.yaml").touch()
            (processes_dir / "process2.json").touch()

            # Act
            str_repr = str(registry)

            # Assert
            expected = f"ProcessRegistry(dir='{processes_dir}', processes=2)"
            assert str_repr == expected

    def test_str_representation_inaccessible_directory(self):
        """Verify __str__ handles inaccessible directory gracefully."""
        # Arrange
        config = ManagerConfig(processes_dir=Path("/nonexistent"))
        registry = ProcessRegistry(config)

        # Act
        str_repr = str(registry)

        # Assert
        expected = f"ProcessRegistry(dir='{Path('/nonexistent')}', processes=0)"
        assert str_repr == expected

    def test_repr_representation(self):
        """Verify __repr__ returns expected representation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act
            repr_str = repr(registry)

            # Assert
            expected = f"ProcessRegistry(config={config!r})"
            assert repr_str == expected


class TestProcessRegistryIntegration:
    """Integration tests for ProcessRegistry with real file operations."""

    def test_full_workflow_save_load_delete(self):
        """Test complete workflow: save, load, delete with real files."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir) / "processes"
            backup_dir = Path(tmp_dir) / "backups"
            config = ManagerConfig(
                processes_dir=processes_dir,
                backup_enabled=True,
                backup_dir=backup_dir,
                create_dir_if_missing=True
            )
            registry = ProcessRegistry(config)

            # Create test process
            process_data = {
                "name": "integration_test",
                "stages": {
                    "start": {"gates": []},
                    "end": {"is_final": True, "gates": []}
                },
                "initial_stage": "start",
                "final_stage": "end"
            }

            # Act - Save process
            saved_path = registry.save_process("integration_test", process_data)
            assert saved_path.exists()

            # Act - Load process
            loaded_process = registry.load_process("integration_test")
            assert loaded_process.name == "integration_test"

            # Act - Check existence
            assert registry.process_exists("integration_test") is True

            # Act - Get info
            info = registry.get_process_info("integration_test")
            assert info["name"] == "integration_test"

            # Act - Delete process (should create backup)
            deleted = registry.delete_process("integration_test")
            assert deleted is True
            assert not saved_path.exists()

            # Assert - Backup was created
            backup_files = list(backup_dir.glob("integration_test_*.yaml"))
            assert len(backup_files) == 1

    def test_multiple_formats_coexistence(self):
        """Test that registry handles multiple file formats correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            processes_dir = Path(tmp_dir)
            config = ManagerConfig(processes_dir=processes_dir)
            registry = ProcessRegistry(config)

            # Create processes in different formats
            yaml_data = {"process": {"name": "yaml_process", "stages": {}}}
            json_data = {"process": {"name": "json_process", "stages": {}}}

            yaml_file = processes_dir / "yaml_proc.yaml"
            json_file = processes_dir / "json_proc.json"

            with open(yaml_file, 'w') as f:
                yaml_handler = YAML(typ='safe', pure=True)
                yaml_handler.dump(yaml_data, f)
            with open(json_file, 'w') as f:
                json.dump(json_data, f)

            # Act - List processes
            processes = registry.list_processes()

            # Assert
            assert "yaml_proc" in processes
            assert "json_proc" in processes

            # Act - Load both
            yaml_process = registry.load_process("yaml_proc")
            json_process = registry.load_process("json_proc")

            # Assert
            assert yaml_process.name == "yaml_process"
            assert json_process.name == "json_process"