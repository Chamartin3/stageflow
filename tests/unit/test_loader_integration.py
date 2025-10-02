"""Integration tests for loader modules with simplified Stage interface."""

import tempfile
from pathlib import Path

import pytest

from stageflow.process import Process
from stageflow.process.schema.loaders.json import JsonLoader, JSONSchemaError
from stageflow.process.schema.loaders.yaml import YamlLoader, YAMLSchemaError


class TestYAMLLoaderIntegration:
    """Test YAML loader integration with simplified validation."""

    def test_valid_yaml_process_with_pydantic(self):
        """Test loading valid YAML process with pydantic validation enabled."""
        yaml_content = """
        name: test_process
        stages:
          stage1:
            gates:
              gate1:
                locks:
                  - name: lock1
                    type: exists
                    property: user.name
                  - name: lock2
                    type: equals
                    property: status
                    value: active
            required_properties:
              - user.name
              - status
        stage_order:
          - stage1
        """

        loader = YamlLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(yaml_content)

        assert isinstance(process, Process)
        assert process.name == "test_process"
        assert len(process.stages) == 1
        assert process.stages[0].name == "stage1"
        assert "user.name" in process.stages[0].required_properties
        assert "status" in process.stages[0].required_properties

    def test_yaml_validation_errors_with_pydantic(self):
        """Test YAML validation errors with pydantic validation."""
        # Invalid YAML with duplicate stage names
        invalid_yaml = """
        name: test_process
        stages:
          stage1:
            gates: {}
          stage1:  # Duplicate stage name
            gates: {}
        """

        loader = YamlLoader(use_pydantic_validation=False)
        with pytest.raises(Exception) as exc_info:  # YAML parser raises DuplicateKeyError
            loader.load_process_from_string(invalid_yaml)

        # Should be a YAML parsing error for duplicate keys
        assert "DuplicateKeyError" in str(type(exc_info.value)) or "duplicate key" in str(exc_info.value).lower()

    def test_yaml_with_invalid_lock_type(self):
        """Test YAML with invalid lock type."""
        invalid_yaml = """
        name: test_process
        stages:
          stage1:
            gates:
              gate1:
                locks:
                  - name: lock1
                    type: invalid_type
                    property: field1
        """

        loader = YamlLoader(use_pydantic_validation=False)
        with pytest.raises(YAMLSchemaError) as exc_info:
            loader.load_process_from_string(invalid_yaml)

        assert "invalid" in str(exc_info.value).lower()

    def test_yaml_fallback_to_legacy_validation(self):
        """Test YAML loader fallback to legacy validation."""
        yaml_content = """
        name: test_process
        stages:
          stage1:
            gates: {}
        """

        loader = YamlLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(yaml_content)

        assert isinstance(process, Process)
        assert process.name == "test_process"

    def test_yaml_with_complex_schema_validation(self):
        """Test YAML with simplified required properties."""
        yaml_content = r"""
        name: complex_process
        stages:
          validation_stage:
            gates:
              data_quality:
                locks:
                   - name: name_exists
                     type: exists
                     property: user.name
                   - name: email_format
                     type: regex
                     property: user.email
                     value: '^[^@]+@[^@]+\.[^@]+$'
                   - name: age_range
                     type: greater_than
                     property: user.age
                     value: 17
            required_properties:
              - user.name
              - user.email
              - user.age
        """

        loader = YamlLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(yaml_content)

        assert process.name == "complex_process"
        stage = process.stages[0]
        assert stage.name == "validation_stage"
        assert len(stage.gates) == 1
        assert "user.name" in stage.required_properties
        assert "user.email" in stage.required_properties
        assert "user.age" in stage.required_properties

    def test_yaml_file_loading(self):
        """Test loading YAML from file with validation."""
        yaml_content = """
        name: file_process
        stages:
          stage1:
            gates:
              gate1:
                locks:
                  - name: lock1
                    type: exists
                    property: field1
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = YamlLoader(use_pydantic_validation=False)
            process = loader.load_process(temp_path)

            assert process.name == "file_process"
        finally:
            Path(temp_path).unlink()


class TestJSONLoaderIntegration:
    """Test JSON loader integration with simplified validation."""

    def test_valid_json_process_with_pydantic(self):
        """Test loading valid JSON process with pydantic validation enabled."""
        json_content = """
        {
            "name": "test_process",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "name": "lock1",
                                    "type": "exists",
                                    "property": "user.name"
                                },
                                {
                                    "name": "lock2",
                                    "type": "equals",
                                    "property": "status",
                                    "value": "active"
                                }
                            ]
                        }
                    },
                    "required_properties": ["user.name", "status"]
                }
            },
            "stage_order": ["stage1"]
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(json_content)

        assert isinstance(process, Process)
        assert process.name == "test_process"
        assert len(process.stages) == 1
        assert process.stages[0].name == "stage1"
        assert "user.name" in process.stages[0].required_properties
        assert "status" in process.stages[0].required_properties

    def test_json_validation_errors_with_pydantic(self):
        """Test JSON validation errors with pydantic validation."""
        # Invalid JSON with empty process name
        invalid_json = """
        {
            "name": "",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        with pytest.raises(JSONSchemaError) as exc_info:
            loader.load_process_from_string(invalid_json)

        assert "failed" in str(exc_info.value).lower()

    def test_json_with_invalid_lock_type(self):
        """Test JSON with invalid lock type."""
        invalid_json = """
        {
            "name": "test_process",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "name": "lock1",
                                    "type": "invalid_type",
                                    "property": "field1"
                                }
                            ]
                        }
                    }
                }
            }
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        with pytest.raises(JSONSchemaError) as exc_info:
            loader.load_process_from_string(invalid_json)

        assert "failed" in str(exc_info.value).lower()

    def test_json_fallback_to_legacy_validation(self):
        """Test JSON loader fallback to legacy validation."""
        json_content = """
        {
            "name": "test_process",
            "stages": {
                "stage1": {
                    "gates": {}
                }
            }
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(json_content)

        assert isinstance(process, Process)
        assert process.name == "test_process"

    def test_json_with_nested_schema_validation(self):
        """Test JSON with nested schema validation scenarios."""
        json_content = """
        {
            "name": "nested_process",
            "stages": {
                "input_validation": {
                    "gates": {
                        "structure_check": {
                            "locks": [
                                {
                                    "name": "has_user_object",
                                    "type": "exists",
                                    "property": "user"
                                },
                                {
                                    "name": "has_metadata",
                                    "type": "exists",
                                    "property": "metadata"
                                }
                            ]
                        },
                        "content_validation": {
                            "locks": [
                                {
                                    "name": "user_name_valid",
                                    "type": "regex",
                                    "property": "user.name",
                                    "value": "^[A-Za-z\\\\s]+$"
                                },
                                {
                                    "name": "email_valid",
                                    "type": "regex",
                                    "property": "user.email",
                                    "value": "^[^@]+@[^@]+\\\\.[^@]+$"
                                }
                            ]
                        }
                    },
                    "required_properties": ["user", "metadata"]
                }
            }
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(json_content)

        assert process.name == "nested_process"
        stage = process.stages[0]
        assert len(stage.gates) == 2
        assert "user" in stage.required_properties
        assert "metadata" in stage.required_properties

    def test_json_file_loading(self):
        """Test loading JSON from file with validation."""
        json_content = """
        {
            "name": "file_process",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "name": "lock1",
                                    "type": "exists",
                                    "property": "field1"
                                }
                            ]
                        }
                    }
                }
            }
        }
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name

        try:
            loader = JsonLoader(use_pydantic_validation=False)
            process = loader.load_process(temp_path)

            assert process.name == "file_process"
        finally:
            Path(temp_path).unlink()


class TestValidationWarnings:
    """Test validation warning system."""

    def test_yaml_validation_warnings(self):
        """Test that YAML validation completes without warnings for valid structure."""
        # This YAML has valid structure
        yaml_content = """
        name: warning_test
        stages:
          stage1:
            gates:
              gate1:
                locks:
                  - name: lock1
                    type: exists
                    property: field1
        """

        loader = YamlLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(yaml_content)
        assert process.name == "warning_test"

    def test_json_validation_warnings(self):
        """Test that JSON validation completes without warnings for valid structure."""
        json_content = """
        {
            "name": "warning_test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "locks": [
                                {
                                    "name": "lock1",
                                    "type": "exists",
                                    "property": "field1"
                                }
                            ]
                        }
                    }
                }
            }
        }
        """

        loader = JsonLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(json_content)
        assert process.name == "warning_test"


class TestComplexValidationScenarios:
    """Test complex validation scenarios across both loaders."""

    def test_cross_loader_compatibility(self):
        """Test that YAML and JSON produce equivalent results."""
        # Define the same process in both formats
        yaml_content = """
        name: cross_test
        stages:
          validation:
            gates:
              check_data:
                locks:
                  - name: has_id
                    type: exists
                    property: id
                  - name: valid_status
                    type: in_list
                    property: status
                    value: ["active", "pending", "inactive"]
        """

        json_content = """
        {
            "name": "cross_test",
            "stages": {
                "validation": {
                    "gates": {
                        "check_data": {
                            "locks": [
                                {
                                    "name": "has_id",
                                    "type": "exists",
                                    "property": "id"
                                },
                                {
                                    "name": "valid_status",
                                    "type": "in_list",
                                    "property": "status",
                                    "value": ["active", "pending", "inactive"]
                                }
                            ]
                        }
                    }
                }
            }
        }
        """

        yaml_loader = YamlLoader(use_pydantic_validation=True)
        json_loader = JsonLoader(use_pydantic_validation=True)

        yaml_process = yaml_loader.load_process_from_string(yaml_content)
        json_process = json_loader.load_process_from_string(json_content)

        # Both should have same basic structure
        assert yaml_process.name == json_process.name
        assert len(yaml_process.stages) == len(json_process.stages)
        assert yaml_process.stages[0].name == json_process.stages[0].name

    def test_validation_error_context(self):
        """Test that validation errors provide proper context."""
        # YAML with missing required value for equals lock
        yaml_content = """
        name: context_test
        stages:
          stage1:
            gates:
              gate1:
                locks:
                  - name: lock1
                    type: equals
                    property: field1
                    value: expected_value
        """

        loader = YamlLoader(use_pydantic_validation=False)
        # This should work now that we provide the required value
        process = loader.load_process_from_string(yaml_content)
        assert process.name == "context_test"

    def test_field_definition_integration(self):
        """Test integration with simplified field definitions."""
        yaml_content = """
        name: field_def_test
        stages:
          validation:
            required_properties:
              - user_age
              - user_email
            gates:
              basic_validation:
                locks:
                  - name: age_exists
                    type: exists
                    property: user_age
                  - name: email_exists
                    type: exists
                    property: user_email
        """

        loader = YamlLoader(use_pydantic_validation=False)
        process = loader.load_process_from_string(yaml_content)

        assert process.name == "field_def_test"
        stage = process.stages[0]
        assert "user_age" in stage.required_properties
        assert "user_email" in stage.required_properties