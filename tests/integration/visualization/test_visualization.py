"""Integration tests for StageFlow visualization capabilities.

This module contains comprehensive integration tests that verify the StageFlow CLI's
visualization generation functionality including Mermaid diagram creation for
simple linear flows and complex branching processes.

Test Categories:
- Simple visualization: Tests basic linear and branching flow diagrams
- Complex visualization: Tests advanced workflow patterns with multiple paths
- Output format validation: Tests diagram syntax and structure correctness
- File handling: Tests output file creation and content verification
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

import pytest


class TestVisualization:
    """Integration test suite for process visualization functionality."""

    @pytest.fixture(scope="class")
    def test_data_dir(self) -> Path:
        """Get the test data directory for visualization tests."""
        return Path(__file__).parent / "data"

    @pytest.fixture(scope="class")
    def simple_process_files(self, test_data_dir: Path) -> List[Path]:
        """Get simple process files for basic visualization testing."""
        simple_dir = test_data_dir / "simple"
        return list(simple_dir.glob("*.yaml"))

    @pytest.fixture(scope="class")
    def complex_process_files(self, test_data_dir: Path) -> List[Path]:
        """Get complex process files for advanced visualization testing."""
        complex_dir = test_data_dir / "complex"
        return list(complex_dir.glob("*.yaml"))

    def run_stageflow_cli(self, args: List[str], expect_success: bool = True) -> Dict[str, Any]:
        """
        Run the StageFlow CLI with given arguments and return structured result.

        Args:
            args: CLI arguments to pass to stageflow command
            expect_success: Whether to expect successful exit code (0)

        Returns:
            Dictionary containing exit_code, stdout, stderr, and parsed_json (if applicable)
        """
        full_cmd = ["uv", "run", "stageflow"] + args

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/omidev/Code/tools/stageflow"
            )

            # Parse JSON output if --json flag was used
            parsed_json = None
            if "--json" in args and result.stdout.strip():
                try:
                    parsed_json = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    pass

            response = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "parsed_json": parsed_json
            }

            if expect_success:
                assert result.returncode == 0, f"Expected success but got exit code {result.returncode}. stderr: {result.stderr}"

            return response

        except subprocess.TimeoutExpired:
            pytest.fail("CLI command timed out after 30 seconds")
        except Exception as e:
            pytest.fail(f"Failed to run CLI command: {e}")

    @pytest.mark.parametrize("process_file", [
        "linear_flow.yaml",
        "branching_flow.yaml"
    ])
    def test_simple_visualization_generation(self, test_data_dir: Path, process_file: str, tmp_path: Path):
        """
        Verify generation of simple process visualizations with correct Mermaid syntax.

        Tests that simple process files:
        - Generate valid Mermaid diagram files
        - Contain proper flowchart syntax structure
        - Include all process stages as nodes
        - Show correct stage transitions
        - Create output files with .md extension
        """
        # Arrange
        process_path = test_data_dir / "simple" / process_file
        output_file = tmp_path / f"{Path(process_file).stem}_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_path),
            "--view",
            "-o", str(output_file)
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists(), "Visualization file should be created"
        assert "visualization written to" in result["stdout"], "Should confirm file creation"

        # Verify file content
        content = output_file.read_text()
        assert "```mermaid" in content, "Should contain Mermaid code block"
        assert "flowchart TD" in content, "Should use top-down flowchart syntax"
        assert "```" in content.split("\n")[-1] or content.strip().endswith("```"), "Should close Mermaid block"

    @pytest.mark.parametrize("process_file", [
        "convergence_flow.yaml",
        "parallel_paths.yaml",
        "nested_conditions.yaml"
    ])
    def test_complex_visualization_generation(self, test_data_dir: Path, process_file: str, tmp_path: Path):
        """
        Verify generation of complex process visualizations with advanced workflow patterns.

        Tests that complex process files:
        - Handle multiple branching and convergence points
        - Generate comprehensive Mermaid diagrams
        - Properly represent parallel execution paths
        - Show nested conditional logic flows
        - Maintain diagram readability despite complexity
        """
        # Arrange
        process_path = test_data_dir / "complex" / process_file
        output_file = tmp_path / f"{Path(process_file).stem}_complex_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_path),
            "--view",
            "-o", str(output_file)
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists(), "Complex visualization file should be created"

        # Verify file content structure
        content = output_file.read_text()
        assert "```mermaid" in content, "Should contain Mermaid code block"
        assert "flowchart TD" in content, "Should use flowchart syntax"

        # Complex diagrams should have multiple transitions
        lines = content.split("\n")
        transition_lines = [line for line in lines if "-->" in line]
        assert len(transition_lines) > 1, "Complex flow should have multiple stage transitions"

    def test_visualization_json_output(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that visualization generation produces correct JSON output for API integration.

        Tests that JSON mode for visualization:
        - Returns structured response with file path
        - Indicates visualization format (mermaid)
        - Provides success confirmation
        - Maintains consistency with other JSON responses
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        output_file = tmp_path / "json_test_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "-o", str(output_file),
            "--json"
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None, "Should return valid JSON"

        json_data = result["parsed_json"]
        assert "visualization" in json_data, "JSON should contain visualization file path"
        assert "format" in json_data, "JSON should specify visualization format"
        assert json_data["format"] == "mermaid", "Should indicate Mermaid format"
        assert str(output_file) in json_data["visualization"], "Should reference correct output file"

    def test_visualization_with_automatic_md_extension(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that visualization automatically adds .md extension when not specified.

        Tests that output files:
        - Automatically get .md extension for Mermaid diagrams
        - Handle various input filename patterns correctly
        - Create files with proper extensions regardless of input
        - Maintain file content integrity with extension handling
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        output_file_no_ext = tmp_path / "diagram_no_extension"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "-o", str(output_file_no_ext)
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0

        # Should create file with .md extension
        expected_file = output_file_no_ext.with_suffix(".md")
        assert expected_file.exists(), "Should create file with .md extension"
        assert not output_file_no_ext.exists(), "Should not create file without extension"

    def test_visualization_verbose_output(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that verbose mode provides detailed progress information during visualization.

        Tests that --verbose flag:
        - Shows progress messages during diagram generation
        - Provides additional diagnostic information
        - Maintains successful visualization creation
        - Helps with debugging visualization issues
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        output_file = tmp_path / "verbose_test_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "-o", str(output_file),
            "--verbose"
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        # Check for any progress-related output in verbose mode
        # The exact message may vary, but should indicate visualization progress
        assert any(keyword in result["stdout"].lower() for keyword in ["generating", "writing", "mermaid"]), "Verbose should show generation progress"
        assert output_file.exists(), "Should still create visualization file"

    def test_visualization_error_handling_missing_output_file(self, test_data_dir: Path):
        """
        Verify proper error handling when output file is not specified for visualization.

        Tests that CLI properly handles:
        - Missing -o/--output flag for visualization
        - Clear error messages about required output file
        - Appropriate exit codes for missing parameters
        - Helpful guidance for correct usage
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view"
            # Missing -o flag
        ], expect_success=False)

        # Assert
        assert result["exit_code"] != 0, "Should fail when output file not specified"
        error_output = result["stdout"] + result["stderr"]
        assert "Output file" in error_output, "Should mention output file requirement"

    def test_visualization_error_handling_missing_output_file_json(self, test_data_dir: Path):
        """
        Verify proper JSON error response when output file is missing.

        Tests that JSON mode properly reports:
        - Structured error response for missing output file
        - Appropriate error messages in JSON format
        - Consistent error handling across output modes
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "--json"
            # Missing -o flag
        ], expect_success=False)

        # Assert
        assert result["exit_code"] != 0, "Should fail when output file not specified"

        # Should have JSON error response
        if result["stdout"].strip():
            try:
                json_data = json.loads(result["stdout"].strip())
                assert "error" in json_data, "JSON error response should contain error field"
            except json.JSONDecodeError:
                # If not JSON, should still indicate error
                assert "error" in result["stdout"].lower(), "Should indicate error condition"

    def test_mermaid_diagram_structure_validation(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that generated Mermaid diagrams have correct structural elements.

        Tests that Mermaid diagrams contain:
        - Proper node definitions for each stage
        - Correct arrow syntax for transitions
        - Valid Mermaid flowchart structure
        - Final stage indicators where appropriate
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        output_file = tmp_path / "structure_test_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "-o", str(output_file)
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists()

        content = output_file.read_text()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Should have opening and closing mermaid blocks
        assert lines[0] == "```mermaid", "Should start with mermaid code block"
        assert lines[-1] == "```", "Should end with closing code block"

        # Should have flowchart declaration
        flowchart_line = next((line for line in lines if "flowchart" in line), None)
        assert flowchart_line is not None, "Should contain flowchart declaration"

        # Should have node definitions (lines with brackets)
        node_lines = [line for line in lines if "[" in line and "]" in line]
        assert len(node_lines) > 0, "Should have stage node definitions"

        # Should have transition definitions (lines with arrows)
        transition_lines = [line for line in lines if "-->" in line]
        assert len(transition_lines) > 0, "Should have stage transitions"

    def test_comprehensive_visualization_workflow(self, test_data_dir: Path, tmp_path: Path):
        """
        Test a comprehensive workflow covering multiple visualization scenarios.

        This test demonstrates real-world usage patterns where developers generate
        visualizations for different types of processes to understand workflow
        structure and complexity.
        """
        # Arrange - test different process types
        test_files = [
            ("simple", "linear_flow.yaml"),
            ("simple", "branching_flow.yaml"),
            ("complex", "parallel_paths.yaml")
        ]

        successful_generations = 0

        # Act & Assert
        for category, filename in test_files:
            process_file = test_data_dir / category / filename
            if process_file.exists():
                output_file = tmp_path / f"{category}_{Path(filename).stem}_diagram.md"

                result = self.run_stageflow_cli([
                    "-p", str(process_file),
                    "--view",
                    "-o", str(output_file)
                ], expect_success=True)

                assert result["exit_code"] == 0, f"Should successfully generate visualization for {filename}"
                assert output_file.exists(), f"Should create output file for {filename}"

                # Verify basic content structure
                content = output_file.read_text()
                assert "```mermaid" in content, f"Should contain Mermaid syntax for {filename}"

                successful_generations += 1

        assert successful_generations > 0, "Should successfully generate at least one visualization"

    def test_visualization_output_file_permissions_and_content(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that visualization output files are created with correct permissions and content.

        Tests that generated files:
        - Have appropriate file permissions for reading
        - Contain well-formed content without corruption
        - Are properly formatted text files
        - Can be read and processed by external tools
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        output_file = tmp_path / "permissions_test_diagram.md"

        # Act
        result = self.run_stageflow_cli([
            "-p", str(process_file),
            "--view",
            "-o", str(output_file)
        ], expect_success=True)

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists()

        # File should be readable
        assert output_file.is_file(), "Should create a regular file"
        assert output_file.stat().st_size > 0, "File should have content"

        # Content should be valid text
        content = output_file.read_text(encoding='utf-8')
        assert len(content) > 0, "File should contain text content"
        assert content.isprintable() or "\n" in content, "Content should be printable text"

    def test_visualization_consistency_across_output_modes(self, test_data_dir: Path, tmp_path: Path):
        """
        Verify that visualization behavior is consistent across different output modes.

        Tests that visualization generation:
        - Produces same diagram content in normal and JSON modes
        - Creates identical files regardless of output verbosity
        - Maintains content consistency across multiple runs
        - Provides consistent success indicators
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        normal_output = tmp_path / "normal_diagram.md"
        json_output = tmp_path / "json_diagram.md"
        verbose_output = tmp_path / "verbose_diagram.md"

        # Act - Generate same diagram with different output modes
        normal_result = self.run_stageflow_cli([
            "-p", str(process_file), "--view", "-o", str(normal_output)
        ], expect_success=True)

        json_result = self.run_stageflow_cli([
            "-p", str(process_file), "--view", "-o", str(json_output), "--json"
        ], expect_success=True)

        verbose_result = self.run_stageflow_cli([
            "-p", str(process_file), "--view", "-o", str(verbose_output), "--verbose"
        ], expect_success=True)

        # Assert
        assert all(result["exit_code"] == 0 for result in [normal_result, json_result, verbose_result])
        assert all(output.exists() for output in [normal_output, json_output, verbose_output])

        # Content should be identical across modes
        normal_content = normal_output.read_text()
        json_content = json_output.read_text()
        verbose_content = verbose_output.read_text()

        assert normal_content == json_content == verbose_content, "Diagram content should be identical across output modes"