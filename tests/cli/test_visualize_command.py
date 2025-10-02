"""Tests for the visualize CLI command."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from stageflow.cli.main import cli


class TestVisualizeCommand:
    """Test suite for the visualize CLI command."""

    def test_visualize_basic_usage(self, sample_process_file):
        """Test basic visualize command functionality."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'visualize',
            str(sample_process_file),
            '--format', 'text'
        ])

        assert result.exit_code == 0
        assert "Process:" in result.output
        assert "Stage:" in result.output

    def test_visualize_with_verbose(self, sample_process_file):
        """Test visualize command with verbose output."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            '--verbose',
            'visualize',
            str(sample_process_file),
            '--format', 'text'
        ])

        assert result.exit_code == 0
        assert "🔄 Loading process" in result.output
        assert "🔄 Generating" in result.output

    def test_visualize_with_details(self, sample_process_file):
        """Test visualize command with detailed output."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'visualize',
            str(sample_process_file),
            '--format', 'text',
            '--include-details'
        ])

        assert result.exit_code == 0
        assert "Gate:" in result.output

    def test_visualize_with_output_file(self, sample_process_file):
        """Test visualize command with file output."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = Path(f.name)

        try:
            result = runner.invoke(cli, [
                '--verbose',
                'visualize',
                str(sample_process_file),
                '--format', 'text',
                '--output', str(output_file)
            ])

            assert result.exit_code == 0
            assert "✅" in result.output and "written to" in result.output
            assert output_file.exists()

            # Verify file content
            with open(output_file) as f:
                content = f.read()
                assert "Process:" in content
                assert "Stage:" in content
        finally:
            if output_file.exists():
                output_file.unlink()

    def test_visualize_nonexistent_file(self):
        """Test visualize command with non-existent process file."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'visualize',
            'nonexistent.yaml',
            '--format', 'text'
        ])

        assert result.exit_code == 2  # Click error for missing file

    def test_visualize_different_styles(self, sample_process_file):
        """Test visualize command with different style options."""
        runner = CliRunner()
        styles = ['overview', 'detailed', 'full']

        for style in styles:
            result = runner.invoke(cli, [
                'visualize',
                str(sample_process_file),
                '--format', 'text',
                '--style', style
            ])

            assert result.exit_code == 0
            assert "Process:" in result.output

    def test_visualize_mermaid_fallback(self, sample_process_file):
        """Test visualize command with mermaid format (should handle missing dependencies)."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'visualize',
            str(sample_process_file),
            '--format', 'mermaid'
        ])

        # Should either succeed or give a helpful error message
        if result.exit_code != 0:
            assert "visualization not available" in result.output or "Error:" in result.output

    def test_visualize_output_extension_auto(self, sample_process_file):
        """Test that output file gets appropriate extension based on format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_base = temp_path / "diagram"

            result = runner.invoke(cli, [
                'visualize',
                str(sample_process_file),
                '--format', 'text',
                '--output', str(output_base)
            ])

            assert result.exit_code == 0
            # Should have added .txt extension
            assert (output_base.with_suffix('.txt')).exists()
