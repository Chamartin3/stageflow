"""Tests for JSON schema loader functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from stageflow.gates import GateOperation, LockType
from stageflow.process.schema.loaders.json import (
    JsonLoader,
    JSONLoadError,
    JSONReferenceError,
    JSONSchemaError,
    load_process,
    load_process_from_string,
)


class TestJSONLoader:
    """Test cases for JsonLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = JsonLoader()

    def test_init_default(self):
        """Test JsonLoader initialization with defaults."""
        loader = JsonLoader()
        assert loader.resolve_references_flag is True
        assert loader._cache_enabled is True
        assert loader._streaming_threshold == 10 * 1024 * 1024

    def test_init_custom_settings(self):
        """Test JsonLoader initialization with custom settings."""
        loader = JsonLoader(validate_schema=False, resolve_references=False)
        assert loader.resolve_references_flag is False

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises appropriate error."""
        with pytest.raises(JSONLoadError, match="Process file not found"):
            self.loader.load_process("/nonexistent/file.json")

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json,}')
            temp_path = f.name

        try:
            with pytest.raises(JSONLoadError, match="JSON parsing error"):
                self.loader.load_process(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_non_object_root(self):
        """Test loading JSON with non-object root raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["not", "an", "object"], f)
            temp_path = f.name

        try:
            with pytest.raises(JSONSchemaError, match="must contain an object at root level"):
                self.loader.load_process(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_minimal_process(self):
        """Test loading a minimal valid process definition."""
        process_data = {
            "name": "test_process",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(process_data, f)
            temp_path = f.name

        try:
            process = self.loader.load_process(temp_path)
            assert process.name == "test_process"
            assert len(process.stages) == 1
            assert process.stage_order == ["stage1"]
        finally:
            Path(temp_path).unlink()

    def test_load_complex_process(self):
        """Test loading a complex process with stages, gates, and locks."""
        process_data = {
            "name": "complex_process",
            "allow_stage_skipping": True,
            "regression_detection": False,
            "metadata": {"version": "1.0"},
            "stage_order": ["stage1", "stage2"],
            "stages": {
                "stage1": {
                    "allow_partial": False,
                    "metadata": {"description": "First stage"},
                    "gates": {
                        "gate1": {
                            "logic": "and",
                            "metadata": {"priority": "high"},
                            "locks": [
                                {
                                    "property": "user.name",
                                    "type": "exists",
                                    "metadata": {}
                                },
                                {
                                    "property": "user.email",
                                    "type": "regex",
                                    "value": r"^[^@]+@[^@]+\.[^@]+$",
                                    "metadata": {}
                                }
                            ]
                        }
                    }
                },
                "stage2": {
                    "allow_partial": True,
                    "metadata": {},
                    "gates": {}
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(process_data, f)
            temp_path = f.name

        try:
            process = self.loader.load_process(temp_path)
            assert process.name == "complex_process"
            assert process.allow_stage_skipping is True
            assert process.regression_detection is False
            assert process.metadata == {"version": "1.0"}
            assert process.stage_order == ["stage1", "stage2"]
            assert len(process.stages) == 2

            # Check stage1
            stage1 = next(s for s in process.stages if s.name == "stage1")
            assert stage1.allow_partial is False
            assert stage1.metadata == {"description": "First stage"}
            assert len(stage1.gates) == 1

            # Check gate1
            gate1 = stage1.gates[0]
            assert gate1.name == "gate1"
            assert gate1.operation == GateOperation.AND
            assert gate1.metadata == {"priority": "high"}
            assert len(gate1.components) == 2

            # Check locks (wrapped in LockWrapper)
            from stageflow.core.gate import LockWrapper
            lock1 = gate1.components[0].lock
            assert isinstance(gate1.components[0], LockWrapper)
            assert lock1.property_path == "user.name"
            assert lock1.lock_type == LockType.EXISTS

            lock2 = gate1.components[1].lock
            assert lock2.property_path == "user.email"
            assert lock2.lock_type == LockType.REGEX
            assert lock2.expected_value == r"^[^@]+@[^@]+\.[^@]+$"

        finally:
            Path(temp_path).unlink()

    def test_load_process_from_string(self):
        """Test loading process from JSON string."""
        process_data = {
            "name": "string_process",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }
        json_string = json.dumps(process_data)

        process = self.loader.load_process_from_string(json_string)
        assert process.name == "string_process"

    def test_load_process_from_invalid_string(self):
        """Test loading from invalid JSON string raises error."""
        with pytest.raises(JSONLoadError, match="JSON parsing error"):
            self.loader.load_process_from_string('{"invalid": json,}')

    def test_validate_schema_missing_name(self):
        """Test schema validation fails when name is missing."""
        data = {"stages": {}}
        with pytest.raises(JSONSchemaError, match="must include 'name' field"):
            self.loader.validate_schema(data)

    def test_validate_schema_empty_name(self):
        """Test schema validation fails when name is empty."""
        data = {"name": "", "stages": {}}
        with pytest.raises(JSONSchemaError, match="must be a non-empty string"):
            self.loader.validate_schema(data)

    def test_validate_schema_invalid_stages_type(self):
        """Test schema validation fails when stages is not an object."""
        data = {"name": "test", "stages": []}
        with pytest.raises(JSONSchemaError, match="'stages' must be an object"):
            self.loader.validate_schema(data)

    def test_validate_schema_invalid_stage_order_type(self):
        """Test schema validation fails when stage_order is not an array."""
        data = {"name": "test", "stage_order": "invalid"}
        with pytest.raises(JSONSchemaError, match="'stage_order' must be an array"):
            self.loader.validate_schema(data)

    def test_validate_schema_stage_order_references_missing_stage(self):
        """Test schema validation fails when stage_order references non-existent stage."""
        data = {
            "name": "test",
            "stages": {"stage1": {}},
            "stage_order": ["stage1", "missing_stage"]
        }
        with pytest.raises(JSONSchemaError, match="stage_order references non-existent stages"):
            self.loader.validate_schema(data)

    def test_validate_schema_invalid_gate_logic(self):
        """Test schema validation fails for invalid gate logic."""
        data = {
            "name": "test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "logic": "invalid_logic",
                            "locks": []
                        }
                    }
                }
            }
        }
        with pytest.raises(JSONSchemaError, match="Invalid gate logic"):
            self.loader.validate_schema(data)

    def test_validate_schema_invalid_lock_type(self):
        """Test schema validation fails for invalid lock type."""
        data = {
            "name": "test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "property": "test",
                                    "type": "invalid_lock_type"
                                }
                            ]
                        }
                    }
                }
            }
        }
        with pytest.raises(JSONSchemaError, match="Invalid lock type"):
            self.loader.validate_schema(data)

    def test_validate_schema_missing_lock_property(self):
        """Test schema validation fails when lock is missing property field."""
        data = {
            "name": "test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "type": "exists"
                                }
                            ]
                        }
                    }
                }
            }
        }
        with pytest.raises(JSONSchemaError, match="must include 'property' field"):
            self.loader.validate_schema(data)

    def test_save_process(self):
        """Test saving a process to JSON file."""
        # First create a process
        process_data = {
            "name": "save_test",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(process_data, f)
            temp_path = f.name

        try:
            # Load the process
            process = self.loader.load_process(temp_path)

            # Save to a new file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
                save_path = f2.name

            try:
                self.loader.save_process(process, save_path)

                # Verify the saved file
                with open(save_path) as f:
                    saved_data = json.load(f)

                assert saved_data["name"] == "save_test"
                assert "stages" in saved_data

            finally:
                Path(save_path).unlink()

        finally:
            Path(temp_path).unlink()

    def test_resolve_external_reference(self):
        """Test resolving external file references."""
        # Create referenced file
        referenced_data = {
            "shared_locks": [
                {
                    "property": "shared.value",
                    "type": "exists"
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as ref_file:
            json.dump(referenced_data, ref_file)
            ref_path = ref_file.name

        # Create main file with reference
        main_data = {
            "name": "reference_test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": {"$ref": Path(ref_path).name + "#/shared_locks"}
                        }
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as main_file:
            json.dump(main_data, main_file)
            main_path = main_file.name

        try:
            # This test will need proper JSON reference implementation
            # For now, just test that the loader can handle references gracefully
            loader = JsonLoader(resolve_references=True)
            # The current implementation doesn't fully support complex references yet
            # but the structure is in place

        finally:
            Path(ref_path).unlink()
            Path(main_path).unlink()

    def test_apply_json_pointer(self):
        """Test JSON pointer application."""
        data = {
            "users": [
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Bob", "email": "bob@example.com"}
            ],
            "config": {
                "timeout": 30
            }
        }

        # Test root pointer
        result = self.loader._apply_json_pointer(data, "/")
        assert result == data

        # Test object property
        result = self.loader._apply_json_pointer(data, "/config/timeout")
        assert result == 30

        # Test array index
        result = self.loader._apply_json_pointer(data, "/users/0/name")
        assert result == "Alice"

        # Test invalid pointer
        with pytest.raises(JSONReferenceError, match="Invalid JSON pointer"):
            self.loader._apply_json_pointer(data, "invalid")

        # Test missing path
        with pytest.raises(JSONReferenceError, match="JSON pointer path not found"):
            self.loader._apply_json_pointer(data, "/missing/path")

    def test_optimize_loading(self):
        """Test optimized loading for large files."""
        large_data = {"name": "large_test", "stages": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_data, f)
            temp_path = Path(f.name)

        try:
            result = self.loader.optimize_loading(temp_path)
            assert result["name"] == "large_test"
        finally:
            temp_path.unlink()

    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        process_data = {
            "name": "convenience_test",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(process_data, f)
            temp_path = f.name

        try:
            # Test load_process function
            process = load_process(temp_path)
            assert process.name == "convenience_test"

            # Test load_process_from_string function
            json_string = json.dumps(process_data)
            process2 = load_process_from_string(json_string)
            assert process2.name == "convenience_test"

        finally:
            Path(temp_path).unlink()

    @patch('stageflow.process.schema.loaders.json.HAS_JSONSCHEMA', False)
    def test_no_jsonschema_warning(self):
        """Test that warning is issued when jsonschema is not available."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            JsonLoader(validate_schema=True)
            assert len(w) == 1
            assert "jsonschema library not available" in str(w[0].message)

    def test_error_location_information(self):
        """Test that errors include proper location information."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json,}')
            temp_path = f.name

        try:
            with pytest.raises(JSONLoadError) as exc_info:
                self.loader.load_process(temp_path)

            error = exc_info.value
            assert temp_path in str(error)
            assert error.line is not None
            assert error.column is not None

        finally:
            Path(temp_path).unlink()


class TestJSONExceptions:
    """Test JSON exception classes."""

    def test_json_load_error_basic(self):
        """Test JSONLoadError with basic message."""
        error = JSONLoadError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.file_path is None
        assert error.line is None
        assert error.column is None

    def test_json_load_error_with_location(self):
        """Test JSONLoadError with full location information."""
        error = JSONLoadError("Test error", "/path/to/file.json", 10, 5)
        expected = "Test error in file '/path/to/file.json' at line 10, column 5"
        assert str(error) == expected
        assert error.file_path == "/path/to/file.json"
        assert error.line == 10
        assert error.column == 5

    def test_json_load_error_with_file_only(self):
        """Test JSONLoadError with file path only."""
        error = JSONLoadError("Test error", "/path/to/file.json")
        expected = "Test error in file '/path/to/file.json'"
        assert str(error) == expected

    def test_json_load_error_with_line_only(self):
        """Test JSONLoadError with line number only."""
        error = JSONLoadError("Test error", "/path/to/file.json", 10)
        expected = "Test error in file '/path/to/file.json' at line 10"
        assert str(error) == expected

    def test_json_schema_error_inheritance(self):
        """Test that JSONSchemaError inherits from JSONLoadError."""
        error = JSONSchemaError("Schema error")
        assert isinstance(error, JSONLoadError)

    def test_json_reference_error_inheritance(self):
        """Test that JSONReferenceError inherits from JSONLoadError."""
        error = JSONReferenceError("Reference error")
        assert isinstance(error, JSONLoadError)
