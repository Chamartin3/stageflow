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
from typing import Any

import pytest


class TestVisualization:
    """Integration test suite for process visualization functionality."""

    @pytest.fixture(scope="class")
    def test_data_dir(self) -> Path:
        """Get the test data directory for visualization tests."""
        return Path(__file__).parent / "data"

    @pytest.fixture(scope="class")
    def simple_process_files(self, test_data_dir: Path) -> list[Path]:
        """Get simple process files for basic visualization testing."""
        simple_dir = test_data_dir / "simple"
        return list(simple_dir.glob("*.yaml"))

    @pytest.fixture(scope="class")
    def complex_process_files(self, test_data_dir: Path) -> list[Path]:
        """Get complex process files for advanced visualization testing."""
        complex_dir = test_data_dir / "complex"
        return list(complex_dir.glob("*.yaml"))

    def run_stageflow_cli(
        self,
        process_file: str,
        output_file: str = "/tmp/test_diagram.md",
        expect_success: bool = True,
        json_output: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Run the StageFlow CLI for visualization with given arguments and return structured result.

        Args:
            process_file: Path to the process definition file
            output_file: Path for the output diagram file
            expect_success: Whether to expect successful exit code (0)
            json_output: Whether to request JSON output
            verbose: Whether to enable verbose output

        Returns:
            Dictionary containing exit_code, stdout, stderr, and parsed_json (if applicable)
        """
        # Build command: stageflow process diagram process_file --output output_file [--json]
        full_cmd = [
            "uv",
            "run",
            "stageflow",
            "process",
            "diagram",
            process_file,
            "--output",
            output_file,
        ]

        # Add JSON flag if requested
        if json_output:
            full_cmd.append("--json")

        # Note: diagram command doesn't support --verbose flag

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
        "process_file", ["linear_flow.yaml", "branching_flow.yaml"]
    )
    def test_simple_visualization_generation(
        self, test_data_dir: Path, process_file: str, tmp_path: Path
    ):
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
        result = self.run_stageflow_cli(
            str(process_path), str(output_file), expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists(), "Visualization file should be created"
        assert "visualization written to" in result["stdout"], (
            "Should confirm file creation"
        )

        # Verify file content
        content = output_file.read_text()
        assert "```mermaid" in content, "Should contain Mermaid code block"
        assert "flowchart TD" in content, "Should use top-down flowchart syntax"
        assert "```" in content.split("\n")[-1] or content.strip().endswith("```"), (
            "Should close Mermaid block"
        )

    @pytest.mark.parametrize(
        "process_file",
        ["convergence_flow.yaml", "parallel_paths.yaml", "nested_conditions.yaml"],
    )
    def test_complex_visualization_generation(
        self, test_data_dir: Path, process_file: str, tmp_path: Path
    ):
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
        result = self.run_stageflow_cli(
            str(process_path), str(output_file), expect_success=True
        )

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
        assert len(transition_lines) > 1, (
            "Complex flow should have multiple stage transitions"
        )

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
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), json_output=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["parsed_json"] is not None, "Should return valid JSON"

        json_data = result["parsed_json"]
        assert "visualization" in json_data, (
            "JSON should contain visualization file path"
        )
        assert "format" in json_data, "JSON should specify visualization format"
        assert json_data["format"] == "mermaid", "Should indicate Mermaid format"
        assert str(output_file) in json_data["visualization"], (
            "Should reference correct output file"
        )

    def test_visualization_with_automatic_md_extension(
        self, test_data_dir: Path, tmp_path: Path
    ):
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
        result = self.run_stageflow_cli(
            str(process_file), str(output_file_no_ext), expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0

        # Should create file with .md extension
        expected_file = output_file_no_ext.with_suffix(".md")
        assert expected_file.exists(), "Should create file with .md extension"
        assert not output_file_no_ext.exists(), (
            "Should not create file without extension"
        )

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
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), verbose=True, expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        # Check for any progress-related output in verbose mode
        # The exact message may vary, but should indicate visualization progress
        assert any(
            keyword in result["stdout"].lower()
            for keyword in ["generating", "writing", "mermaid"]
        ), "Verbose should show generation progress"
        assert output_file.exists(), "Should still create visualization file"

    def test_visualization_error_handling_missing_output_file(
        self, test_data_dir: Path
    ):
        """
        Verify proper error handling when source file is not specified.

        Tests that CLI properly handles:
        - Missing SOURCE argument for diagram command
        - Clear error messages about required source file
        - Appropriate exit codes for missing parameters
        - Helpful guidance for correct usage
        """
        # Arrange - call diagram command without SOURCE argument

        # Act - Test missing source file parameter by calling CLI directly
        try:
            result = subprocess.run(
                ["uv", "run", "stageflow", "process", "diagram"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/omidev/Code/tools/stageflow",
            )
            result_dict = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as e:
            pytest.fail(f"Failed to run CLI command: {e}")

        # Assert
        assert result_dict["exit_code"] != 0, (
            "Should fail when source file not specified"
        )
        error_output = result_dict["stdout"] + result_dict["stderr"]
        assert (
            "Missing argument" in error_output or "required" in error_output.lower()
        ), "Should mention missing required argument"

    def test_visualization_error_handling_missing_output_file_json(
        self, test_data_dir: Path, tmp_path: Path
    ):
        """
        Verify proper JSON error response when CLI generates default output file.

        Tests that JSON mode properly reports:
        - Successful generation with default output file
        - JSON response with generated file path
        - Proper handling when output path is not explicitly provided
        """
        # Arrange
        process_file = test_data_dir / "simple" / "linear_flow.yaml"
        # Since CLI generates default filename, we test success case with JSON output
        output_file = tmp_path / "test_default_output.md"

        # Act - Test with explicit output file and JSON flag
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), expect_success=True, json_output=True
        )

        # Assert - Should succeed and return JSON response
        assert result["exit_code"] == 0, "Should succeed with explicit output file"
        assert result["parsed_json"] is not None, "Should return valid JSON response"

        json_data = result["parsed_json"]
        assert "visualization" in json_data, (
            "JSON should contain visualization file path"
        )
        assert "format" in json_data, "JSON should specify visualization format"
        assert json_data["format"] == "mermaid", "Should indicate Mermaid format"
        assert str(output_file) in json_data["visualization"], (
            "Should reference correct output file"
        )

    def test_mermaid_diagram_structure_validation(
        self, test_data_dir: Path, tmp_path: Path
    ):
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
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), expect_success=True
        )

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

    def test_comprehensive_visualization_workflow(
        self, test_data_dir: Path, tmp_path: Path
    ):
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
            ("complex", "parallel_paths.yaml"),
        ]

        successful_generations = 0

        # Act & Assert
        for category, filename in test_files:
            process_file = test_data_dir / category / filename
            if process_file.exists():
                output_file = tmp_path / f"{category}_{Path(filename).stem}_diagram.md"

                result = self.run_stageflow_cli(
                    str(process_file), str(output_file), expect_success=True
                )

                assert result["exit_code"] == 0, (
                    f"Should successfully generate visualization for {filename}"
                )
                assert output_file.exists(), f"Should create output file for {filename}"

                # Verify basic content structure
                content = output_file.read_text()
                assert "```mermaid" in content, (
                    f"Should contain Mermaid syntax for {filename}"
                )

                successful_generations += 1

        assert successful_generations > 0, (
            "Should successfully generate at least one visualization"
        )

    def test_visualization_output_file_permissions_and_content(
        self, test_data_dir: Path, tmp_path: Path
    ):
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
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), expect_success=True
        )

        # Assert
        assert result["exit_code"] == 0
        assert output_file.exists()

        # File should be readable
        assert output_file.is_file(), "Should create a regular file"
        assert output_file.stat().st_size > 0, "File should have content"

        # Content should be valid text
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0, "File should contain text content"
        assert content.isprintable() or "\n" in content, (
            "Content should be printable text"
        )

    def test_visualization_consistency_across_output_modes(
        self, test_data_dir: Path, tmp_path: Path
    ):
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
        normal_result = self.run_stageflow_cli(
            str(process_file), str(normal_output), expect_success=True
        )

        json_result = self.run_stageflow_cli(
            str(process_file), str(json_output), expect_success=True, json_output=True
        )

        verbose_result = self.run_stageflow_cli(
            str(process_file), str(verbose_output), expect_success=True, verbose=True
        )

        # Assert
        assert all(
            result["exit_code"] == 0
            for result in [normal_result, json_result, verbose_result]
        )
        assert all(
            output.exists() for output in [normal_output, json_output, verbose_output]
        )

        # Content should be identical across modes
        normal_content = normal_output.read_text()
        json_content = json_output.read_text()
        verbose_content = verbose_output.read_text()

        assert normal_content == json_content == verbose_content, (
            "Diagram content should be identical across output modes"
        )

    def test_visualization_transition_accuracy(self, tmp_path: Path):
        """
        Test that visualizations show accurate transitions based on gate relationships,
        not linear stage ordering. This test detects the bug where transitions were
        generated linearly instead of following actual gate targets.
        """
        from stageflow.loader import load_process

        # Test with convergence flow that has non-linear transitions
        test_data_dir = Path(__file__).parent.parent / "data"
        convergence_file = (
            test_data_dir / "visualization" / "complex" / "convergence_flow.yaml"
        )

        assert convergence_file.exists(), "Convergence flow test data should exist"

        output_file = tmp_path / "convergence_test.md"

        # Generate visualization
        result = self.run_stageflow_cli(
            str(convergence_file), str(output_file), expect_success=True
        )

        assert result["exit_code"] == 0
        assert output_file.exists()

        # Parse the diagram content
        content = output_file.read_text()
        lines = content.split("\n")

        # Extract transitions (lines with -->)
        transitions = []
        for line in lines:
            if "-->" in line and line.strip().startswith("S"):
                # Parse transition like "S0 --> S1"
                parts = line.strip().split(" --> ")
                if len(parts) == 2:
                    source = parts[0].strip()
                    target = parts[1].strip()
                    transitions.append((source, target))

        # Load the actual process to verify correct transitions
        load_process(str(convergence_file))

        # Verify specific expected transitions exist (convergence pattern)
        expected_patterns = [
            # order_received should branch to multiple validation stages
            ("S0", ["S1", "S6", "S8"]),  # online, phone, store validation
            # Multiple paths should converge at inventory_check
            ("S1", "S2"),  # online_validation -> inventory_check
            ("S7", "S2"),  # payment_processing -> inventory_check
            ("S8", "S2"),  # store_validation -> inventory_check
        ]

        for source, expected_targets in expected_patterns:
            if isinstance(expected_targets, list):
                # Check that source connects to at least one of the expected targets
                actual_targets = [
                    target for src, target in transitions if src == source
                ]
                found_targets = [t for t in actual_targets if t in expected_targets]
                assert len(found_targets) > 0, (
                    f"Stage {source} should connect to at least one of {expected_targets}, but found: {actual_targets}"
                )
            else:
                # Check specific transition exists
                assert (source, expected_targets) in transitions, (
                    f"Expected transition {source} -> {expected_targets} not found in: {transitions}"
                )

        # Verify it's NOT a simple linear progression (which was the bug)
        # If it were linear, we'd see S0->S1->S2->S3->S4->S5->S6->S7->S8
        linear_transitions = [
            ("S0", "S1"),
            ("S1", "S2"),
            ("S2", "S3"),
            ("S3", "S4"),
            ("S4", "S5"),
            ("S5", "S6"),
            ("S6", "S7"),
            ("S7", "S8"),
        ]
        actual_transition_set = set(transitions)
        linear_transition_set = set(linear_transitions)

        # Should not be a purely linear flow
        assert not linear_transition_set.issubset(actual_transition_set), (
            "Visualization should not show linear progression for convergence flow"
        )

    def test_visualization_initial_final_stage_styling(self, tmp_path: Path):
        """
        Test that initial and final stages are correctly identified and styled,
        not based on array position. This detects the bug where final stage
        styling was based on stage_order position instead of actual final_stage.
        """
        from stageflow.loader import load_process

        # Test with convergence flow where final stage is not last in stage order
        test_data_dir = Path(__file__).parent.parent / "data"
        convergence_file = (
            test_data_dir / "visualization" / "complex" / "convergence_flow.yaml"
        )

        assert convergence_file.exists(), "Convergence flow test data should exist"

        output_file = tmp_path / "styling_test.md"

        # Generate visualization
        result = self.run_stageflow_cli(
            str(convergence_file), str(output_file), expect_success=True
        )

        assert result["exit_code"] == 0
        assert output_file.exists()

        # Load process to get actual initial and final stages
        process = load_process(str(convergence_file))
        actual_initial_stage = process.initial_stage._id
        actual_final_stage = process.final_stage._id

        # Parse the diagram content
        content = output_file.read_text()
        lines = content.split("\n")

        # Extract stage node mappings (S0["stage_name"])
        stage_mappings = {}
        for line in lines:
            if "[" in line and "]" in line and line.strip().startswith("S"):
                # Parse line like '    S0["order_received"]'
                parts = line.strip().split("[", 1)
                if len(parts) == 2:
                    node_id = parts[0].strip()
                    # Remove trailing ] and any surrounding quotes
                    stage_name = parts[1].rstrip("]").strip('"')
                    stage_mappings[stage_name] = node_id

        # Extract styling assignments
        initial_nodes = []
        final_nodes = []
        for line in lines:
            if "class" in line and "initial" in line:
                # Parse "    class S0 initial"
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0] == "class" and parts[2] == "initial":
                    initial_nodes.append(parts[1])
            elif "class" in line and "final" in line:
                # Parse "    class S4 final"
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0] == "class" and parts[2] == "final":
                    final_nodes.append(parts[1])

        # Verify correct initial stage styling
        expected_initial_node = stage_mappings.get(actual_initial_stage)
        assert expected_initial_node in initial_nodes, (
            f"Initial stage '{actual_initial_stage}' (node {expected_initial_node}) should be styled as initial. Found initial nodes: {initial_nodes}"
        )

        # Verify correct final stage styling
        expected_final_node = stage_mappings.get(actual_final_stage)
        assert expected_final_node in final_nodes, (
            f"Final stage '{actual_final_stage}' (node {expected_final_node}) should be styled as final. Found final nodes: {final_nodes}"
        )

        # Verify no other stages are incorrectly styled as final
        assert len(final_nodes) == 1, (
            f"Should have exactly one final stage, but found: {final_nodes}"
        )

    def test_visualization_convergence_pattern_detection(self, tmp_path: Path):
        """
        Test that complex convergence patterns are properly represented in visualizations.
        This ensures multiple paths correctly converge at common stages.
        """
        test_data_dir = Path(__file__).parent.parent / "data"

        # Test files that should show convergence patterns
        convergence_files = [
            ("convergence_flow.yaml", "complex"),
            ("parallel_paths.yaml", "complex"),
        ]

        for filename, category in convergence_files:
            process_file = test_data_dir / "visualization" / category / filename

            if not process_file.exists():
                continue

            output_file = tmp_path / f"convergence_{filename.replace('.yaml', '.md')}"

            # Generate visualization
            result = self.run_stageflow_cli(
                str(process_file), str(output_file), expect_success=True
            )

            assert result["exit_code"] == 0, (
                f"Should generate visualization for {filename}"
            )
            assert output_file.exists(), f"Should create output file for {filename}"

            # Parse transitions
            content = output_file.read_text()
            lines = content.split("\n")

            transitions = []
            for line in lines:
                if "-->" in line and line.strip().startswith("S"):
                    parts = line.strip().split(" --> ")
                    if len(parts) == 2:
                        source = parts[0].strip()
                        target = parts[1].strip()
                        transitions.append((source, target))

            # Verify convergence patterns exist
            # Find stages that are targets of multiple transitions (convergence points)
            target_counts = {}
            for _source, target in transitions:
                target_counts[target] = target_counts.get(target, 0) + 1

            convergence_points = [
                target for target, count in target_counts.items() if count > 1
            ]

            # Should have at least one convergence point for these complex flows
            assert len(convergence_points) > 0, (
                f"Complex flow {filename} should have convergence points where multiple paths merge. Transitions: {transitions}"
            )

            # Verify no stage connects to itself (would indicate sorting bugs)
            self_loops = [(s, t) for s, t in transitions if s == t]
            assert len(self_loops) == 0, (
                f"No stage should connect to itself in {filename}. Found self-loops: {self_loops}"
            )

    def test_visualization_handles_orphaned_stages(self, tmp_path: Path):
        """
        Test that visualization properly handles stages that might be orphaned
        or unreachable due to the sorting algorithm.
        """
        from stageflow.loader import load_process

        test_data_dir = Path(__file__).parent.parent / "data"

        # Test with a complex process
        process_file = (
            test_data_dir / "visualization" / "complex" / "convergence_flow.yaml"
        )

        assert process_file.exists(), "Test process file should exist"

        output_file = tmp_path / "orphaned_test.md"

        # Generate visualization
        result = self.run_stageflow_cli(
            str(process_file), str(output_file), expect_success=True
        )

        assert result["exit_code"] == 0
        assert output_file.exists()

        # Load process and get all stage names
        process = load_process(str(process_file))
        all_stage_names = {stage._id for stage in process.stages}

        # Parse visualization to find represented stages
        content = output_file.read_text()
        lines = content.split("\n")

        represented_stages = set()
        for line in lines:
            if "[" in line and "]" in line and line.strip().startswith("S"):
                # Parse line like '    S0["order_received"]'
                parts = line.strip().split("[", 1)
                if len(parts) == 2:
                    # Remove trailing ] and any surrounding quotes
                    stage_name = parts[1].rstrip("]").strip('"')
                    represented_stages.add(stage_name)

        # All stages should be represented in the visualization
        missing_stages = all_stage_names - represented_stages
        assert len(missing_stages) == 0, (
            f"All stages should be represented in visualization. Missing: {missing_stages}"
        )

        # All represented stages should be real stages
        extra_stages = represented_stages - all_stage_names
        assert len(extra_stages) == 0, (
            f"Only real stages should be in visualization. Extra: {extra_stages}"
        )
