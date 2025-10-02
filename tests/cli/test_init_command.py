"""Tests for the init CLI command."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from stageflow.cli.main import cli


class TestInitCommand:
    """Test suite for the init CLI command."""

    def test_init_basic_project(self):
        """Test basic project initialization."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'test-project',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0
            assert "✅ Project 'test-project' created successfully!" in result.output

            # Check project structure
            project_dir = temp_path / 'test-project'
            assert project_dir.exists()
            assert (project_dir / 'process.yaml').exists()
            assert (project_dir / 'example_element.json').exists()
            assert (project_dir / 'README.md').exists()
            assert (project_dir / 'elements').exists()
            assert (project_dir / 'outputs').exists()

    def test_init_with_verbose(self):
        """Test init command with verbose output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                '--verbose',
                'init',
                'test-project',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0
            assert "🔄 Creating project" in result.output
            assert "🔄 Generating process definition" in result.output
            assert "🔄 Writing process definition" in result.output

    def test_init_onboarding_template(self):
        """Test init command with onboarding template."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'onboarding-project',
                '--template', 'onboarding',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0

            # Check that onboarding-specific content exists
            project_dir = temp_path / 'onboarding-project'
            process_file = project_dir / 'process.yaml'

            with open(process_file) as f:
                content = f.read()
                assert 'registration' in content
                assert 'profile_setup' in content
                assert 'verification' in content
                assert 'activation' in content

    def test_init_json_format(self):
        """Test init command with JSON format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'json-project',
                '--format', 'json',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0

            # Check that JSON process file was created
            project_dir = temp_path / 'json-project'
            process_file = project_dir / 'process.json'
            assert process_file.exists()

            # Verify it's valid JSON
            with open(process_file) as f:
                data = json.load(f)
                assert 'name' in data
                assert 'stages' in data

    def test_init_all_templates(self):
        """Test init command with all available templates."""
        runner = CliRunner()
        templates = ['basic', 'onboarding', 'approval', 'ecommerce']

        for template in templates:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                result = runner.invoke(cli, [
                    'init',
                    f'{template}-project',
                    '--template', template,
                    '--output-dir', str(temp_path)
                ])

                assert result.exit_code == 0, f"Failed to create {template} template"

                # Verify project was created
                project_dir = temp_path / f'{template}-project'
                assert project_dir.exists()
                assert (project_dir / 'process.yaml').exists()

    def test_init_invalid_template(self):
        """Test init command with invalid template."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'test-project',
                '--template', 'invalid-template',
                '--output-dir', str(temp_path)
            ])

            # Click validates choice options, so this returns exit code 2
            assert result.exit_code == 2
            assert "Invalid value for '--template'" in result.output

    def test_init_invalid_format(self):
        """Test init command with invalid format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'test-project',
                '--format', 'invalid-format',
                '--output-dir', str(temp_path)
            ])

            # Click validates choice options, so this returns exit code 2
            assert result.exit_code == 2
            assert "Invalid value for '--format'" in result.output

    def test_init_existing_directory(self):
        """Test init command with existing directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / 'existing-project'
            project_dir.mkdir()

            result = runner.invoke(cli, [
                'init',
                'existing-project',
                '--output-dir', str(temp_path)
            ])

            # Should still succeed (creates files in existing directory)
            assert result.exit_code == 0

    def test_init_readme_content(self):
        """Test that README contains appropriate content."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'readme-test',
                '--template', 'onboarding',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0

            readme_file = temp_path / 'readme-test' / 'README.md'
            with open(readme_file) as f:
                content = f.read()
                assert '# readme-test' in content
                assert 'onboarding' in content
                assert 'stageflow validate' in content
                assert 'stageflow evaluate' in content

    def test_init_example_element_content(self):
        """Test that example element contains appropriate data for template."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = runner.invoke(cli, [
                'init',
                'element-test',
                '--template', 'onboarding',
                '--output-dir', str(temp_path)
            ])

            assert result.exit_code == 0

            element_file = temp_path / 'element-test' / 'example_element.json'
            with open(element_file) as f:
                data = json.load(f)
                assert 'email' in data
                assert 'password' in data
                assert 'profile' in data
