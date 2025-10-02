"""Tests for the evaluate CLI command."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from stageflow.cli.main import cli


class TestEvaluateCommand:
    """Test suite for the evaluate CLI command."""

    def test_evaluate_basic_usage(self, sample_process_file, sample_element_file):
        """Test basic evaluate command functionality."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            str(sample_element_file)
        ])

        assert result.exit_code == 0
        assert "State:" in result.output
        assert "Actions:" in result.output

    def test_evaluate_with_verbose(self, sample_process_file, sample_element_file):
        """Test evaluate command with verbose output."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            '--verbose',
            'evaluate',
            str(sample_process_file),
            str(sample_element_file)
        ])

        assert result.exit_code == 0
        assert "🔄 Loading process" in result.output
        assert "🔄 Loading element" in result.output
        assert "🔄 Evaluating element" in result.output

    def test_evaluate_json_output(self, sample_process_file, sample_element_file):
        """Test evaluate command with JSON output format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            str(sample_element_file),
            '--format', 'json'
        ])

        assert result.exit_code == 0
        # Should be valid JSON
        output_data = json.loads(result.output)
        assert 'state' in output_data
        assert 'actions' in output_data

    def test_evaluate_yaml_output(self, sample_process_file, sample_element_file):
        """Test evaluate command with YAML output format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            str(sample_element_file),
            '--format', 'yaml'
        ])

        assert result.exit_code == 0
        assert "state:" in result.output

    def test_evaluate_with_output_file(self, sample_process_file, sample_element_file):
        """Test evaluate command with file output."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = Path(f.name)

        try:
            result = runner.invoke(cli, [
                '--verbose',
                'evaluate',
                str(sample_process_file),
                str(sample_element_file),
                '--format', 'json',
                '--output', str(output_file)
            ])

            assert result.exit_code == 0
            assert "✅ Evaluation result written to" in result.output
            assert output_file.exists()

            # Verify file content
            with open(output_file) as f:
                data = json.load(f)
                assert 'state' in data
                assert 'actions' in data
        finally:
            if output_file.exists():
                output_file.unlink()

    def test_evaluate_with_current_stage(self, sample_process_file, sample_element_file):
        """Test evaluate command with current stage specification."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            str(sample_element_file),
            '--current-stage', 'stage1'
        ])

        assert result.exit_code == 0

    def test_evaluate_nonexistent_process_file(self, sample_element_file):
        """Test evaluate command with non-existent process file."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            'nonexistent.yaml',
            str(sample_element_file)
        ])

        assert result.exit_code == 2  # Click error for missing file

    def test_evaluate_nonexistent_element_file(self, sample_process_file):
        """Test evaluate command with non-existent element file."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            'nonexistent.json'
        ])

        assert result.exit_code == 2  # Click error for missing file

    def test_evaluate_invalid_format(self, sample_process_file, sample_element_file):
        """Test evaluate command with invalid output format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'evaluate',
            str(sample_process_file),
            str(sample_element_file),
            '--format', 'invalid'
        ])

        # Click validates choice options, so this returns exit code 2
        assert result.exit_code == 2
        assert "Invalid value for '--format'" in result.output

    def test_evaluate_invalid_json_element(self, sample_process_file):
        """Test evaluate command with invalid JSON element file."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            element_file = Path(f.name)

        try:
            result = runner.invoke(cli, [
                'evaluate',
                str(sample_process_file),
                str(element_file)
            ])

            assert result.exit_code == 1
            assert "Invalid JSON" in result.output
        finally:
            if element_file.exists():
                element_file.unlink()
