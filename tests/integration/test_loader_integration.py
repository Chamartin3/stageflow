"""Integration tests for the simplified loader implementation."""

import json
import subprocess
import time
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from stageflow import Loader, LoadError, load_element, load_process
from stageflow.element import Element
from stageflow.process import Process


class TestDualInterfaceConsistency:
    """Test that function-based and class-based interfaces return identical results."""

    def test_process_loading_consistency(self, tmp_path):
        """Test that Loader.process() and load_process() return identical Process objects."""
        process_data = {
            "process": {
                "name": "test_process",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "gates": {
                            "to_end": {
                                "target_stage": "end",
                                "locks": [
                                    {"property_path": "ready", "type": "exists"}
                                ]
                            }
                        }
                    },
                    "end": {
                        "is_final": True
                    }
                }
            }
        }

        # Create temporary YAML file
        process_file = tmp_path / "test_process.yaml"
        yaml = YAML()
        with open(process_file, 'w') as f:
            yaml.dump(process_data, f)

        # Load using both interfaces
        process_class = Loader.process(process_file)
        process_func = load_process(process_file)

        # Verify they are equivalent Process objects
        assert isinstance(process_class, Process)
        assert isinstance(process_func, Process)
        assert process_class.name == process_func.name == "test_process"
        assert process_class.initial_stage._id == process_func.initial_stage._id == "start"
        assert process_class.final_stage._id == process_func.final_stage._id == "end"

    def test_element_loading_consistency(self, tmp_path):
        """Test that Loader.element() and load_element() return identical Element objects."""
        element_data = {
            "user_id": 123,
            "email": "test@example.com",
            "ready": True
        }

        # Create temporary JSON file
        element_file = tmp_path / "test_element.json"
        with open(element_file, 'w') as f:
            json.dump(element_data, f)

        # Load using both interfaces
        element_class = Loader.element(element_file)
        element_func = load_element(element_file)

        # Verify they are equivalent Element objects
        assert isinstance(element_class, Element)
        assert isinstance(element_func, Element)
        assert element_class.get_property("user_id") == element_func.get_property("user_id") == 123
        assert element_class.get_property("email") == element_func.get_property("email") == "test@example.com"
        assert element_class.get_property("ready") == element_func.get_property("ready") is True


class TestBackwardCompatibility:
    """Test that existing code patterns continue to work."""

    def test_existing_process_patterns(self, tmp_path):
        """Test that existing process loading patterns still work."""
        # Test with a complex process from examples
        example_process = Path("examples/case1_process_creation/valid_processes/simple_2stage.yaml")
        if example_process.exists():
            # Load using new interface
            process = load_process(example_process)

            # Verify it's a valid Process object
            assert isinstance(process, Process)
            assert process.name
            assert process.initial_stage
            assert process.final_stage

    def test_existing_element_patterns(self, tmp_path):
        """Test that existing element loading patterns still work."""
        # Test with an example element
        example_element = Path("examples/case2_element_validation/normal_flow/ready_elements/user_ready_for_activation.json")
        if example_element.exists():
            # Load using new interface
            element = load_element(example_element)

            # Verify it's a valid Element object
            assert isinstance(element, Element)
            assert element.get_property("email")  # Should have email property


class TestCLIIntegration:
    """Test that CLI works with new element loading."""

    def test_cli_process_loading(self, tmp_path):
        """Test CLI can load processes using new loader."""
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
                                ]
                            }
                        }
                    },
                    "published": {
                        "is_final": True
                    }
                }
            }
        }

        process_file = tmp_path / "cli_process.yaml"
        yaml = YAML()
        with open(process_file, 'w') as f:
            yaml.dump(process_data, f)

        # Test CLI process validation
        result = subprocess.run(
            ["uv", "run", "stageflow", "eval", "-p", str(process_file)],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        assert result.returncode == 0
        assert "cli_test_process" in result.stdout
        assert "Valid" in result.stdout

    def test_cli_element_evaluation(self, tmp_path):
        """Test CLI can evaluate elements using new loader."""
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
                            ]
                            }
                        }
                    },
                    "end": {
                        "is_final": True
                    }
                }
            }
        }

        process_file = tmp_path / "cli_eval_process.yaml"
        yaml = YAML()
        with open(process_file, 'w') as f:
            yaml.dump(process_data, f)

        # Create element file
        element_data = {"approved": True, "user_id": 456}
        element_file = tmp_path / "cli_element.json"
        with open(element_file, 'w') as f:
            json.dump(element_data, f)

        # Test CLI element evaluation
        result = subprocess.run(
            ["uv", "run", "stageflow", "eval", "-p", str(process_file), "-e", str(element_file)],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        assert result.returncode == 0
        assert "cli_eval_process" in result.stdout
        assert "Evaluation Result" in result.stdout


class TestErrorMessageQuality:
    """Test that error messages are helpful and specific."""

    def test_file_not_found_error(self, tmp_path):
        """Test helpful error message for missing files."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(LoadError) as exc_info:
            load_process(nonexistent_file)

        error_msg = str(exc_info.value)
        assert "File not found" in error_msg
        assert str(nonexistent_file) in error_msg

    def test_invalid_yaml_error(self, tmp_path):
        """Test helpful error message for invalid YAML."""
        invalid_yaml_file = tmp_path / "invalid.yaml"
        with open(invalid_yaml_file, 'w') as f:
            f.write("invalid: yaml: content: [\n")

        with pytest.raises(LoadError) as exc_info:
            load_process(invalid_yaml_file)

        error_msg = str(exc_info.value)
        assert "Error parsing YAML" in error_msg

    def test_invalid_json_error(self, tmp_path):
        """Test helpful error message for invalid JSON."""
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, 'w') as f:
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
        with open(wrong_file, 'w') as f:
            json.dump(element_data, f)

        with pytest.raises(LoadError) as exc_info:
            load_process(wrong_file)

        error_msg = str(exc_info.value)
        assert "File must contain either a 'process' key or process definition at root level" in error_msg
        assert "use load_element() instead" in error_msg


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
                    "target_stage": f"stage_{i+1}",
                    "locks": [
                        {"property_path": f"prop_{j}", "type": "exists"}
                        for j in range(5)
                    ]
                }
            stages[stage_id] = {"gates": gates}
            if i == 19:
                stages[stage_id]["is_final"] = True

        process_data = {
            "process": {
                "name": "performance_test_process",
                "initial_stage": "stage_0",
                "final_stage": "stage_19",
                "stages": stages
            }
        }

        process_file = tmp_path / "perf_process.yaml"
        yaml = YAML()
        with open(process_file, 'w') as f:
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
        with open(element_file, 'w') as f:
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
            base_path / "examples/case1_process_creation/valid_processes/simple_2stage.yaml",
            base_path / "examples/case1_process_creation/valid_processes/complex_multistage.yaml",
            base_path / "examples/case4_manager_testing/sample_processes/user_onboarding.yaml"
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
            base_path / "examples/case2_element_validation/normal_flow/ready_elements/user_ready_for_activation.json",
            base_path / "examples/case2_element_validation/default_properties/user_needs_defaults.json"
        ]

        for element_path in example_elements:
            if Path(element_path).exists():
                element = load_element(element_path)
                assert isinstance(element, Element)
                # Should have some common properties
                assert element.get_property("email") or element.get_property("user_id")


class TestLoaderClassInterface:
    """Test the Loader class interface specifically."""

    def test_loader_class_methods(self, tmp_path):
        """Test that Loader class methods work correctly."""
        # Create test files
        process_data = {
            "process": {
                "name": "loader_class_test",
                "initial_stage": "init",
                "final_stage": "done",
                "stages": {
                    "init": {"gates": {"advance": {"target_stage": "done", "locks": [{"property_path": "ready", "type": "exists"}]}}},
                    "done": {"is_final": True}
                }
            }
        }

        element_data = {"ready": True, "user_id": 789}

        process_file = tmp_path / "loader_test.yaml"
        element_file = tmp_path / "loader_test.json"

        yaml = YAML()
        with open(process_file, 'w') as f:
            yaml.dump(process_data, f)
        with open(element_file, 'w') as f:
            json.dump(element_data, f)

        # Test Loader class methods
        process = Loader.process(process_file)
        element = Loader.element(element_file)

        assert isinstance(process, Process)
        assert isinstance(element, Element)
        assert process.name == "loader_class_test"
        assert element.get_property("user_id") == 789

        # Test evaluation works
        result = process.evaluate(element)
        assert result is not None
        assert 'stage' in result
        assert 'stage_result' in result