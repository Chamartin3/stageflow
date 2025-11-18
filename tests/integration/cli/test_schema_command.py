"""Integration tests for schema command."""

import json
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from stageflow.cli.main import app


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture(scope="module")
def test_data_dir() -> Path:
    """Get the test data directory."""
    data_path = Path(__file__).parent.parent / "data"
    assert data_path.exists(), f"Test data directory not found at {data_path}"
    return data_path


@pytest.fixture(scope="module")
def user_onboarding_process(test_data_dir: Path) -> Path:
    """Get the user onboarding process file."""
    file_path = test_data_dir / "manager_testing" / "user_onboarding.yaml"
    assert file_path.exists(), f"User onboarding file not found at {file_path}"
    return file_path


def validate_json_schema(schema_dict: dict) -> bool:
    """Validate that schema is valid JSON Schema Draft-07."""
    try:
        import jsonschema

        jsonschema.Draft7Validator.check_schema(schema_dict)
        return True
    except ImportError:
        # If jsonschema is not available, skip validation
        pytest.skip("jsonschema not available for validation")
    except Exception:
        return False


def run_schema_command(runner: CliRunner, source: str, stage: str, **options) -> Any:
    """Helper to run schema command with options."""
    args = ["process", "schema", source, stage]

    if options.get("stage_specific"):
        args.append("--stage-specific")
    if options.get("output"):
        args.extend(["--output", str(options["output"])])
    if options.get("json"):
        args.append("--json")

    return runner.invoke(app, args)


class TestSchemaCommandBasic:
    """Test basic schema command execution."""

    def test_schema_command_file_source(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test schema generation with file source."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification"
        )

        assert result.exit_code == 0
        assert (
            "Schema generated successfully" not in result.output
        )  # Should be stdout only
        assert "$schema" in result.output
        assert "type: object" in result.output

    def test_schema_cumulative_default(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test cumulative schema generation (default)."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification"
        )

        assert result.exit_code == 0
        # Should include properties from all stages in path
        assert "email:" in result.output
        assert "user_id:" in result.output
        assert "verification:" in result.output

    def test_schema_stage_specific(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test stage-specific schema generation."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification", stage_specific=True
        )

        assert result.exit_code == 0
        # Should only include Verification stage properties
        assert "verification:" in result.output
        assert "email:" not in result.output  # From earlier stages
        assert "user_id:" not in result.output  # From earlier stages

    def test_schema_stdout_output(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test schema output to stdout (default)."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification"
        )

        assert result.exit_code == 0
        assert len(result.output.strip()) > 0
        # Should not have success message (only in file output)
        assert "Schema generated successfully" not in result.output

    def test_schema_file_output(
        self, runner: CliRunner, user_onboarding_process: Path, tmp_path: Path
    ):
        """Test schema output to file."""
        output_file = tmp_path / "test_schema.yaml"
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification", output=output_file
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Check success message in output
        assert "Schema generated successfully" in result.output
        assert "Verification" in result.output
        assert str(output_file) in result.output

        # Check file contents
        content = output_file.read_text()
        assert "$schema" in content
        assert "type: object" in content

    def test_schema_json_mode(self, runner: CliRunner, user_onboarding_process: Path):
        """Test JSON output format."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification", json=True
        )

        assert result.exit_code == 0
        # Should be valid JSON
        schema_dict = json.loads(result.output)
        assert schema_dict["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema_dict["type"] == "object"
        assert "properties" in schema_dict

    def test_schema_yaml_mode(self, runner: CliRunner, user_onboarding_process: Path):
        """Test YAML output format (default)."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification"
        )

        assert result.exit_code == 0
        # Should be valid YAML
        yaml_parser = YAML(typ="safe")
        schema_dict = yaml_parser.load(result.output)
        assert schema_dict["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema_dict["type"] == "object"
        assert "properties" in schema_dict


class TestSchemaCommandErrors:
    """Test error handling in schema command."""

    def test_invalid_process_source(self, runner: CliRunner):
        """Test error for invalid process source."""
        result = run_schema_command(runner, "nonexistent.yaml", "stage")

        assert result.exit_code == 1
        assert "Failed to load process" in result.output

    def test_nonexistent_stage(self, runner: CliRunner, user_onboarding_process: Path):
        """Test error for non-existent stage."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "NonExistentStage"
        )

        assert result.exit_code == 1
        assert "Stage 'NonExistentStage' not found" in result.output

    def test_unreachable_stage(self, runner: CliRunner):
        """Test error for unreachable stage."""
        # Create a process with unreachable stage
        unreachable_process = {
            "name": "unreachable_test",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "complete"}],
                        }
                    ]
                },
                "unreachable": {},  # No path from start
                "end": {"is_final": True},
            },
        }

        import os
        import tempfile

        yaml_writer = YAML()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_writer.dump(unreachable_process, f)
            temp_file = f.name

        try:
            result = run_schema_command(runner, temp_file, "unreachable")
            assert result.exit_code == 1
            assert "No path found" in result.output
        finally:
            os.unlink(temp_file)


class TestSchemaCommandRealWorld:
    """Test with real-world example processes."""

    def test_user_onboarding_process(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test with user_onboarding.yaml example."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification"
        )

        assert result.exit_code == 0
        yaml_parser = YAML(typ="safe")
        schema_dict = yaml_parser.load(result.output)
        assert validate_json_schema(schema_dict)

        # Should have properties from the onboarding process
        assert "email" in schema_dict["properties"]
        assert "verification" in schema_dict["properties"]

    def test_minimal_process(self, runner: CliRunner):
        """Test with minimal process definition."""
        minimal_process = {
            "name": "minimal",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "expected_properties": {"data": {"type": "string"}},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "data"}],
                        }
                    ],
                },
                "end": {"is_final": True},
            },
        }

        import os
        import tempfile

        yaml_writer = YAML()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_writer.dump(minimal_process, f)
            temp_file = f.name

        try:
            result = run_schema_command(runner, temp_file, "start")
            assert result.exit_code == 0

            yaml_parser = YAML(typ="safe")
            schema_dict = yaml_parser.load(result.output)
            assert validate_json_schema(schema_dict)
            assert "data" in schema_dict["properties"]
            assert "required" in schema_dict
            assert "data" in schema_dict["required"]
        finally:
            os.unlink(temp_file)


class TestSchemaValidation:
    """Test that generated schemas are valid JSON Schema."""

    def test_generated_schema_validates(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test that generated schema is valid JSON Schema Draft-07."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification", json=True
        )

        assert result.exit_code == 0
        schema_dict = json.loads(result.output)
        assert validate_json_schema(schema_dict)

    def test_schema_structure_correct(
        self, runner: CliRunner, user_onboarding_process: Path
    ):
        """Test that schema has correct structure."""
        result = run_schema_command(
            runner, str(user_onboarding_process), "Verification", json=True
        )

        assert result.exit_code == 0
        schema_dict = json.loads(result.output)

        # Required JSON Schema fields
        assert "$schema" in schema_dict
        assert schema_dict["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema_dict["type"] == "object"
        assert "properties" in schema_dict
        assert isinstance(schema_dict["properties"], dict)

        # StageFlow specific fields
        assert "title" in schema_dict
        assert "description" in schema_dict
        assert "Verification" in schema_dict["title"]

        # Should have required fields based on EXISTS locks
        if "required" in schema_dict:
            assert isinstance(schema_dict["required"], list)
            # All required fields should exist in properties
            for req_field in schema_dict["required"]:
                assert req_field in schema_dict["properties"]
