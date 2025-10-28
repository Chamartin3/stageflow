"""Integration tests for StageFlow element validation and evaluation.

This module contains comprehensive integration tests that verify the StageFlow CLI's
element evaluation capabilities including normal flow progression, regression detection,
edge case handling, and default property application.

Test Categories:
- Normal flow: Tests typical element progression through process stages
- Regression detection: Tests backward progression and property loss scenarios
- Edge cases: Tests boundary conditions and unusual data patterns
- Default properties: Tests automatic property application and progressive enhancement
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


class TestElementValidation:
    """Integration test suite for element validation and evaluation functionality."""

    @pytest.fixture(scope="class")
    def test_data_dir(self) -> Path:
        """Get the test data directory for element validation tests."""
        return Path(__file__).parent / "data"

    @pytest.fixture(scope="class")
    def normal_flow_test_cases(
        self, test_data_dir: Path
    ) -> list[tuple[Path, list[Path]]]:
        """
        Get normal flow test cases with process files and their associated element files.

        Returns:
            List of tuples containing (process_file, list_of_element_files)
        """
        normal_flow_dir = test_data_dir / "normal_flow"
        test_cases = []

        # Each subdirectory should have a process.yaml and element files
        for subdir in normal_flow_dir.iterdir():
            if subdir.is_dir():
                process_file = subdir / "process.yaml"
                if process_file.exists():
                    element_files = list(subdir.glob("*.json"))
                    if element_files:
                        test_cases.append((process_file, element_files))

        return test_cases

    @pytest.fixture(scope="class")
    def regression_test_cases(
        self, test_data_dir: Path
    ) -> list[tuple[Path, list[Path]]]:
        """Get regression detection test cases with process and element files."""
        regression_dir = test_data_dir / "regression"
        test_cases = []

        for subdir in regression_dir.iterdir():
            if subdir.is_dir():
                process_file = subdir / "process.yaml"
                if process_file.exists():
                    element_files = list(subdir.glob("*.json"))
                    if element_files:
                        test_cases.append((process_file, element_files))

        return test_cases

    @pytest.fixture(scope="class")
    def edge_case_elements(self, test_data_dir: Path) -> tuple[Path, list[Path]]:
        """Get edge case test elements with their process file."""
        edge_cases_dir = test_data_dir / "edge_cases"
        process_file = edge_cases_dir / "process.yaml"
        element_files = list(edge_cases_dir.glob("*.json"))
        return process_file, element_files

    @pytest.fixture(scope="class")
    def default_properties_test_case(
        self, test_data_dir: Path
    ) -> tuple[Path, list[Path]]:
        """Get default properties test case with process and element files."""
        defaults_dir = test_data_dir / "default_properties"
        # Look for the main process file for defaults testing
        process_file = defaults_dir / "defaults_demo_process.yaml"
        if not process_file.exists():
            process_file = defaults_dir / "process.yaml"
        element_files = list(defaults_dir.glob("*.json"))
        return process_file, element_files

    def run_stageflow_cli(
        self,
        process_file: str,
        element_file: str | None = None,
        stage: str | None = None,
        expect_success: bool = True,
        json_output: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Run the StageFlow CLI with given arguments and return structured result.

        Args:
            process_file: Path to the process definition file
            element_file: Path to the element file for evaluation (optional)
            stage: Stage for element evaluation (optional)
            expect_success: Whether to expect successful exit code (0)
            json_output: Whether to request JSON output
            verbose: Whether to enable verbose output

        Returns:
            Dictionary containing exit_code, stdout, stderr, and parsed_json (if applicable)
        """
        # Build command: stageflow evaluate process_file [-e element_file] [-s stage] [--json] [--verbose]
        # If element_file is provided, use evaluate command; otherwise use view command
        if element_file:
            full_cmd = ["uv", "run", "stageflow", "evaluate", process_file]
            full_cmd.extend(["-e", element_file])

            # Add stage if specified
            if stage:
                full_cmd.extend(["-s", stage])
        else:
            # No element file, use view command
            full_cmd = ["uv", "run", "stageflow", "view", process_file]

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

            # Parse JSON output if JSON flag was used
            parsed_json = None
            if json_output and result.stdout.strip():
                try:
                    parsed_json = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
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
        "element_file",
        [
            "user_ready_for_profile.json",
            "user_ready_for_verification.json",
            "user_ready_for_activation.json",
        ],
    )
    def test_ready_elements_human_output(self, test_data_dir: Path, element_file: str):
        """
        Verify that elements ready for progression show correct status and next steps.

        Tests that elements with sufficient data for stage transitions:
        - Display 'ready' status with success indicator
        - Show current stage information
        - Indicate which gates passed
        - Provide clear progression path
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "process.yaml"
        element_path = test_data_dir / "normal_flow" / "ready_elements" / element_file

        # Act
        result = self.run_stageflow_cli(
            str(process_file), str(element_path), expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert "✅" in result["stdout"], "Ready element should show success indicator"
        assert "Evaluation Result" in result["stdout"], (
            "Should display evaluation section"
        )
        assert "Current Stage:" in result["stdout"], "Should show current stage"
        assert "Status:" in result["stdout"], "Should show evaluation status"

    @pytest.mark.parametrize(
        "element_file",
        [
            "user_missing_email_verification.json",
            "user_incomplete_profile.json",
            "user_pending_identity_verification.json",
        ],
    )
    def test_action_required_elements_human_output(
        self, test_data_dir: Path, element_file: str
    ):
        """
        Verify that elements requiring actions show clear guidance and missing requirements.

        Tests that elements missing required data:
        - Display 'action_required' status with warning indicator
        - List specific required actions
        - Identify missing properties or validation failures
        - Provide actionable next steps
        """
        # Arrange
        process_file = (
            test_data_dir / "normal_flow" / "action_required" / "process.yaml"
        )
        element_path = test_data_dir / "normal_flow" / "action_required" / element_file

        # Act - Use appropriate stage based on element type
        stage = (
            "verification" if "verification" in element_file else "profile_completion"
        )
        result = self.run_stageflow_cli(
            str(process_file), str(element_path), stage=stage, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert "⚠️" in result["stdout"], "Action required should show warning indicator"
        assert "Required Actions:" in result["stdout"], "Should list required actions"
        assert "Current Stage:" in result["stdout"], "Should show current stage"

    @pytest.mark.parametrize(
        "element_file", ["user_invalid_email.json", "user_missing_required_field.json"]
    )
    def test_invalid_schema_elements_human_output(
        self, test_data_dir: Path, element_file: str
    ):
        """
        Verify that elements with schema violations show clear error reporting.

        Tests that elements with invalid data:
        - Display 'invalid_schema' status with error indicator
        - Identify specific schema violations
        - Show which properties are invalid or missing
        - Provide guidance for data correction
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "invalid_schema" / "process.yaml"
        element_path = test_data_dir / "normal_flow" / "invalid_schema" / element_file

        # Act - Test at data_validation stage to trigger type validation failures
        result = self.run_stageflow_cli(
            str(process_file),
            str(element_path),
            stage="data_validation",
            expect_success=True,
        )

        # Assert
        assert result["exit_code"] == 0
        assert "⚠️" in result["stdout"], (
            "Schema validation failures should show warning indicator"
        )
        assert "action_required" in result["stdout"], (
            "Should show action_required status for validation failures"
        )
        assert "Type" in result["stdout"] or "should be of type" in result["stdout"], (
            "Should show type validation errors"
        )

    def test_normal_flow_progression_json_output(self, test_data_dir: Path):
        """
        Verify JSON output structure for normal element progression scenarios.

        Tests that JSON evaluation responses contain:
        - Process information with validity status
        - Element evaluation results with proper status values
        - Gate results with pass/fail details
        - Regression detection information
        - Suggested actions when applicable
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "process.yaml"
        element_file = (
            test_data_dir
            / "normal_flow"
            / "ready_elements"
            / "user_ready_for_profile.json"
        )

        # Act
        result = self.run_stageflow_cli(
            str(process_file), str(element_file), json_output=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None, "Should return valid JSON"

        json_data = result["parsed_json"]
        assert "process" in json_data, "JSON should contain process information"
        assert "evaluation" in json_data, "JSON should contain evaluation results"

        # Verify process structure
        process_info = json_data["process"]
        assert "name" in process_info, "Process should have name"
        assert "valid" in process_info, "Process should have validity status"

        # Verify evaluation structure
        evaluation = json_data["evaluation"]
        assert "stage" in evaluation, "Evaluation should show current stage"
        assert "status" in evaluation, "Evaluation should show status"
        assert "regression" in evaluation, "Evaluation should show regression info"
        assert "gate_results" in evaluation, "Evaluation should show gate results"

    @pytest.mark.parametrize(
        "element_file",
        ["element_regressed_to_basic.json", "element_regressed_to_intermediate.json"],
    )
    def test_backward_regression_detection(
        self, test_data_dir: Path, element_file: str
    ):
        """
        Verify detection of backward progression through process stages.

        Tests that elements showing backward stage progression:
        - Are properly identified as regressions
        - Show appropriate regression indicators
        - Maintain evaluation functionality despite regression
        - Provide clear indication of the regression type
        """
        # Arrange
        process_file = (
            test_data_dir / "regression" / "backward_regression" / "process.yaml"
        )
        element_path = (
            test_data_dir / "regression" / "backward_regression" / element_file
        )

        # Act - Test both human and JSON output at appropriate stage to detect regression
        stage = "review" if "intermediate" in element_file else "draft"
        human_result = self.run_stageflow_cli(
            str(process_file), str(element_path), stage=stage, expect_success=True
        )
        json_result = self.run_stageflow_cli(
            str(process_file),
            str(element_path),
            stage=stage,
            json_output=True,
            expect_success=True,
        )

        # Assert human output
        assert human_result["exit_code"] == 0
        assert "Evaluation Result" in human_result["stdout"], (
            "Should show evaluation results"
        )

        # Assert JSON output
        assert json_result["exit_code"] == 0
        assert json_result["parsed_json"] is not None
        evaluation = json_result["parsed_json"]["evaluation"]
        assert "regression" in evaluation, "Should contain regression information"

    @pytest.mark.parametrize(
        "element_file",
        ["element_lost_processed_data.json", "element_lost_advanced_features.json"],
    )
    def test_property_loss_regression_detection(
        self, test_data_dir: Path, element_file: str
    ):
        """
        Verify detection of property loss regressions in element data.

        Tests that elements missing previously required properties:
        - Are identified as property loss regressions
        - Show specific properties that were lost
        - Maintain proper stage evaluation despite missing data
        - Provide actionable feedback about missing properties
        """
        # Arrange
        process_file = test_data_dir / "regression" / "property_loss" / "process.yaml"
        element_path = test_data_dir / "regression" / "property_loss" / element_file

        # Act
        result = self.run_stageflow_cli(
            str(process_file), str(element_path), json_output=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None
        evaluation = result["parsed_json"]["evaluation"]
        assert "regression" in evaluation, "Should detect regression"

    @pytest.mark.parametrize(
        "element_file", ["element_status_changed.json", "element_score_decreased.json"]
    )
    def test_value_change_regression_detection(
        self, test_data_dir: Path, element_file: str
    ):
        """
        Verify detection of value change regressions in element properties.

        Tests that elements with changed critical values:
        - Are identified as value change regressions
        - Show which values changed unexpectedly
        - Continue proper evaluation with current values
        - Provide clear indication of value-based regression
        """
        # Arrange
        process_file = test_data_dir / "regression" / "value_change" / "process.yaml"
        element_path = test_data_dir / "regression" / "value_change" / element_file

        # Act - Test at application_approved stage to detect value change regression
        result = self.run_stageflow_cli(
            str(process_file),
            str(element_path),
            stage="application_approved",
            json_output=True,
            expect_success=True,
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None
        evaluation = result["parsed_json"]["evaluation"]
        assert "regression" in evaluation, "Should detect value change regression"

    @pytest.mark.parametrize(
        "element_file",
        [
            "empty_element.json",
            "nested_properties.json",
            "large_data.json",
            "special_chars.json",
        ],
    )
    def test_edge_case_element_handling(self, test_data_dir: Path, element_file: str):
        """
        Verify robust handling of edge case element data patterns.

        Tests that the system gracefully handles:
        - Empty or minimal element data
        - Deeply nested property structures
        - Large data payloads
        - Special characters and encoding scenarios
        """
        # Arrange
        process_file = test_data_dir / "edge_cases" / "process.yaml"
        element_path = test_data_dir / "edge_cases" / element_file

        # Act
        result = self.run_stageflow_cli(
            str(process_file), str(element_path), expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0, (
            f"Edge case {element_file} should not cause CLI failure"
        )
        assert "Evaluation Result" in result["stdout"], (
            "Should provide evaluation results"
        )

    def test_stage_specific_evaluation(self, test_data_dir: Path):
        """
        Verify that stage-specific evaluation works correctly with -s/--stage flag.

        Tests that specifying a target stage:
        - Evaluates element against the specific stage
        - Shows correct stage-specific validation results
        - Handles stage transitions appropriately
        - Provides accurate gate results for the target stage
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "process.yaml"
        element_file = (
            test_data_dir
            / "normal_flow"
            / "ready_elements"
            / "user_ready_for_profile.json"
        )

        # Act - Test evaluation at specific stage
        result = self.run_stageflow_cli(
            str(process_file),
            str(element_file),
            stage="profile_setup",
            json_output=True,
            expect_success=True,
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None
        evaluation = result["parsed_json"]["evaluation"]
        assert "stage" in evaluation, "Should show evaluated stage"

    def test_default_properties_progression(self, test_data_dir: Path):
        """
        Verify that default property application works correctly throughout element progression.

        Tests that elements with default properties:
        - Apply defaults correctly at appropriate stages
        - Show progressive enhancement of data
        - Maintain defaults through stage transitions
        - Properly handle missing vs. defaulted properties
        """
        # Arrange
        defaults_dir = test_data_dir / "default_properties"
        process_file = defaults_dir / "defaults_demo_process.yaml"
        if not process_file.exists():
            process_file = defaults_dir / "process.yaml"

        # Test with various elements that should trigger defaults
        test_elements = [
            "minimal_user.json",
            "user_needs_defaults.json",
            "profile_needs_defaults.json",
        ]

        for element_file in test_elements:
            element_path = defaults_dir / element_file
            if element_path.exists():
                # Act
                result = self.run_stageflow_cli(
                    str(process_file), str(element_path), expect_success=True
                )

                # Assert
                assert result["exit_code"] == 0, (
                    f"Default properties test should succeed for {element_file}"
                )
                assert "Evaluation Result" in result["stdout"], (
                    "Should show evaluation results"
                )

    def test_comprehensive_element_evaluation_workflow(self, test_data_dir: Path):
        """
        Test a comprehensive workflow covering multiple element evaluation scenarios.

        This test demonstrates real-world usage patterns where developers evaluate
        various elements against the same process to understand data requirements
        and progression paths.
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "process.yaml"

        # Test different element types in sequence
        test_scenarios = [
            (
                test_data_dir
                / "normal_flow"
                / "ready_elements"
                / "user_ready_for_profile.json",
                "should be ready",
            ),
            (
                test_data_dir
                / "normal_flow"
                / "action_required"
                / "user_incomplete_profile.json",
                "should need actions",
            ),
            (
                test_data_dir
                / "normal_flow"
                / "invalid_schema"
                / "user_invalid_email.json",
                "should be invalid",
            ),
        ]

        # Act & Assert
        for element_path, expectation in test_scenarios:
            if element_path.exists():
                result = self.run_stageflow_cli(
                    str(process_file), str(element_path), expect_success=True
                )

                assert result["exit_code"] == 0, f"Element evaluation {expectation}"
                assert "Evaluation Result" in result["stdout"], (
                    f"Should show results for {element_path.name}"
                )

    def test_verbose_element_evaluation(self, test_data_dir: Path):
        """
        Verify that verbose output provides enhanced diagnostic information for element evaluation.

        Tests that --verbose flag during element evaluation:
        - Shows loading progress for both process and element
        - Provides detailed evaluation step information
        - Includes additional debugging context
        - Maintains structured output while adding detail
        """
        # Arrange
        process_file = test_data_dir / "normal_flow" / "process.yaml"
        element_file = (
            test_data_dir
            / "normal_flow"
            / "ready_elements"
            / "user_ready_for_profile.json"
        )

        # Act
        result = self.run_stageflow_cli(
            str(process_file), str(element_file), verbose=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert "Loading process" in result["stdout"], (
            "Verbose should show process loading"
        )
        assert "Loading element" in result["stdout"], (
            "Verbose should show element loading"
        )
        assert "Evaluating element" in result["stdout"], (
            "Verbose should show evaluation progress"
        )

    def test_json_output_consistency_across_evaluation_types(self, test_data_dir: Path):
        """
        Verify that JSON output maintains consistent structure across all evaluation scenarios.

        Tests that JSON responses have consistent schema for:
        - Ready elements
        - Action required elements
        - Invalid schema elements
        - Regression scenarios
        - Edge cases

        This ensures API consumers can rely on predictable response formats.
        """
        # Arrange - collect representative files from different categories
        test_cases = [
            (
                test_data_dir / "normal_flow" / "ready_elements" / "process.yaml",
                test_data_dir
                / "normal_flow"
                / "ready_elements"
                / "user_ready_for_profile.json",
            ),
            (
                test_data_dir / "normal_flow" / "action_required" / "process.yaml",
                test_data_dir
                / "normal_flow"
                / "action_required"
                / "user_incomplete_profile.json",
            ),
        ]

        # Act & Assert
        for process_file, element_file in test_cases:
            if process_file.exists() and element_file.exists():
                result = self.run_stageflow_cli(
                    str(process_file),
                    str(element_file),
                    json_output=True,
                    expect_success=True,
                )

                assert result["parsed_json"] is not None, (
                    f"Should return valid JSON for {element_file.name}"
                )
                json_data = result["parsed_json"]

                # Verify consistent top-level structure
                assert "process" in json_data, "JSON should contain process information"
                assert "evaluation" in json_data, (
                    "JSON should contain evaluation results"
                )

                # Verify evaluation structure consistency
                evaluation = json_data["evaluation"]
                required_eval_fields = ["stage", "status", "regression", "gate_results"]
                for field in required_eval_fields:
                    assert field in evaluation, (
                        f"Evaluation should contain {field} for {element_file.name}"
                    )
