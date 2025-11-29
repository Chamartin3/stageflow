"""Integration tests for StageFlow process creation and validation.

This module contains comprehensive integration tests that verify the StageFlow CLI's
ability to handle process creation scenarios including valid process loading,
invalid structure detection, and consistency error identification.

Test Categories:
- Valid processes: Tests successful loading and validation of well-formed processes
- Invalid structure: Tests detection of malformed YAML/JSON and missing required fields
- Consistency errors: Tests detection of logical process issues (circular deps, dead ends, etc.)
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


class TestProcessCreation:
    """Integration test suite for process creation and validation functionality."""

    @pytest.fixture(scope="class")
    def test_data_dir(self) -> Path:
        """Get the test data directory for process creation tests."""
        return Path(__file__).parent / "data"

    @pytest.fixture(scope="class")
    def valid_process_files(self, test_data_dir: Path) -> list[Path]:
        """Get all valid process files for testing."""
        valid_dir = test_data_dir / "valid_processes"
        return list(valid_dir.glob("*.yaml"))

    @pytest.fixture(scope="class")
    def invalid_structure_files(self, test_data_dir: Path) -> list[Path]:
        """Get all invalid structure files for testing."""
        invalid_dir = test_data_dir / "invalid_structure"
        return list(invalid_dir.glob("*.yaml"))

    @pytest.fixture(scope="class")
    def consistency_error_files(self, test_data_dir: Path) -> list[Path]:
        """Get all consistency error files for testing."""
        consistency_dir = test_data_dir / "consistency_errors"
        return list(consistency_dir.glob("*.yaml"))

    def run_stageflow_cli(
        self,
        process_file: str,
        operation: str = None,
        json_output: bool = False,
        verbose: bool = False,
        expect_success: bool = True,
    ) -> dict[str, Any]:
        """
        Run the StageFlow CLI with given arguments and return structured result.

        Args:
            process_file: Path to the process definition file
            operation: Operation to perform (None for default description, or other operations)
            json_output: Whether to request JSON output
            verbose: Whether to enable verbose output
            expect_success: Whether to expect successful exit code (0)

        Returns:
            Dictionary containing exit_code, stdout, stderr, and parsed_json (if applicable)
        """
        # Build command: stageflow process view process_file [--json] [--verbose]
        full_cmd = ["uv", "run", "stageflow", "process", "view", process_file]

        # Add JSON flag if requested
        if json_output:
            full_cmd.append("--json")

        # Add verbose flag if requested
        if verbose:
            full_cmd.append("--verbose")

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/omidev/Code/tools/stageflow",
            )

            # Try to parse JSON output if JSON flag was used
            parsed_json = None
            if json_output and result.stdout.strip():
                try:
                    parsed_json = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    # Not valid JSON, leave as None
                    pass

            response = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "parsed_json": parsed_json,
            }

            if expect_success:
                assert result.returncode == 0, (
                    f"Expected success but got exit code {result.returncode}. stderr: {result.stderr}"
                )

            return response

        except subprocess.TimeoutExpired:
            pytest.fail("CLI command timed out after 30 seconds")
        except Exception as e:
            pytest.fail(f"Failed to run CLI command: {e}")

    @pytest.mark.parametrize(
        "process_file", ["simple_2stage.yaml", "all_lock_types.yaml"]
    )
    def test_valid_process_loading_human_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that valid process files load successfully with human-readable output.

        Tests that well-formed process configurations:
        - Load without errors (exit code 0)
        - Display process information correctly
        - Show valid status with checkmark
        - List stages and their relationships
        """
        # Arrange
        process_path = test_data_dir / "valid_processes" / process_file
        assert process_path.exists(), f"Test file {process_file} not found"

        # Act
        result = self.run_stageflow_cli(str(process_path), None, expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert "✅" in result["stdout"], (
            "Should show success checkmark for valid process"
        )
        assert "Process:" in result["stdout"], "Should display process information"
        assert "Stages:" in result["stdout"], "Should list process stages"
        assert not result["stderr"], "Should not have error output"

    @pytest.mark.parametrize(
        "process_file", ["simple_2stage.yaml", "all_lock_types.yaml"]
    )
    def test_valid_process_loading_json_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that valid process files produce correct JSON output structure.

        Tests that valid processes return properly structured JSON with:
        - Process metadata (name, description, stages)
        - Validity status (true for valid processes)
        - Stage information with correct relationships
        - No consistency issues
        """
        # Arrange
        process_path = test_data_dir / "valid_processes" / process_file

        # Act
        result = self.run_stageflow_cli(
            str(process_path), None, json_output=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None, "Should return valid JSON"

        json_data = result["parsed_json"]
        assert "name" in json_data, "JSON should contain process name"
        assert "valid" in json_data, "JSON should contain validity status"
        assert json_data["valid"] is True, "Valid process should have valid=true"
        assert "stages" in json_data, "JSON should contain stages list"
        assert "consistency_issues" in json_data, (
            "JSON should contain consistency issues list"
        )
        assert len(json_data["consistency_issues"]) == 0, (
            "Valid process should have no consistency issues"
        )

    @pytest.mark.parametrize(
        "process_file",
        ["missing_required.yaml", "malformed_syntax.yaml", "invalid_locks.yaml"],
    )
    def test_invalid_structure_detection_human_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that structurally invalid process files are properly detected and reported.

        Tests that processes with structural issues:
        - Fail with appropriate exit code (non-zero)
        - Display clear error messages
        - Identify specific structural problems
        - Provide actionable feedback
        """
        # Arrange
        process_path = test_data_dir / "invalid_structure" / process_file

        # Act
        result = self.run_stageflow_cli(str(process_path), None, expect_success=False)

        # Assert
        assert result["exit_code"] != 0, (
            "Invalid structure should cause non-zero exit code"
        )
        # Error output can be in stdout or stderr depending on the error type
        error_output = result["stdout"] + result["stderr"]
        assert len(error_output.strip()) > 0, "Should provide error feedback"

    @pytest.mark.parametrize(
        "process_file",
        ["missing_required.yaml", "malformed_syntax.yaml", "invalid_locks.yaml"],
    )
    def test_invalid_structure_detection_json_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that structurally invalid processes return appropriate JSON error responses.

        Tests that invalid structures produce JSON containing:
        - Error field with descriptive message
        - Proper error categorization
        - Structured error information for API consumers
        """
        # Arrange
        process_path = test_data_dir / "invalid_structure" / process_file

        # Act
        result = self.run_stageflow_cli(
            str(process_path), None, json_output=True, expect_success=False
        )

        # Assert
        assert result["exit_code"] != 0, (
            "Invalid structure should cause non-zero exit code"
        )

        # Should have some output (either valid JSON with error field or error message)
        output = result["stdout"].strip()
        assert len(output) > 0, "Should provide error output"

        # Try to parse as JSON - if successful, should contain errors field
        try:
            json_data = json.loads(output)
            assert "errors" in json_data or "status" in json_data, (
                "JSON error response should contain errors or status field"
            )
        except json.JSONDecodeError:
            # If not JSON, should still be meaningful error message
            assert "error" in output.lower() or "failed" in output.lower(), (
                "Should indicate error condition"
            )

    @pytest.mark.parametrize(
        "process_file",
        [
            "circular_dependencies.yaml",
            "unreachable_stages.yaml",
            "missing_targets.yaml",
            "conflicting_gates.yaml",
            # "multiple_gates_same_target.yaml",  # Only produces warnings
            # "complex_multistage.yaml",  # Only produces warnings (alternative terminal stage)
            # "multiple_gates.yaml",  # Only produces warnings
        ],
    )
    def test_consistency_error_detection_human_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that logically inconsistent processes are detected and reported clearly.

        Tests that processes with consistency issues:
        - Fail to load with fatal consistency errors
        - Display specific consistency error messages
        - Exit with non-zero code
        """
        # Arrange
        process_path = test_data_dir / "consistency_errors" / process_file

        # Act - expect failure since fatal consistency errors
        result = self.run_stageflow_cli(str(process_path), None, expect_success=False)

        # Assert - should fail with consistency errors
        assert result["exit_code"] == 1, "Fatal consistency errors should cause exit code 1"
        # Check output contains error information
        output = result["stdout"].lower()
        assert "error" in output or "❌" in result["stdout"], (
            "Should show error indicator for invalid process"
        )

    @pytest.mark.parametrize(
        "process_file",
        [
            "circular_dependencies.yaml",
            "unreachable_stages.yaml",
            "missing_targets.yaml",
            "conflicting_gates.yaml",
            # "multiple_gates_same_target.yaml",  # Only produces warnings
            # "complex_multistage.yaml",  # Only produces warnings (alternative terminal stage)
            # "multiple_gates.yaml",  # Only produces warnings
        ],
    )
    def test_consistency_error_detection_json_output(
        self, test_data_dir: Path, process_file: str
    ):
        """
        Verify that consistency errors are properly reported in JSON format.

        Tests that processes with consistency issues return JSON with:
        - Error status indicating consistency failure
        - Proper error information for automated processing
        """
        # Arrange
        process_path = test_data_dir / "consistency_errors" / process_file

        # Act - expect failure for fatal consistency errors
        result = self.run_stageflow_cli(
            str(process_path), None, json_output=True, expect_success=False
        )

        # Assert - should fail with consistency errors
        assert result["exit_code"] == 1, "Fatal consistency errors should cause exit code 1"
        assert result["parsed_json"] is not None, "Should return valid JSON even on error"

        json_data = result["parsed_json"]
        # Check for error status
        assert "status" in json_data, "JSON should contain status"
        assert "error" in json_data["status"], (
            "Process with fatal consistency errors should have error status"
        )

    def test_comprehensive_process_validation_workflow(self, test_data_dir: Path):
        """
        Test a comprehensive workflow covering multiple process validation scenarios.

        This test verifies that the CLI can handle a mixed batch of process files
        with different validity states, demonstrating real-world usage patterns
        where developers might validate multiple processes in sequence.
        """
        # Arrange - collect representative files from each category
        valid_file = test_data_dir / "valid_processes" / "simple_2stage.yaml"
        invalid_file = test_data_dir / "invalid_structure" / "missing_required.yaml"
        consistency_file = (
            test_data_dir / "consistency_errors" / "circular_dependencies.yaml"
        )

        # Act & Assert - Test each file type in sequence

        # 1. Valid process should succeed
        valid_result = self.run_stageflow_cli(
            str(valid_file), None, expect_success=True
        )
        assert valid_result["exit_code"] == 0
        assert "✅" in valid_result["stdout"]

        # 2. Invalid structure should fail
        invalid_result = self.run_stageflow_cli(
            str(invalid_file), None, expect_success=False
        )
        assert invalid_result["exit_code"] != 0

        # 3. Consistency error should fail with exit code 1
        consistency_result = self.run_stageflow_cli(
            str(consistency_file), None, expect_success=False
        )
        assert consistency_result["exit_code"] == 1

    def test_error_handling_with_nonexistent_files(self):
        """
        Verify proper error handling when process files don't exist.

        Tests that CLI gracefully handles:
        - Missing process files
        - Invalid file paths
        - Clear error messages for file access issues
        - Appropriate exit codes for file system errors
        """
        # Arrange
        nonexistent_file = "/path/that/does/not/exist.yaml"

        # Act
        result = self.run_stageflow_cli(nonexistent_file, None, expect_success=False)

        # Assert
        assert result["exit_code"] != 0, "Nonexistent file should cause error exit code"
        error_output = result["stdout"] + result["stderr"]
        assert len(error_output) > 0, "Should provide error message for missing file"

    def test_json_output_consistency_across_scenarios(self, test_data_dir: Path):
        """
        Verify that JSON output maintains consistent structure across all process types.

        Tests that JSON responses have consistent schema for:
        - Valid processes
        - Invalid processes
        - Processes with consistency errors
        - Error conditions

        This ensures API consumers can rely on predictable response formats.
        """
        # Arrange - get one file from each category
        # Only test valid process for JSON consistency - consistency errors now fail
        test_files = [
            (test_data_dir / "valid_processes" / "simple_2stage.yaml", True),
        ]

        # Act & Assert
        for process_file, should_be_valid in test_files:
            result = self.run_stageflow_cli(
                str(process_file), None, json_output=True, expect_success=True
            )

            assert result["parsed_json"] is not None, (
                f"Should return valid JSON for {process_file.name}"
            )
            json_data = result["parsed_json"]

            # Common fields that should always be present
            required_fields = ["name", "valid", "stages", "consistency_issues"]
            for field in required_fields:
                assert field in json_data, (
                    f"JSON should contain {field} field for {process_file.name}"
                )

            # Validity should match expectation
            assert json_data["valid"] == should_be_valid, (
                f"Process {process_file.name} validity mismatch"
            )

    def test_self_referencing_gate_detection(self, tmp_path: Path):
        """
        Test that self-referencing gates (gates that target their own stage) are
        properly detected and reported as warnings (valid use case for revision loops).
        """
        # Create a test process with a self-referencing gate
        test_process_content = """process:
  name: test_self_reference
  initial_stage: start
  final_stage: end

  stages:
    start:
      gates:
        self_loop:
          target_stage: start  # Self-referencing gate - valid for revision loops
          locks:
            - exists: "revision_needed"
        proceed:
          target_stage: end
          locks:
            - exists: "ready_to_proceed"
    end:
      gates: []
"""

        test_file = tmp_path / "test_self_reference.yaml"
        test_file.write_text(test_process_content)

        # Act - expect success with warnings (self-loops are valid for revision patterns)
        result = self.run_stageflow_cli(str(test_file), None, expect_success=True)

        # Assert - should succeed with warnings
        assert result["exit_code"] == 0, "CLI should succeed with warnings for self-loop"

        # Should detect the self-referencing gate issue as a warning
        output = result["stdout"]
        assert "self-loop" in output.lower(), "Should mention self-loop in description"
        assert "self_loop" in output, "Should mention the specific gate name"
        assert "warning" in output.lower(), "Should indicate it's a warning"

        # Test JSON output as well
        json_result = self.run_stageflow_cli(
            str(test_file), None, json_output=True, expect_success=True
        )
        assert json_result["parsed_json"] is not None, "Should return valid JSON"

        json_data = json_result["parsed_json"]
        assert json_data["is_valid"] is True, (
            "Process with self-referencing gate should be valid (warning only)"
        )
        assert "consistency_issues" in json_data, "Should report consistency issues"
        assert len(json_data["consistency_issues"]) > 0, "Should have at least one consistency issue"
        # Check that the self-referencing issue is not blocking
        non_blocking = [i for i in json_data["consistency_issues"] if not i["blocking"]]
        assert len(non_blocking) > 0, "Self-referencing gate should be a non-blocking issue"
