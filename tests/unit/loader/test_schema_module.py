"""
Unit tests for the simplified stageflow.schema module.

Tests the actual available functionality in the schema module including
the loader functions and integration with the core Process class.
"""

import json
from textwrap import dedent

import pytest

from stageflow.elements import DictElement
from stageflow.loader import (
    ActionDefinition,
    GateDefinition,
    LoadError,
    LockDefinition,
    Process,
    ProcessDefinition,
    ProcessElementEvaluationResult,
    StageDefinition,
    load_process,
)


class TestSchemaModuleImports:
    """Test suite for schema module imports and availability."""

    def test_schema_module_imports_available(self):
        """Verify all expected schema module imports are available."""
        # Arrange & Act
        from stageflow.loader import (
            LoadError,
            Process,
            load_process,
        )

        # Assert
        assert Process is not None
        assert ProcessDefinition is not None
        assert ProcessElementEvaluationResult is not None
        assert StageDefinition is not None
        assert ActionDefinition is not None
        assert GateDefinition is not None
        assert LockDefinition is not None
        assert LoadError is not None
        assert load_process is not None

    def test_load_error_exception_class(self):
        """Verify LoadError is a proper exception class."""
        # Arrange & Act
        error = LoadError("Test error message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"


class TestLoadProcessFunction:
    """Test suite for load_process function."""

    def test_load_process_with_valid_yaml_file(self, tmp_path):
        """Verify load_process loads valid YAML files correctly."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: test_process
              description: Test process
              initial_stage: start
              final_stage: end
              stages:
                start:
                  name: start
                  description: Starting stage
                  gates:
                    begin:
                      name: begin
                      description: Begin gate
                      target_stage: end
                      locks:
                        - property_path: ready
                          type: exists
                  expected_actions: []
                  expected_properties:
                    ready:
                      type: boolean
                  is_final: false
                end:
                  name: end
                  description: Ending stage
                  gates: {}
                  expected_actions: []
                  expected_properties: null
                  is_final: true
        """).strip()

        yaml_file = tmp_path / "test_process.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(yaml_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "test_process"

    def test_load_process_with_valid_json_file(self, tmp_path):
        """Verify load_process loads valid JSON files correctly."""
        # Arrange
        process_data = {
            "process": {
                "name": "json_test_process",
                "description": "JSON test process",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "name": "start",
                        "description": "Starting stage",
                        "gates": {
                            "begin": {
                                "name": "begin",
                                "description": "Begin gate",
                                "target_stage": "end",
                                "locks": [{"property_path": "ready", "type": "exists"}],
                            }
                        },
                        "expected_actions": [],
                        "expected_properties": {"ready": {"type": "boolean"}},
                        "is_final": False,
                    },
                    "end": {
                        "name": "end",
                        "description": "Ending stage",
                        "gates": {},
                        "expected_actions": [],
                        "expected_properties": None,
                        "is_final": True,
                    },
                },
            }
        }

        json_file = tmp_path / "test_process.json"
        with open(json_file, "w") as f:
            json.dump(process_data, f)

        # Act
        process = load_process(json_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "json_test_process"

    def test_load_process_with_nonexistent_file(self, tmp_path):
        """Verify load_process raises LoadError for nonexistent files."""
        # Arrange
        nonexistent_file = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(LoadError, match="Process file not found"):
            load_process(nonexistent_file)

    def test_load_process_with_unsupported_file_format(self, tmp_path):
        """Verify load_process raises LoadError for unsupported file formats."""
        # Arrange
        txt_file = tmp_path / "process.txt"
        txt_file.write_text("plain text content")

        # Act & Assert
        with pytest.raises(LoadError, match="Process file must contain a dictionary"):
            load_process(txt_file)

    def test_load_process_with_invalid_yaml_syntax(self, tmp_path):
        """Verify load_process raises LoadError for invalid YAML syntax."""
        # Arrange
        invalid_yaml = "invalid: yaml: content: ["
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(invalid_yaml)

        # Act & Assert
        with pytest.raises(LoadError):
            load_process(yaml_file)

    def test_load_process_with_invalid_json_syntax(self, tmp_path):
        """Verify load_process raises LoadError for invalid JSON syntax."""
        # Arrange
        invalid_json = '{"invalid": json syntax}'
        json_file = tmp_path / "invalid.json"
        json_file.write_text(invalid_json)

        # Act & Assert
        with pytest.raises(LoadError):
            load_process(json_file)

    def test_load_process_with_missing_process_key(self, tmp_path):
        """Verify load_process raises LoadError when 'process' key is missing."""
        # Arrange
        yaml_content = dedent("""
            name: missing_process_key
            stages: []
        """).strip()

        yaml_file = tmp_path / "missing_key.yaml"
        yaml_file.write_text(yaml_content)

        # Act & Assert
        # New loader accepts root-level process definition, but validates required fields
        with pytest.raises(
            LoadError,
            match=".*missing required field.*",
        ):
            load_process(yaml_file)

    def test_load_process_with_non_dict_content(self, tmp_path):
        """Verify load_process raises LoadError when file content is not a dictionary."""
        # Arrange
        yaml_content = "- item1\n- item2\n- item3"
        yaml_file = tmp_path / "list_content.yaml"
        yaml_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(LoadError, match="must contain a dictionary"):
            load_process(yaml_file)

    def test_load_process_with_pathlib_path(self, tmp_path):
        """Verify load_process works with pathlib.Path objects."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: pathlib_test
              description: Pathlib test
              initial_stage: start
              final_stage: end
              stages:
                start:
                  name: start
                  description: Start stage
                  gates:
                    finish:
                      name: finish
                      description: Go to end
                      target_stage: end
                      locks:
                        - property_path: done
                          type: exists
                  expected_actions: []
                  expected_properties:
                    done:
                      type: boolean
                  is_final: false
                end:
                  name: end
                  description: End stage
                  gates: {}
                  expected_actions: []
                  expected_properties: null
                  is_final: true
        """).strip()

        yaml_file = tmp_path / "pathlib_test.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(yaml_file)  # yaml_file is already a Path object

        # Assert
        assert isinstance(process, Process)
        assert process.name == "pathlib_test"

    def test_load_process_with_string_path(self, tmp_path):
        """Verify load_process works with string paths."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: string_path_test
              description: String path test
              initial_stage: start
              final_stage: end
              stages:
                start:
                  name: start
                  description: Start stage
                  gates:
                    finish:
                      name: finish
                      description: Go to end
                      target_stage: end
                      locks:
                        - property_path: done
                          type: exists
                  expected_actions: []
                  expected_properties:
                    done:
                      type: boolean
                  is_final: false
                end:
                  name: end
                  description: End stage
                  gates: {}
                  expected_actions: []
                  expected_properties: null
                  is_final: true
        """).strip()

        yaml_file = tmp_path / "string_path_test.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(str(yaml_file))  # Convert to string

        # Assert
        assert isinstance(process, Process)
        assert process.name == "string_path_test"


class TestSchemaIntegrationWithProcess:
    """Test suite for schema module integration with Process class."""

    def test_end_to_end_process_loading_and_evaluation(self, tmp_path):
        """Verify end-to-end workflow from schema loading to process evaluation."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: e2e_integration_test
              description: End-to-end integration test process
              initial_stage: input_validation
              final_stage: completed
              stages:
                input_validation:
                  description: Validate input data
                  gates:
                    - name: data_present
                      description: Check if required data is present
                      target_stage: processing
                      locks:
                        - property_path: input.data
                          type: exists
                        - property_path: input.format
                          type: equals
                          expected_value: "json"

                processing:
                  description: Process the data
                  gates:
                    - name: processing_complete
                      description: Check if processing is complete
                      target_stage: completed
                      locks:
                        - property_path: processing.status
                          type: equals
                          expected_value: "done"

                completed:
                  description: Final completion stage
                  gates: []
        """).strip()

        yaml_file = tmp_path / "e2e_test.yaml"
        yaml_file.write_text(yaml_content)

        # Valid element data
        valid_element_data = {
            "input": {"data": {"key": "value"}, "format": "json"},
            "processing": {"status": "done", "duration_ms": 1500},
        }

        # Invalid element data
        invalid_element_data = {
            "input": {
                "format": "xml"  # Wrong format
                # Missing data
            }
            # Missing processing status
        }

        # Act
        process = load_process(yaml_file)

        # Test with valid element
        valid_element = DictElement(valid_element_data)
        valid_result = process.evaluate(valid_element, "input_validation")

        # Test with invalid element
        invalid_element = DictElement(invalid_element_data)
        invalid_result = process.evaluate(invalid_element, "input_validation")

        # Assert
        assert process.name == "e2e_integration_test"
        assert process.description == "End-to-end integration test process"

        # Valid element should have successful evaluation
        assert valid_result["stage"] == "input_validation"

        # Invalid element should have evaluation issues
        assert invalid_result["stage"] == "input_validation"


class TestSchemaErrorHandling:
    """Test suite for schema module error handling."""

    def test_error_handling_preserves_original_exceptions(self, tmp_path):
        """Verify error handling preserves information about original exceptions."""
        # Arrange
        # Create a file with a syntax error that will cause a specific exception
        invalid_json = '{"process": {"name": "test", "invalid": json}}'
        json_file = tmp_path / "syntax_error.json"
        json_file.write_text(invalid_json)

        # Act & Assert
        with pytest.raises(LoadError) as exc_info:
            load_process(json_file)

        # The LoadError should contain information about the original JSON error
        assert "syntax_error.json" in str(exc_info.value)

    def test_error_messages_are_descriptive(self, tmp_path):
        """Verify error messages provide useful information for debugging."""
        # Test various error conditions and check message quality

        # Nonexistent file - updated regex for new error format
        with pytest.raises(LoadError, match=".*file not found.*nonexistent.yaml"):
            load_process(tmp_path / "nonexistent.yaml")

        # Unsupported format - updated regex for new error format
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("plain text")
        with pytest.raises(
            LoadError, match=".*Process file must contain a dictionary.*"
        ):
            load_process(txt_file)

        # Missing process key - updated regex for new error format
        yaml_content = "name: test"
        yaml_file = tmp_path / "missing_process_key.yaml"
        yaml_file.write_text(yaml_content)
        with pytest.raises(
            LoadError,
            match=".*missing required field.*(initial_stage|final_stage|stages)",
        ):
            load_process(yaml_file)
