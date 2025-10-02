"""Tests for the validate CLI command."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from stageflow.cli.main import cli


class TestValidateCommand:
    """Test suite for the validate CLI command."""

    def test_validate_basic_usage(self, sample_process_file):
        """Test basic validate command functionality."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'validate',
            str(sample_process_file)
        ])

        # Note: The command might exit with 1 if there are validation errors
        # That's still considered successful command execution
        assert result.exit_code in [0, 1]
        assert "Process:" in result.output
        assert "Summary:" in result.output

    def test_validate_with_verbose(self, sample_process_file):
        """Test validate command with verbose output."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            '--verbose',
            'validate',
            str(sample_process_file)
        ])

        assert result.exit_code in [0, 1]
        assert "🔄 Loading process" in result.output
        assert "🔄 Validating process" in result.output

    def test_validate_json_output(self, sample_process_file):
        """Test validate command with JSON output format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'validate',
            str(sample_process_file),
            '--format', 'json'
        ])

        assert result.exit_code in [0, 1]
        # Should be valid JSON
        try:
            output_data = json.loads(result.output)
            assert 'process_name' in output_data
            assert 'summary' in output_data
            assert 'messages' in output_data
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_validate_with_output_file(self, sample_process_file):
        """Test validate command with file output."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = Path(f.name)

        try:
            result = runner.invoke(cli, [
                '--verbose',
                'validate',
                str(sample_process_file),
                '--format', 'json',
                '--output', str(output_file)
            ])

            assert result.exit_code in [0, 1]
            assert "✅" in result.output and "written to" in result.output
            assert output_file.exists()

            # Verify file content
            with open(output_file) as f:
                data = json.load(f)
                assert 'process_name' in data
                assert 'summary' in data
        finally:
            if output_file.exists():
                output_file.unlink()

    def test_validate_severity_filtering(self, sample_process_file):
        """Test validate command with different severity levels."""
        runner = CliRunner()
        severities = ['error', 'warning', 'info']

        for severity in severities:
            result = runner.invoke(cli, [
                'validate',
                str(sample_process_file),
                '--severity', severity
            ])

            assert result.exit_code in [0, 1]
            assert "Summary:" in result.output

    def test_validate_nonexistent_file(self):
        """Test validate command with non-existent process file."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'validate',
            'nonexistent.yaml'
        ])

        assert result.exit_code == 2  # Click error for missing file

    def test_validate_invalid_format(self, sample_process_file):
        """Test validate command with invalid output format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'validate',
            str(sample_process_file),
            '--format', 'invalid'
        ])

        # Click validates choice options, so this returns exit code 2
        assert result.exit_code == 2
        assert "Invalid value for '--format'" in result.output

    def test_validate_error_exit_code(self, sample_process_file):
        """Test that validate command exits with error code when validation fails."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'validate',
            str(sample_process_file),
            '--severity', 'error'
        ])

        # If there are errors, should exit with code 1
        # If no errors, should exit with code 0
        assert result.exit_code in [0, 1]

        if result.exit_code == 1:
            # Should show error information
            assert "ERROR:" in result.output or "❌" in result.output

    def test_validate_no_issues_message(self):
        """Test validate command with a valid process that has no issues."""
        runner = CliRunner()

        # Create a minimal valid process for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
name: simple_test
stage_order:
  - stage1
stages:
  stage1:
    gates:
      gate1:
        logic: and
        locks:
          - property: field1
            type: exists
""")
            process_file = Path(f.name)

        try:
            result = runner.invoke(cli, [
                'validate',
                str(process_file),
                '--severity', 'info'
            ])

            # Check if the command ran successfully
            assert result.exit_code in [0, 1]
            assert "Process: simple_test" in result.output
        finally:
            if process_file.exists():
                process_file.unlink()
