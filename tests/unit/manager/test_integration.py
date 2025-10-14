"""
Comprehensive test suite for StageFlow Manager functionality.

This test suite validates the complete manager module integration including:
- Configuration management with environment variables
- Process registry operations with file system
- Process editor with safe mutation and rollback
- Process manager coordination and lifecycle
- CLI utility functions and operations
- End-to-end workflows and error handling
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

import pytest

from stageflow import Element, Process, load_process
from stageflow.manager import (
    ManagerConfig,
    ConfigValidationError,
    ProcessFileFormat,
    ProcessRegistry,
    ProcessRegistryError,
    ProcessEditor,
    ProcessEditorError,
    ValidationFailedError,
    ProcessManager,
    ProcessManagerError,
    ProcessNotFoundError,
)
from stageflow.manager.utils import (
    OperationResultType,
    ManageOperationResult,
    list_all_processes,
    sync_all_processes,
    add_stage_to_process,
    remove_stage_from_process,
    sync_process,
    validate_process_operations,
)


class TestManagerComprehensiveWorkflows:
    """Test complete manager workflows and integration scenarios."""

    @pytest.fixture
    def temp_processes_dir(self):
        """Create temporary directory for process files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_process_definition(self) -> Dict[str, Any]:
        """Create a valid process definition for testing."""
        return {
            "name": "test_process",
            "description": "Test process for manager testing",
            "stages": {
                "start": {
                    "name": "Start Stage",
                    "expected_properties": {"id": {"type": "str"}},
                    "gates": [{
                        "name": "to_middle",
                        "target_stage": "middle",
                        "locks": [{"exists": "id"}]
                    }]
                },
                "middle": {
                    "name": "Middle Stage",
                    "expected_properties": {"status": {"type": "str"}},
                    "gates": [{
                        "name": "to_end",
                        "target_stage": "end",
                        "locks": [{"equals": {"property_path": "status", "expected_value": "ready"}}]
                    }]
                },
                "end": {
                    "name": "End Stage",
                    "expected_properties": {},
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "start",
            "final_stage": "end"
        }

    @pytest.fixture
    def sample_manager_config(self, temp_processes_dir) -> ManagerConfig:
        """Create a manager configuration for testing."""
        return ManagerConfig(
            processes_dir=temp_processes_dir,
            default_format=ProcessFileFormat.YAML,
            create_dir_if_missing=True,
            backup_enabled=True,
            backup_dir=temp_processes_dir / ".backups",
            max_backups=3,
            strict_validation=True,
            auto_fix_permissions=True
        )

    @pytest.fixture
    def sample_element_data(self) -> Dict[str, Any]:
        """Create sample element data for testing."""
        return {
            "id": "test_123",
            "status": "ready",
            "metadata": {"created": "2024-01-01"}
        }

    def test_complete_manager_lifecycle(self, sample_manager_config, sample_process_definition, sample_element_data):
        """Test complete manager lifecycle: create, edit, save, load, validate."""
        # 1. Create manager and registry
        manager = ProcessManager(sample_manager_config)
        assert len(manager.list_processes()) == 0

        # 2. Create new process
        process = Process(sample_process_definition)
        process_name = "lifecycle_test"

        # Save process via registry
        manager.registry.save_process(process, process_name)
        assert process_name in manager.list_processes()

        # 3. Load and validate process works
        loaded_process = manager.load_process(process_name)
        assert loaded_process.definition["name"] == sample_process_definition["name"]

        # Test process evaluation works
        element = Element(sample_element_data)
        result = loaded_process.evaluate(element, "start")
        assert result["stage"] == "start"

        # 4. Edit process - add new stage
        editor = manager.edit_process(process_name)
        assert not editor.is_dirty

        new_stage_config = {
            "name": "validation",
            "expected_properties": {"validated": {"type": "bool"}},
            "gates": [{
                "name": "to_middle",
                "target_stage": "middle",
                "locks": [{"equals": {"property_path": "validated", "expected_value": True}}]
            }]
        }

        success = editor.add_stage("validation", new_stage_config)
        assert success
        assert editor.is_dirty

        # 5. Sync changes to file
        sync_success = manager.sync(process_name)
        assert sync_success
        assert not editor.is_dirty

        # 6. Reload and verify changes persisted
        reloaded_process = manager.load_process(process_name)
        assert "validation" in reloaded_process.definition["stages"]

        # 7. Test process still works after modification
        result = reloaded_process.evaluate(element, "start")
        assert result["stage"] == "start"

    def test_manager_error_handling_and_recovery(self, sample_manager_config, sample_process_definition):
        """Test manager error handling and recovery mechanisms."""
        manager = ProcessManager(sample_manager_config)

        # 1. Test loading non-existent process
        with pytest.raises(ProcessNotFoundError):
            manager.load_process("non_existent")

        # 2. Create process with invalid configuration
        invalid_definition = sample_process_definition.copy()
        invalid_definition["stages"]["start"]["gates"][0]["target_stage"] = "non_existent"

        invalid_process = Process(invalid_definition)

        # Should create but have consistency issues
        assert not invalid_process.checker.valid

        # 3. Test editor rollback on validation failure
        process = Process(sample_process_definition)
        manager.registry.save_process(process, "rollback_test")

        editor = manager.edit_process("rollback_test")
        original_stages = list(editor.process.definition["stages"].keys())

        # Try to add invalid stage (this should rollback)
        invalid_stage = {
            "name": "invalid",
            "expected_properties": {},
            "gates": [{
                "name": "invalid_gate",
                "target_stage": "non_existent_target",
                "locks": [{"exists": "some_field"}]
            }]
        }

        success = editor.add_stage("invalid", invalid_stage)
        assert not success  # Should fail validation and rollback
        assert not editor.is_dirty
        assert list(editor.process.definition["stages"].keys()) == original_stages

    def test_manager_cli_utility_functions(self, sample_manager_config, sample_process_definition):
        """Test CLI utility functions with manager integration."""
        manager = ProcessManager(sample_manager_config)

        # 1. Test list_all_processes with empty registry
        result = list_all_processes(manager)
        assert result.success
        assert result.data == []
        assert "0 processes" in result.message

        # 2. Add a process
        process = Process(sample_process_definition)
        manager.registry.save_process(process, "cli_test")

        # 3. Test list_all_processes with processes
        result = list_all_processes(manager)
        assert result.success
        assert "cli_test" in result.data
        assert "1 processes" in result.message

        # 4. Test add_stage_to_process
        stage_json = json.dumps({
            "name": "new_stage",
            "expected_properties": {"field": {"type": "str"}},
            "gates": []
        })

        result = add_stage_to_process(manager, "cli_test", stage_json)
        assert result.success
        assert "new_stage" in result.data["stage_id"]
        assert "not saved" in result.message  # Should indicate in-memory only

        # 5. Test sync_process
        result = sync_process(manager, "cli_test")
        assert result.success
        assert "saved" in result.message

        # 6. Test remove_stage_from_process
        result = remove_stage_from_process(manager, "cli_test", "new_stage")
        assert result.success
        assert "new_stage" in result.data["stage_name"]

        # 7. Test sync_all_processes
        result = sync_all_processes(manager)
        assert result.success
        assert result.data["cli_test"] == True

    def test_manager_environment_configuration(self, temp_processes_dir):
        """Test environment variable configuration."""
        env_vars = {
            "STAGEFLOW_PROCESSES_DIR": str(temp_processes_dir),
            "STAGEFLOW_DEFAULT_FORMAT": "json",
            "STAGEFLOW_CREATE_DIR": "true",
            "STAGEFLOW_BACKUP_ENABLED": "true",
            "STAGEFLOW_MAX_BACKUPS": "10",
            "STAGEFLOW_STRICT_VALIDATION": "false",
            "STAGEFLOW_AUTO_FIX_PERMISSIONS": "false"
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ManagerConfig.from_env()

            assert config.processes_dir == temp_processes_dir
            assert config.default_format == ProcessFileFormat.JSON
            assert config.backup_enabled == True
            assert config.max_backups == 10
            assert config.strict_validation == False
            assert config.auto_fix_permissions == False

    def test_manager_concurrent_operations(self, sample_manager_config, sample_process_definition):
        """Test manager behavior with concurrent operations."""
        manager = ProcessManager(sample_manager_config)

        # Create process
        process = Process(sample_process_definition)
        manager.registry.save_process(process, "concurrent_test")

        # Get multiple editors for same process
        editor1 = manager.edit_process("concurrent_test")
        editor2 = manager.edit_process("concurrent_test")

        # Should return same editor instance
        assert editor1 is editor2

        # Modify through one editor
        stage_config = {
            "name": "concurrent_stage",
            "expected_properties": {},
            "gates": []
        }

        success = editor1.add_stage("concurrent_stage", stage_config)
        assert success
        assert editor1.is_dirty
        assert editor2.is_dirty  # Same instance

        # Sync through manager
        sync_success = manager.sync("concurrent_test")
        assert sync_success
        assert not editor1.is_dirty
        assert not editor2.is_dirty

    def test_manager_backup_and_recovery(self, sample_manager_config, sample_process_definition):
        """Test backup and recovery functionality."""
        # Enable backups
        config = sample_manager_config
        assert config.backup_enabled

        manager = ProcessManager(config)
        process = Process(sample_process_definition)

        # Save initial process
        manager.registry.save_process(process, "backup_test")

        # Verify backup directory exists
        assert config.backup_dir.exists()

        # Modify and save (should create backup)
        editor = manager.edit_process("backup_test")
        editor.add_stage("backup_stage", {
            "name": "backup_stage",
            "expected_properties": {},
            "gates": []
        })
        manager.sync("backup_test")

        # Check if backup was created
        backup_files = list(config.backup_dir.glob("backup_test_*.yaml"))
        assert len(backup_files) > 0

    def test_manager_validation_and_consistency(self, sample_manager_config):
        """Test validation and consistency checking throughout manager operations."""
        manager = ProcessManager(sample_manager_config)

        # 1. Test with valid process
        valid_definition = {
            "name": "validation_test",
            "description": "Test validation",
            "stages": {
                "start": {
                    "name": "Start",
                    "expected_properties": {},
                    "gates": [{
                        "name": "to_end",
                        "target_stage": "end",
                        "locks": [{"exists": "id"}]
                    }]
                },
                "end": {
                    "name": "End",
                    "expected_properties": {},
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "start",
            "final_stage": "end"
        }

        valid_process = Process(valid_definition)
        assert valid_process.checker.valid

        manager.registry.save_process(valid_process, "valid_process")
        loaded_process = manager.load_process("valid_process")
        assert loaded_process.checker.valid

        # 2. Test editing maintains consistency
        editor = manager.edit_process("valid_process")

        # Add valid stage
        valid_stage = {
            "name": "middle",
            "expected_properties": {"status": {"type": "str"}},
            "gates": [{
                "name": "to_end",
                "target_stage": "end",
                "locks": [{"exists": "status"}]
            }]
        }

        success = editor.add_stage("middle", valid_stage)
        assert success
        assert editor.process.checker.valid

        # 3. Test invalid modification gets rolled back
        invalid_stage = {
            "name": "invalid",
            "expected_properties": {},
            "gates": [{
                "name": "broken_gate",
                "target_stage": "non_existent",
                "locks": [{"exists": "field"}]
            }]
        }

        success = editor.add_stage("invalid", invalid_stage)
        assert not success  # Should fail and rollback
        assert editor.process.checker.valid  # Should still be valid after rollback


class TestManagerModuleExports:
    """Test that manager module exports are properly defined and accessible."""

    def test_manager_module_imports(self):
        """Test all manager module exports can be imported."""
        from stageflow.manager import (
            ManagerConfig,
            ConfigValidationError,
            ProcessFileFormat,
            ManagerConfigDict,
            ProcessEditor,
            ProcessEditorError,
            ValidationFailedError,
            ProcessRegistry,
            ProcessRegistryError,
            ProcessManager,
            ProcessManagerError,
            ProcessNotFoundError,
            ProcessValidationError,
            ProcessSyncError,
        )

        # Verify classes exist and are callable
        assert callable(ManagerConfig)
        assert callable(ProcessEditor)
        assert callable(ProcessRegistry)
        assert callable(ProcessManager)

        # Verify exceptions exist
        assert issubclass(ConfigValidationError, Exception)
        assert issubclass(ProcessEditorError, Exception)
        assert issubclass(ValidationFailedError, ProcessEditorError)
        assert issubclass(ProcessRegistryError, Exception)
        assert issubclass(ProcessManagerError, Exception)
        assert issubclass(ProcessNotFoundError, ProcessManagerError)

    def test_core_stageflow_imports(self):
        """Test core StageFlow imports work correctly."""
        from stageflow import (
            Element,
            Process,
            Stage,
            Gate,
            Lock,
            load_process,
            ProcessDefinition,
            ProcessElementEvaluationResult,
        )

        # Verify classes exist and are callable
        assert callable(Element)
        assert callable(Process)
        assert callable(Stage)
        assert callable(Gate)
        assert callable(Lock)
        assert callable(load_process)

    def test_manager_utils_imports(self):
        """Test manager utility functions can be imported."""
        from stageflow.manager.utils import (
            OperationResultType,
            ManageOperationResult,
            list_all_processes,
            sync_all_processes,
            add_stage_to_process,
            remove_stage_from_process,
            sync_process,
            validate_process_operations,
        )

        # Verify functions exist and are callable
        assert callable(list_all_processes)
        assert callable(sync_all_processes)
        assert callable(add_stage_to_process)
        assert callable(remove_stage_from_process)
        assert callable(sync_process)
        assert callable(validate_process_operations)

        # Verify enums and classes
        assert hasattr(OperationResultType, 'SUCCESS')
        assert callable(ManageOperationResult)

    def test_backwards_compatibility(self):
        """Test that existing code patterns still work."""
        # Test basic StageFlow usage still works
        from stageflow import create_element, Process

        sample_data = {"id": "test", "status": "active"}
        element = create_element(sample_data)
        assert element.get_property("id") == "test"

        # Test process creation still works
        sample_process_def = {
            "name": "compat_test",
            "description": "Compatibility test",
            "stages": {
                "start": {
                    "name": "Start",
                    "expected_properties": {},
                    "gates": [{
                        "name": "to_end",
                        "target_stage": "end",
                        "locks": [{"exists": "id"}]
                    }]
                },
                "end": {
                    "name": "End",
                    "expected_properties": {},
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "start",
            "final_stage": "end"
        }

        process = Process(sample_process_def)
        result = process.evaluate(element, "start")
        assert result["stage"] == "start"

    def test_optional_manager_import(self):
        """Test that manager functionality is optional and doesn't break core functionality."""
        # Core functionality should work without importing manager
        from stageflow import create_element, Process, load_process

        # Manager should be importable separately
        from stageflow.manager import ProcessManager

        # Both should coexist
        sample_data = {"test": "data"}
        element = create_element(sample_data)
        assert element.get_property("test") == "data"

        # Manager should be creatable
        manager = ProcessManager()
        assert manager is not None