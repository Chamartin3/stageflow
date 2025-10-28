"""Comprehensive unit tests for the stageflow.schema.loader module.

This module tests the core functionality of loading Process objects from YAML/JSON files,
including file loading, data validation, error handling, and configuration conversion.
"""
# type: ignore

import json
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest

from stageflow.element import Element
from stageflow.process import Process
from stageflow.schema.loader import (
    Loader,
    LoadError,
    _convert_process_config,
    load_process,
)


class TestLoadError:
    """Test cases for LoadError exception."""

    def test_load_error_inheritance(self):
        """Verify LoadError inherits from Exception."""
        # Arrange & Act
        error = LoadError("test message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    def test_load_error_with_custom_message(self):
        """Verify LoadError preserves custom error messages."""
        # Arrange
        custom_message = "Custom error occurred during loading"

        # Act
        error = LoadError(custom_message)

        # Assert
        assert str(error) == custom_message


class TestLoadProcess:
    """Test cases for load_process function."""

    def test_load_process_from_valid_yaml_file(self, tmp_path):
        """Verify successful loading of Process from valid YAML file."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: test_process
              description: Test process for unit testing
              initial_stage: start
              final_stage: end
              stages:
                start:
                  name: Start Stage
                  description: Initial stage
                  gates:
                    proceed:
                      target_stage: end
                      locks:
                        - exists: "user.email"
                        - type: regex
                          property_path: "user.email"
                          expected_value: "^[^@]+@[^@]+\\\\.[^@]+$"
                end:
                  name: End Stage
                  description: Final stage
                  is_final: true
                  gates: []
        """).strip()

        yaml_file = tmp_path / "test_process.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(yaml_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "test_process"
        assert process.description == "Test process for unit testing"
        assert process.initial_stage._id == "start"
        assert process.final_stage._id == "end"
        assert len(process.stages) == 2

    def test_load_process_from_valid_json_file(self, tmp_path):
        """Verify successful loading of Process from valid JSON file."""
        # Arrange
        json_data = {
            "process": {
                "name": "json_test_process",
                "description": "Test process from JSON",
                "initial_stage": "initial",
                "final_stage": "final",
                "stages": {
                    "initial": {
                        "name": "Initial Stage",
                        "description": "Starting point",
                        "gates": {
                            "validate": {
                                "target_stage": "final",
                                "locks": [
                                    {"exists": "data.required_field"},
                                    {
                                        "type": "equals",
                                        "property_path": "status",
                                        "expected_value": "ready",
                                    },
                                ],
                            }
                        },
                    },
                    "final": {
                        "name": "Final Stage",
                        "description": "End point",
                        "is_final": True,
                        "gates": [],
                    },
                },
            }
        }

        json_file = tmp_path / "test_process.json"
        json_file.write_text(json.dumps(json_data, indent=2))

        # Act
        process = load_process(json_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "json_test_process"
        assert process.description == "Test process from JSON"
        assert process.initial_stage._id == "initial"
        assert process.final_stage._id == "final"
        assert len(process.stages) == 2

    def test_load_process_with_pathlib_path(self, tmp_path):
        """Verify load_process accepts pathlib.Path objects."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: pathlib_test
              description: Test with pathlib Path
              initial_stage: start
              final_stage: end
              stages:
                start:
                  gates:
                    proceed:
                      target_stage: end
                      locks:
                        - exists: "field"
                end:
                  is_final: true
                  gates: []
        """).strip()

        yaml_file = tmp_path / "pathlib_test.yaml"
        yaml_file.write_text(yaml_content)
        path_object = Path(yaml_file)

        # Act
        process = load_process(path_object)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "pathlib_test"

    def test_load_process_with_string_path(self, tmp_path):
        """Verify load_process accepts string file paths."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: string_path_test
              description: Test with string path
              initial_stage: start
              final_stage: end
              stages:
                start:
                  gates:
                    proceed:
                      target_stage: end
                      locks:
                        - exists: "field"
                end:
                  is_final: true
                  gates: []
        """).strip()

        yaml_file = tmp_path / "string_test.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(str(yaml_file))

        # Assert
        assert isinstance(process, Process)
        assert process.name == "string_path_test"

    def test_load_process_file_not_found_raises_load_error(self):
        """Verify LoadError is raised when file does not exist."""
        # Arrange
        non_existent_file = "/tmp/non_existent_file.yaml"

        # Act & Assert
        with pytest.raises(LoadError, match="File not found"):
            load_process(non_existent_file)

    def test_load_process_unsupported_file_format_raises_load_error(self, tmp_path):
        """Verify LoadError is raised for unsupported file formats."""
        # Arrange
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("some content")

        # Act & Assert
        with pytest.raises(LoadError, match="Unsupported file format"):
            load_process(txt_file)

    def test_load_process_invalid_yaml_syntax_raises_load_error(self, tmp_path):
        """Verify LoadError is raised for invalid YAML syntax."""
        # Arrange
        invalid_yaml = "process:\n  name: test\n  invalid: [unclosed"
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(invalid_yaml)

        # Act & Assert
        with pytest.raises(LoadError, match="Error parsing YAML"):
            load_process(yaml_file)

    def test_load_process_invalid_json_syntax_raises_load_error(self, tmp_path):
        """Verify LoadError is raised for invalid JSON syntax."""
        # Arrange
        invalid_json = '{"process": {"name": "test", "invalid": [}'
        json_file = tmp_path / "invalid.json"
        json_file.write_text(invalid_json)

        # Act & Assert
        with pytest.raises(LoadError, match="Error parsing JSON"):
            load_process(json_file)

    def test_load_process_non_dict_content_raises_load_error(self, tmp_path):
        """Verify LoadError is raised when file content is not a dictionary."""
        # Arrange
        yaml_content = "- item1\n- item2\n- item3"
        yaml_file = tmp_path / "list_content.yaml"
        yaml_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(LoadError, match="File must contain a dictionary"):
            load_process(yaml_file)

    def test_load_process_missing_process_key_raises_load_error(self, tmp_path):
        """Verify LoadError is raised when 'process' key is missing."""
        # Arrange
        yaml_content = dedent("""
            name: test_without_process_key
            stages:
              start:
                gates: []
        """).strip()
        yaml_file = tmp_path / "no_process_key.yaml"
        yaml_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(
            LoadError,
            match="File must contain either a 'process' key or process definition at root level",
        ):
            load_process(yaml_file)

    def test_load_process_yml_extension_works(self, tmp_path):
        """Verify .yml extension is recognized as YAML format."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: yml_extension_test
              description: Test .yml extension
              initial_stage: start
              final_stage: end
              stages:
                start:
                  gates:
                    proceed:
                      target_stage: end
                      locks:
                        - exists: "field"
                end:
                  is_final: true
                  gates: []
        """).strip()

        yml_file = tmp_path / "test.yml"
        yml_file.write_text(yaml_content)

        # Act
        process = load_process(yml_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "yml_extension_test"

    def test_load_process_case_insensitive_extensions(self, tmp_path):
        """Verify file extensions are case-insensitive."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: case_test
              description: Test case insensitive extensions
              initial_stage: start
              final_stage: end
              stages:
                start:
                  gates:
                    proceed:
                      target_stage: end
                      locks:
                        - exists: "field"
                end:
                  is_final: true
                  gates: []
        """).strip()

        upper_yaml_file = tmp_path / "test.YAML"
        upper_json_file = tmp_path / "test.JSON"

        json_data = {
            "process": {
                "name": "case_json_test",
                "description": "Test case insensitive JSON",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "gates": {
                            "proceed": {
                                "target_stage": "end",
                                "locks": [{"exists": "field"}],
                            }
                        }
                    },
                    "end": {"is_final": True, "gates": []},
                },
            }
        }

        upper_yaml_file.write_text(yaml_content)
        upper_json_file.write_text(json.dumps(json_data))

        # Act
        yaml_process = load_process(upper_yaml_file)
        json_process = load_process(upper_json_file)

        # Assert
        assert isinstance(yaml_process, Process)
        assert yaml_process.name == "case_test"
        assert isinstance(json_process, Process)
        assert json_process.name == "case_json_test"


class TestConvertProcessConfig:
    """Test cases for _convert_process_config function."""

    def test_convert_process_config_with_dict_gates(self):
        """Verify conversion of dict-style gates to list format."""
        # Arrange
        config = {
            "name": "convert_test",
            "stages": {
                "stage1": {
                    "name": "Stage One",
                    "gates": {
                        "gate1": {
                            "target_stage": "stage2",
                            "locks": [{"exists": "field1"}],
                        },
                        "gate2": {
                            "target_stage": "stage3",
                            "locks": [{"exists": "field2"}],
                        },
                    },
                }
            },
        }

        # Act
        converted = _convert_process_config(config)

        # Assert
        stage1 = converted["stages"]["stage1"]
        assert isinstance(stage1["gates"], list)
        assert len(stage1["gates"]) == 2

        gates = {gate["name"]: gate for gate in stage1["gates"]}
        assert "gate1" in gates
        assert "gate2" in gates
        assert gates["gate1"]["target_stage"] == "stage2"
        assert gates["gate2"]["target_stage"] == "stage3"
        assert gates["gate1"]["parent_stage"] == "stage1"
        assert gates["gate2"]["parent_stage"] == "stage1"

    def test_convert_process_config_with_list_gates(self):
        """Verify proper handling of already list-format gates."""
        # Arrange
        config = {
            "name": "list_gates_test",
            "stages": {
                "stage1": {
                    "gates": [
                        {
                            "name": "gate1",
                            "target_stage": "stage2",
                            "locks": [{"exists": "field1"}],
                        },
                        {
                            "name": "gate2",
                            "target_stage": "stage3",
                            "locks": [{"exists": "field2"}],
                        },
                    ]
                }
            },
        }

        # Act
        converted = _convert_process_config(config)

        # Assert
        stage1 = converted["stages"]["stage1"]
        assert isinstance(stage1["gates"], list)
        assert len(stage1["gates"]) == 2
        assert stage1["gates"][0]["parent_stage"] == "stage1"
        assert stage1["gates"][1]["parent_stage"] == "stage1"
        assert stage1["gates"][0]["description"] == ""
        assert stage1["gates"][1]["description"] == ""

    def test_convert_process_config_adds_default_stage_fields(self):
        """Verify default fields are added to stages when missing."""
        # Arrange
        config = {"name": "defaults_test", "stages": {"minimal_stage": {"gates": {}}}}

        # Act
        converted = _convert_process_config(config)

        # Assert
        stage = converted["stages"]["minimal_stage"]
        assert stage["name"] == "minimal_stage"
        assert stage["description"] == ""
        assert stage["expected_actions"] == []
        assert stage["expected_properties"] is None
        assert stage["is_final"] is False

    def test_convert_process_config_preserves_existing_stage_fields(self):
        """Verify existing stage fields are preserved during conversion."""
        # Arrange
        config = {
            "name": "preserve_test",
            "stages": {
                "custom_stage": {
                    "name": "Custom Stage Name",
                    "description": "Custom description",
                    "expected_actions": ["action1", "action2"],
                    "expected_properties": {"prop1": {"type": "str"}},
                    "is_final": True,
                    "gates": {},
                }
            },
        }

        # Act
        converted = _convert_process_config(config)

        # Assert
        stage = converted["stages"]["custom_stage"]
        assert stage["name"] == "Custom Stage Name"
        assert stage["description"] == "Custom description"
        assert stage["expected_actions"] == ["action1", "action2"]
        assert stage["expected_properties"] == {"prop1": {"type": "str"}}
        assert stage["is_final"] is True

    def test_convert_process_config_adds_gate_descriptions(self):
        """Verify empty descriptions are added to gates when missing."""
        # Arrange
        config = {
            "name": "gate_desc_test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate_without_desc": {
                            "target_stage": "stage2",
                            "locks": [{"exists": "field"}],
                        },
                        "gate_with_desc": {
                            "description": "Existing description",
                            "target_stage": "stage2",
                            "locks": [{"exists": "field"}],
                        },
                    }
                }
            },
        }

        # Act
        converted = _convert_process_config(config)

        # Assert
        gates = {gate["name"]: gate for gate in converted["stages"]["stage1"]["gates"]}
        assert gates["gate_without_desc"]["description"] == ""
        assert gates["gate_with_desc"]["description"] == "Existing description"

    def test_convert_process_config_preserves_top_level_fields(self):
        """Verify top-level configuration fields are preserved."""
        # Arrange
        config = {
            "name": "preserve_top_test",
            "description": "Test description",
            "initial_stage": "start",
            "final_stage": "end",
            "custom_field": "custom_value",
            "metadata": {"version": "1.0"},
            "stages": {"start": {"gates": {}}, "end": {"gates": {}}},
        }

        # Act
        converted = _convert_process_config(config)

        # Assert
        assert converted["name"] == "preserve_top_test"
        assert converted["description"] == "Test description"
        assert converted["initial_stage"] == "start"
        assert converted["final_stage"] == "end"

    def test_convert_process_config_handles_no_stages(self):
        """Verify conversion works when no stages are present."""
        # Arrange
        config = {"name": "no_stages_test", "description": "Test without stages"}

        # Act
        converted = _convert_process_config(config)

        # Assert
        assert converted["name"] == "no_stages_test"
        assert converted["description"] == "Test without stages"
        # No stages key should remain absent or be handled gracefully

    def test_convert_process_config_does_not_mutate_original(self):
        """Verify original configuration is not modified during conversion."""
        # Arrange
        original_config = {
            "name": "mutation_test",
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "target_stage": "stage2",
                            "locks": [{"exists": "field"}],
                        }
                    }
                }
            },
        }
        original_copy = json.loads(json.dumps(original_config))  # Deep copy

        # Act
        converted = _convert_process_config(original_config)

        # Assert
        assert original_config == original_copy  # Original unchanged
        assert converted != original_config  # Conversion produced different structure
        assert isinstance(converted["stages"]["stage1"]["gates"], list)
        assert isinstance(original_config["stages"]["stage1"]["gates"], dict)


class TestIntegrationScenarios:
    """Integration tests combining multiple functions with realistic scenarios."""

    def test_end_to_end_yaml_loading_and_conversion(self, tmp_path):
        """Verify complete workflow from YAML file to Process object."""
        # Arrange
        yaml_content = dedent("""
            process:
              name: e2e_test_process
              description: End-to-end test process
              initial_stage: registration
              final_stage: active

              stages:
                registration:
                  name: User Registration
                  description: Initial user registration stage
                  expected_properties:
                    email: {type: str}
                    password: {type: str}
                  gates:
                    basic_validation:
                      description: Basic field validation
                      target_stage: verification
                      locks:
                        - exists: "email"
                        - exists: "password"
                        - type: regex
                          property_path: "email"
                          expected_value: "^[^@]+@[^@]+\\\\.[^@]+$"

                verification:
                  name: Email Verification
                  description: Email verification stage
                  gates:
                    email_verified:
                      target_stage: active
                      locks:
                        - type: equals
                          property_path: "verification.email_verified"
                          expected_value: true

                active:
                  name: Active User
                  description: Fully activated user
                  is_final: true
                  gates: {}
        """).strip()

        yaml_file = tmp_path / "e2e_test.yaml"
        yaml_file.write_text(yaml_content)

        # Act
        process = load_process(yaml_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "e2e_test_process"
        assert process.description == "End-to-end test process"
        assert process.initial_stage._id == "registration"
        assert process.final_stage._id == "active"
        assert len(process.stages) == 3

        # Verify stage names are properly set
        stage_names = {stage.name for stage in process.stages}
        assert "User Registration" in stage_names
        assert "Email Verification" in stage_names
        assert "Active User" in stage_names

    def test_complex_process_with_multiple_gates_per_stage(self, tmp_path):
        """Verify loading of complex processes with multiple gates per stage."""
        # Arrange
        complex_config = {
            "process": {
                "name": "complex_workflow",
                "description": "Complex multi-gate workflow",
                "initial_stage": "draft",
                "final_stage": "published",
                "stages": {
                    "draft": {
                        "name": "Draft Content",
                        "gates": {
                            "submit_for_review": {
                                "target_stage": "review",
                                "locks": [
                                    {"exists": "content.title"},
                                    {"exists": "content.body"},
                                    {
                                        "type": "greater_than",
                                        "property_path": "content.word_count",
                                        "expected_value": 100,
                                    },
                                ],
                            },
                            "save_as_template": {
                                "target_stage": "template",
                                "locks": [
                                    {"exists": "content.title"},
                                    {
                                        "type": "equals",
                                        "property_path": "content.type",
                                        "expected_value": "template",
                                    },
                                ],
                            },
                            "discard": {
                                "target_stage": "discarded",
                                "locks": [
                                    {
                                        "type": "equals",
                                        "property_path": "action",
                                        "expected_value": "discard",
                                    }
                                ],
                            },
                        },
                    },
                    "review": {
                        "name": "Under Review",
                        "gates": {
                            "approve": {
                                "target_stage": "published",
                                "locks": [
                                    {"exists": "review.decision"},
                                    {
                                        "type": "equals",
                                        "property_path": "review.decision",
                                        "expected_value": "approved",
                                    },
                                ],
                            },
                            "reject": {
                                "target_stage": "draft",
                                "locks": [
                                    {"exists": "review.decision"},
                                    {
                                        "type": "equals",
                                        "property_path": "review.decision",
                                        "expected_value": "rejected",
                                    },
                                ],
                            },
                        },
                    },
                    "template": {
                        "name": "Template Library",
                        "gates": {
                            "finalize_template": {
                                "target_stage": "published",
                                "locks": [
                                    {
                                        "type": "equals",
                                        "property_path": "template.finalized",
                                        "expected_value": True,
                                    }
                                ],
                            }
                        },
                    },
                    "published": {"name": "Published Content", "gates": {}},
                    "discarded": {
                        "name": "Discarded Content",
                        "gates": {
                            "archive": {
                                "target_stage": "published",
                                "locks": [
                                    {
                                        "type": "equals",
                                        "property_path": "action",
                                        "expected_value": "archive",
                                    }
                                ],
                            }
                        },
                    },
                },
            }
        }

        json_file = tmp_path / "complex_workflow.json"
        json_file.write_text(json.dumps(complex_config, indent=2))

        # Act
        process = load_process(json_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "complex_workflow"
        assert len(process.stages) == 5

        # Verify draft stage has 3 gates
        draft_stage = next(stage for stage in process.stages if stage._id == "draft")
        assert len(draft_stage.gates) == 3

        # Verify review stage has 2 gates
        review_stage = next(stage for stage in process.stages if stage._id == "review")
        assert len(review_stage.gates) == 2

    def test_error_handling_with_nested_exceptions(self, tmp_path):
        """Verify proper error handling and exception chaining."""
        # Arrange
        invalid_process_config = {
            "process": {
                "name": "invalid_config",
                "stages": {
                    "stage1": {
                        "gates": {
                            "invalid_gate": {
                                "target_stage": "stage2",
                                "locks": [
                                    {
                                        "type": "invalid_lock_type",
                                        "property_path": "field",
                                        "expected_value": "value",
                                    }
                                ],
                            }
                        }
                    }
                },
            }
        }

        json_file = tmp_path / "invalid_config.json"
        json_file.write_text(json.dumps(invalid_process_config, indent=2))

        # Act & Assert
        with pytest.raises(LoadError) as exc_info:
            load_process(json_file)

        # Verify error message includes file path and nested exception info
        error_message = str(exc_info.value)
        assert "Failed to load" in error_message
        assert str(json_file) in error_message
        assert exc_info.value.__cause__ is not None  # Verify exception chaining


# Fixtures for comprehensive testing
@pytest.fixture
def sample_process_config() -> dict[str, Any]:
    """Sample process configuration for reuse across tests."""
    return {
        "name": "sample_process",
        "description": "Sample process for testing",
        "initial_stage": "start",
        "final_stage": "end",
        "stages": {
            "start": {
                "name": "Start Stage",
                "description": "Initial stage",
                "gates": {
                    "proceed": {
                        "description": "Proceed to next stage",
                        "target_stage": "middle",
                        "locks": [
                            {"exists": "required_field"},
                            {"type": "not_empty", "property_path": "required_field"},
                        ],
                    }
                },
            },
            "middle": {
                "name": "Middle Stage",
                "description": "Intermediate stage",
                "gates": {
                    "advance": {
                        "target_stage": "end",
                        "locks": [
                            {
                                "type": "equals",
                                "property_path": "status",
                                "expected_value": "ready",
                            }
                        ],
                    },
                    "rollback": {
                        "target_stage": "start",
                        "locks": [
                            {
                                "type": "equals",
                                "property_path": "action",
                                "expected_value": "rollback",
                            }
                        ],
                    },
                },
            },
            "end": {
                "name": "End Stage",
                "description": "Final stage",
                "is_final": True,
                "gates": [],
            },
        },
    }


@pytest.fixture
def sample_yaml_file(tmp_path, sample_process_config) -> Path:
    """Create a temporary YAML file with sample process configuration."""
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe", pure=True)

    yaml_data = {"process": sample_process_config}
    yaml_file = tmp_path / "sample_process.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(yaml_data, f)
    return yaml_file


@pytest.fixture
def sample_json_file(tmp_path, sample_process_config) -> Path:
    """Create a temporary JSON file with sample process configuration."""
    json_data = {"process": sample_process_config}
    json_file = tmp_path / "sample_process.json"
    json_file.write_text(json.dumps(json_data, indent=2))
    return json_file


def _dict_to_yaml_string(data: dict[str, Any], indent: int = 0) -> str:
    """Helper function to convert dictionary to YAML-like string for testing."""
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe", pure=True)
    from io import StringIO

    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue().strip()


class TestLoader:
    """Test cases for the Loader class."""

    def test_loader_process_loads_from_yaml(self, sample_yaml_file: Path):
        """Verify Loader.process successfully loads a Process from a YAML file."""
        # Act
        process = Loader.process(sample_yaml_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "sample_process"

    def test_loader_process_loads_from_json(self, sample_json_file: Path):
        """Verify Loader.process successfully loads a Process from a JSON file."""
        # Act
        process = Loader.process(sample_json_file)

        # Assert
        assert isinstance(process, Process)
        assert process.name == "sample_process"

    def test_loader_element_loads_from_json(self, tmp_path: Path):
        """Verify Loader.element successfully loads an Element from a JSON file."""
        # Arrange
        element_data = {"user_id": "123", "email": "test@example.com"}
        element_file = tmp_path / "element.json"
        element_file.write_text(json.dumps(element_data))

        # Act
        element = Loader.element(element_file)

        # Assert
        assert isinstance(element, Element)
        assert element.get_property("user_id") == "123"
        assert element.get_property("email") == "test@example.com"

    def test_loader_process_raises_load_error_for_non_existent_file(self):
        """Verify Loader.process raises LoadError for a non-existent file."""
        # Arrange
        non_existent_file = "/tmp/non_existent_process.yaml"

        # Act & Assert
        with pytest.raises(LoadError, match="File not found"):
            Loader.process(non_existent_file)

    def test_loader_element_raises_load_error_for_non_existent_file(self):
        """Verify Loader.element raises LoadError for a non-existent file."""
        # Arrange
        non_existent_file = "/tmp/non_existent_element.json"

        # Act & Assert
        with pytest.raises(LoadError, match="File not found"):
            Loader.element(non_existent_file)

    def test_loader_element_raises_load_error_for_invalid_json(self, tmp_path: Path):
        """Verify Loader.element raises LoadError for invalid JSON."""
        # Arrange
        invalid_json = '{"user_id": "123", "email": "test@example.com",}'
        element_file = tmp_path / "invalid_element.json"
        element_file.write_text(invalid_json)

        # Act & Assert
        with pytest.raises(LoadError, match="Error parsing JSON"):
            Loader.element(element_file)
