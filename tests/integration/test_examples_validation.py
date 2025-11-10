"""Integration tests for validating all example files in the examples/ directory.

This module ensures that all example files in the examples/ directory are valid
and can be loaded successfully by the StageFlow CLI. This catches issues like
invalid lock types or malformed YAML that users would encounter when using
the provided examples.
"""

import subprocess
from pathlib import Path

import pytest


class TestExamplesValidation:
    """Integration test suite that validates all example files."""

    @pytest.fixture(scope="class")
    def examples_dir(self) -> Path:
        """Get the examples directory."""
        return Path(__file__).parent.parent.parent / "examples"

    @pytest.fixture(scope="class")
    def valid_example_files(self, examples_dir: Path) -> list[Path]:
        """Get all valid example YAML files that should load successfully."""
        # Exclude intentionally invalid files
        invalid_patterns = [
            "invalid_structure",
            "consistency_errors",
            "malformed_syntax.yaml",
            "invalid_references.yaml",
            "missing_required.yaml",
            "invalid_locks.yaml",
            "outputs",
        ]

        all_yaml_files = list(examples_dir.glob("**/*.yaml"))
        valid_files = []

        for file_path in all_yaml_files:
            # Skip files in directories or with names indicating they should be invalid
            if any(pattern in str(file_path) for pattern in invalid_patterns):
                continue
            valid_files.append(file_path)

        return valid_files

    @pytest.fixture(scope="class")
    def invalid_example_files(self, examples_dir: Path) -> list[Path]:
        """Get example files that should fail validation (for testing error handling)."""
        # Only include structural errors, not consistency errors
        # Consistency errors require graceful loading mode which is not yet implemented
        invalid_dirs = ["invalid_structure"]

        invalid_files = []
        for invalid_dir in invalid_dirs:
            invalid_path = examples_dir / "case1_process_creation" / invalid_dir
            if invalid_path.exists():
                invalid_files.extend(list(invalid_path.glob("*.yaml")))

        return invalid_files

    def run_stageflow_cli(
        self, process_file: Path, expect_success: bool = True
    ) -> dict:
        """Run StageFlow CLI on a process file and return result."""
        cmd = ["uv", "run", "stageflow", "process", "view", str(process_file)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).parent.parent.parent,
            )

            success = result.returncode == 0
            if expect_success and not success:
                pytest.fail(
                    f"Expected {process_file.name} to load successfully but got "
                    f"exit code {result.returncode}. stderr: {result.stderr}"
                )
            elif not expect_success and success:
                pytest.fail(
                    f"Expected {process_file.name} to fail but it loaded successfully"
                )

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": success,
            }

        except subprocess.TimeoutExpired:
            pytest.fail(f"CLI command timed out for {process_file.name}")
        except Exception as e:
            pytest.fail(f"Failed to run CLI command for {process_file.name}: {e}")

    def test_all_valid_examples_batch(self, valid_example_files: list[Path]):
        """Test all valid examples in a batch to ensure comprehensive coverage."""
        failed_files = []

        for process_file in valid_example_files:
            try:
                # Run without expect_success assertion, handle results manually
                cmd = ["uv", "run", "stageflow", "process", "view", str(process_file)]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path(__file__).parent.parent.parent,
                )

                if result.returncode != 0:
                    failed_files.append(
                        {
                            "file": process_file,
                            "exit_code": result.returncode,
                            "error": result.stderr or result.stdout,
                        }
                    )
            except Exception as e:
                failed_files.append(
                    {"file": process_file, "exit_code": "exception", "error": str(e)}
                )

        if failed_files:
            error_msg = "The following example files failed to load:\n"
            for failure in failed_files:
                error_msg += (
                    f"  - {failure['file'].name}: {failure['error'][:100]}...\n"
                )
            pytest.fail(error_msg)

    def test_invalid_examples_fail_appropriately(
        self, invalid_example_files: list[Path]
    ):
        """Test that intentionally invalid examples fail with appropriate error messages."""
        assert invalid_example_files, "Invalid example files should exist for testing"

        for process_file in invalid_example_files:
            # All invalid example files should be structural errors that fail to load
            result = self.run_stageflow_cli(process_file, expect_success=False)
            assert not result["success"], (
                f"Structural error file {process_file.name} should fail to load"
            )

            # Should provide meaningful error output
            error_output = result["stderr"] or result["stdout"]
            assert len(error_output.strip()) > 0, (
                f"Should provide error message for {process_file.name}"
            )

    def test_visualization_examples_generate_diagrams(self, examples_dir: Path):
        """Test that visualization examples can generate Mermaid diagrams."""
        viz_dir = examples_dir / "case3_visualization"
        assert viz_dir.exists(), "Visualization examples directory should exist"

        viz_files = list(viz_dir.glob("**/*.yaml"))
        assert viz_files, "Visualization example files should exist"

        failed_visualizations = []

        for viz_file in viz_files:
            # Skip files that are intentionally invalid
            if "invalid" in str(viz_file) or "error" in str(viz_file):
                continue

            try:
                # Test visualization generation
                cmd = [
                    "uv",
                    "run",
                    "stageflow",
                    "process",
                    "diagram",
                    str(viz_file),
                    "-o",
                    "/tmp/test_viz.md",
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=examples_dir.parent,
                )

                if result.returncode != 0:
                    failed_visualizations.append(
                        {"file": viz_file, "error": result.stderr or result.stdout}
                    )

            except Exception as e:
                failed_visualizations.append({"file": viz_file, "error": str(e)})

        if failed_visualizations:
            error_msg = "The following visualization examples failed:\n"
            for failure in failed_visualizations:
                error_msg += (
                    f"  - {failure['file'].name}: {failure['error'][:100]}...\n"
                )
            pytest.fail(error_msg)

    def test_examples_contain_no_uppercase_lock_types(self, examples_dir: Path):
        """Test that no example files contain uppercase lock types (except intentional INVALID_TYPE)."""
        yaml_files = list(examples_dir.glob("**/*.yaml"))
        files_with_uppercase_locks = []

        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    content = f.read()

                # Check for uppercase lock types (excluding INVALID_TYPE which is intentional)
                uppercase_patterns = [
                    "type: EQUALS",
                    "type: NOT_EMPTY",
                    "type: TYPE_CHECK",
                    "type: GREATER_THAN",
                    "type: LESS_THAN",
                    "type: RANGE",
                    "type: REGEX",
                    "type: CONTAINS",
                    "type: LENGTH",
                    "type: IN_LIST",
                    "type: NOT_IN_LIST",
                ]

                found_patterns = []
                for pattern in uppercase_patterns:
                    if pattern in content:
                        found_patterns.append(pattern)

                if found_patterns:
                    files_with_uppercase_locks.append(
                        {"file": yaml_file, "patterns": found_patterns}
                    )

            except Exception as e:
                pytest.fail(f"Failed to read {yaml_file}: {e}")

        if files_with_uppercase_locks:
            error_msg = "Found files with uppercase lock types (should be lowercase):\n"
            for item in files_with_uppercase_locks:
                error_msg += f"  - {item['file'].name}: {', '.join(item['patterns'])}\n"
            pytest.fail(error_msg)

    def test_examples_directory_structure(self, examples_dir: Path):
        """Test that the examples directory has the expected structure."""
        assert examples_dir.exists(), "Examples directory should exist"

        # Check for expected case directories
        expected_cases = [
            "case1_process_creation",
            "case2_element_validation",
            "case3_visualization",
        ]
        for case in expected_cases:
            case_dir = examples_dir / case
            assert case_dir.exists(), f"Expected case directory {case} should exist"

            # Each case should have at least one YAML file
            yaml_files = list(case_dir.glob("**/*.yaml"))
            assert len(yaml_files) > 0, (
                f"Case {case} should contain at least one YAML file"
            )

    def test_examples_are_loadable_by_process_api(
        self, valid_example_files: list[Path]
    ):
        """Test that examples can be loaded using the Python API, not just CLI."""
        # This test ensures examples work with the core StageFlow API
        from stageflow.loader import load_process

        failed_loads = []

        for process_file in valid_example_files[:5]:  # Test first 5 to avoid timeout
            try:
                process = load_process(str(process_file))
                assert process is not None, (
                    f"Process should be loaded from {process_file.name}"
                )

                # Basic validation that the process has required attributes
                assert hasattr(process, "name"), (
                    f"Process from {process_file.name} should have name"
                )
                assert hasattr(process, "stages"), (
                    f"Process from {process_file.name} should have stages"
                )

            except Exception as e:
                failed_loads.append({"file": process_file, "error": str(e)})

        if failed_loads:
            error_msg = "The following files failed to load via Python API:\n"
            for failure in failed_loads:
                error_msg += (
                    f"  - {failure['file'].name}: {failure['error'][:100]}...\n"
                )
            pytest.fail(error_msg)
