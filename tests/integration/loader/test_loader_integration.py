"""Integration tests for the simplified loader implementation."""

import json
import subprocess
import time
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from stageflow import LoadError, load_element, load_process
from stageflow.elements import Element
from stageflow.process import Process


class TestLoaderAPI:
    """Test that loader API functions work correctly."""

    def test_process_loading(self, tmp_path):
        """Test that process loading works correctly."""
        # Test with a complex process from examples
        example_process = Path(
            "examples/process_validation/valid_processes/simple_2stage.yaml"
        )
        if example_process.exists():
            # Load using new interface
            process = load_process(example_process)

            # Verify it's a valid Process object
            assert isinstance(process, Process)
            assert process.name
            assert process.initial_stage
            assert process.final_stage

    def test_element_loading(self, tmp_path):
        """Test that element loading works correctly."""
        # Test with an example element
        example_element = Path(
            "examples/case2_element_validation/normal_flow/ready_elements/user_ready_for_activation.json"
        )
        if example_element.exists():
            # Load using new interface
            element = load_element(example_element)

            # Verify it's a valid Element object
            assert isinstance(element, Element)
            assert element.get_property("email")  # Should have email property


class TestCLIIntegration:
    """Test that CLI works with loader API."""

    def test_cli_process_loading(self, tmp_path):
        """Test CLI can load processes correctly."""
        process_data = {
            "process": {
                "name": "cli_test_process",
                "initial_stage": "draft",
                "final_stage": "published",
                "stages": {
                    "draft": {
                        "gates": {
                            "submit": {
                                "target_stage": "published",
                                "locks": [
                                    {"property_path": "content", "type": "exists"}
                                ],
                            }
                        }
                    },
                    "published": {"is_final": True},
                },
            }
        }

        process_file = tmp_path / "cli_process.yaml"
        yaml = YAML()
        with open(process_file, "w") as f:
            yaml.dump(process_data, f)

        # Test CLI process validation
        result = subprocess.run(
            ["uv", "run", "stageflow", "process", "view", str(process_file)],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0
        assert "cli_test_process" in result.stdout
        assert "Valid" in result.stdout

    def test_cli_element_evaluation(self, tmp_path):
        """Test CLI can evaluate elements correctly."""
        # Create process file
        process_data = {
            "process": {
                "name": "cli_eval_process",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "gates": {
                            "proceed": {
                                "target_stage": "end",
                                "locks": [
                                    {"property_path": "approved", "type": "exists"}
                                ],
                            }
                        }
                    },
                    "end": {"is_final": True},
                },
            }
        }

        process_file = tmp_path / "cli_eval_process.yaml"
        yaml = YAML()
        with open(process_file, "w") as f:
            yaml.dump(process_data, f)

        # Create element file
        element_data = {"approved": True, "user_id": 456}
        element_file = tmp_path / "cli_element.json"
        with open(element_file, "w") as f:
            json.dump(element_data, f)

        # Test CLI element evaluation
        result = subprocess.run(
            [
                "uv",
                "run",
                "stageflow",
                "evaluate",
                str(process_file),
                "-e",
                str(element_file),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0
        assert "Evaluation Result" in result.stdout
        assert "Current Stage:" in result.stdout


class TestErrorMessageQuality:
    """Test that error messages are helpful and specific."""

    def test_file_not_found_error(self, tmp_path):
        """Test helpful error message for missing files."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(LoadError) as exc_info:
            load_process(nonexistent_file)

        error_msg = str(exc_info.value)
        assert "Process file not found" in error_msg
        assert str(nonexistent_file) in error_msg

    def test_invalid_yaml_error(self, tmp_path):
        """Test helpful error message for invalid YAML."""
        invalid_yaml_file = tmp_path / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("invalid: yaml: content: [\n")

        with pytest.raises(LoadError) as exc_info:
            load_process(invalid_yaml_file)

        error_msg = str(exc_info.value)
        assert "Failed to read file" in error_msg

    def test_invalid_json_error(self, tmp_path):
        """Test helpful error message for invalid JSON."""
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, "w") as f:
            f.write('{"invalid": json content}')

        with pytest.raises(LoadError) as exc_info:
            load_element(invalid_json_file)

        error_msg = str(exc_info.value)
        assert "Error parsing JSON" in error_msg

    def test_wrong_file_type_error(self, tmp_path):
        """Test helpful error message when loading wrong file types."""
        # Try to load element data as process
        element_data = {"user_id": 123, "email": "test@example.com"}
        wrong_file = tmp_path / "element_as_process.json"
        with open(wrong_file, "w") as f:
            json.dump(element_data, f)

        with pytest.raises(LoadError) as exc_info:
            load_process(wrong_file)

        error_msg = str(exc_info.value)
        assert "Process missing required field" in error_msg


class TestPerformanceCharacteristics:
    """Test that loading performance is acceptable."""

    def test_process_loading_performance(self, tmp_path):
        """Test that process loading is reasonably fast."""
        # Create a moderately complex process
        stages = {}
        for i in range(20):
            stage_id = f"stage_{i}"
            gates = {}
            if i < 19:
                gates[f"gate_{i}"] = {
                    "target_stage": f"stage_{i + 1}",
                    "locks": [
                        {"property_path": f"prop_{j}", "type": "exists"}
                        for j in range(5)
                    ],
                }
            stages[stage_id] = {"gates": gates}
            if i == 19:
                stages[stage_id]["is_final"] = True

        process_data = {
            "process": {
                "name": "performance_test_process",
                "initial_stage": "stage_0",
                "final_stage": "stage_19",
                "stages": stages,
            }
        }

        process_file = tmp_path / "perf_process.yaml"
        yaml = YAML()
        with open(process_file, "w") as f:
            yaml.dump(process_data, f)

        # Measure loading time
        start_time = time.time()
        for _ in range(10):  # Load multiple times to get average
            process = load_process(process_file)
        end_time = time.time()

        avg_load_time = (end_time - start_time) / 10
        assert avg_load_time < 0.1  # Should load in under 100ms
        assert isinstance(process, Process)

    def test_element_loading_performance(self, tmp_path):
        """Test that element loading is reasonably fast."""
        # Create a large element with many properties
        element_data = {f"prop_{i}": f"value_{i}" for i in range(1000)}
        element_data["user_id"] = "12345"

        element_file = tmp_path / "perf_element.json"
        with open(element_file, "w") as f:
            json.dump(element_data, f)

        # Measure loading time
        start_time = time.time()
        for _ in range(50):  # Load multiple times
            element = load_element(element_file)
        end_time = time.time()

        avg_load_time = (end_time - start_time) / 50
        assert avg_load_time < 0.01  # Should load in under 10ms
        assert isinstance(element, Element)
        assert element.get_property("user_id") == "12345"


class TestRealWorldUsage:
    """Test with real example files to verify end-to-end functionality."""

    def test_example_files_loading(self):
        """Test loading real example files from the examples directory."""
        # Test various example processes
        base_path = Path(__file__).parent.parent.parent.parent
        example_processes = [
            base_path
            / "examples/process_validation/valid_processes/simple_2stage.yaml",
            base_path
            / "examples/process_validation/valid_processes/complex_multistage.yaml",
            base_path
            / "examples/case4_manager_testing/sample_processes/user_onboarding.yaml",
        ]

        for process_path in example_processes:
            if Path(process_path).exists():
                process = load_process(process_path)
                assert isinstance(process, Process)
                assert process.name
                assert process.initial_stage
                assert process.final_stage

    def test_example_elements_loading(self):
        """Test loading real example elements."""
        base_path = Path(__file__).parent.parent.parent.parent
        example_elements = [
            base_path
            / "examples/case2_element_validation/normal_flow/ready_elements/user_ready_for_activation.json",
            base_path
            / "examples/case2_element_validation/default_properties/user_needs_defaults.json",
        ]

        for element_path in example_elements:
            if Path(element_path).exists():
                element = load_element(element_path)
                assert isinstance(element, Element)
                # Should have some common properties
                assert element.get_property("email") or element.get_property("user_id")
