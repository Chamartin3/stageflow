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
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from stageflow.manager.config import ManagerConfig
from stageflow.manager.registry import ProcessRegistry, ProcessRegistryError
from stageflow.process import Process


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
            assert hasattr(registry, "_yaml")

    def test_registry_yaml_configuration(self):
        """Verify registry has properly configured YAML instance."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))

            # Act
            registry = ProcessRegistry(config)

            # Assert
            assert hasattr(registry, "_yaml")
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
        config = ManagerConfig(
            processes_dir=Path("/nonexistent/directory"), create_dir_if_missing=False
        )
        registry = ProcessRegistry(config)

        # Act & Assert
        with pytest.raises(
            ProcessRegistryError, match="Processes directory not accessible"
        ):
            registry.list_processes()

    def test_list_processes_with_os_error_raises_registry_error(self):
        """Verify list_processes raises ProcessRegistryError on OSError."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ManagerConfig(processes_dir=Path(tmp_dir))
            registry = ProcessRegistry(config)

            # Act & Assert
            with patch.object(
                Path, "iterdir", side_effect=OSError("Permission denied")
            ):
                with pytest.raises(
                    ProcessRegistryError, match="Failed to list processes"
                ):
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
            with patch.object(Path, "exists", side_effect=OSError("Permission denied")):
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
                        "fields": {"input": {"type": "str"}},
                        "gates": [
                            {
                                "name": "proceed",
                                "target_stage": "end",
                                "locks": [{"exists": "input"}],
                            }
                        ],
                    },
                    "end": {"name": "End Stage", "is_final": True, "gates": []},
                },
                "initial_stage": "start",
                "final_stage": "end",
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
            with open(process_file, "w") as f:
                yaml_handler = YAML(typ="safe", pure=True)
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
            with open(process_file, "w") as f:
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
            with pytest.raises(
                ProcessRegistryError, match="Process 'nonexistent' not found"
            ):
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
            with pytest.raises(
                ProcessRegistryError, match="Failed to load process 'invalid'"
            ):
                registry.load_process("invalid")
