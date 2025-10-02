"""Tests for enhanced YAML loader with validation and comment preservation."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from stageflow.process.main import Process
from stageflow.process.schema.loaders.yaml import (
    YAMLIncludeError,
    YamlLoader,
    YAMLLoadError,
    YAMLSchemaError,
    load_process,
    load_process_from_string,
)


class TestYamlLoader:
    """Test cases for YamlLoader class."""

    def test_init_with_default_settings(self):
        """Test loader initialization with default settings."""
        loader = YamlLoader()
        assert loader.yaml.preserve_quotes is True
        assert loader.yaml.width == 120
        assert loader._current_file is None
        assert loader._include_stack == []

    def test_init_with_custom_settings(self):
        """Test loader initialization with custom settings."""
        loader = YamlLoader(preserve_quotes=False, width=80)
        assert loader.yaml.preserve_quotes is False
        assert loader.yaml.width == 80

    def test_load_simple_process_from_string(self):
        """Test loading a simple process from YAML string."""
        yaml_content = dedent("""
            name: test_process
            stage_order: [stage1, stage2]
            stages:
              stage1:
                gates:
                  gate1:
                    logic: and
                    locks:
                      - property: field1
                        type: exists
                      - property: field1_status
                        type: exists
              stage2:
                gates:
                  gate2:
                    logic: and
                    locks:
                      - property: field2
                        type: equals
                        value: complete
                      - property: field2_status
                        type: exists
        """).strip()

        process = load_process_from_string(yaml_content)
        assert isinstance(process, Process)
        assert process.name == "test_process"
        assert process.stage_order == ["stage1", "stage2"]
        assert len(process.stages) == 2

    def test_load_process_from_file(self):
        """Test loading process from YAML file."""
        yaml_content = dedent("""
            name: file_process
            stages:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: test
                        type: exists
                      - property: test_status
                        type: exists
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            process = load_process(temp_path)
            assert process.name == "file_process"
            assert len(process.stages) == 1
        finally:
            Path(temp_path).unlink()

    def test_file_not_found_error(self):
        """Test error handling for non-existent files."""
        with pytest.raises(YAMLLoadError) as exc_info:
            load_process("non_existent.yaml")

        assert "Process file not found" in str(exc_info.value)
        assert "non_existent.yaml" in str(exc_info.value)

    def test_invalid_yaml_syntax_error(self):
        """Test error handling for invalid YAML syntax."""
        invalid_yaml = "name: test\n  invalid: [unclosed"

        with pytest.raises(YAMLLoadError) as exc_info:
            load_process_from_string(invalid_yaml)

        assert "YAML parsing error" in str(exc_info.value)

    def test_schema_validation_missing_name(self):
        """Test schema validation for missing process name."""
        yaml_content = dedent("""
            stages:
              stage1:
                gates: {}
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "must include 'name' field" in str(exc_info.value)

    def test_schema_validation_empty_name(self):
        """Test schema validation for empty process name."""
        yaml_content = dedent("""
            name: ""
            stages: {}
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "must be a non-empty string" in str(exc_info.value)

    def test_schema_validation_invalid_stages_type(self):
        """Test schema validation for invalid stages type."""
        yaml_content = dedent("""
            name: test
            stages: not_a_dict
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "'stages' must be a dictionary" in str(exc_info.value)

    def test_schema_validation_invalid_stage_order_type(self):
        """Test schema validation for invalid stage_order type."""
        yaml_content = dedent("""
            name: test
            stage_order: not_a_list
            stages:
              stage1: {}
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "'stage_order' must be a list" in str(exc_info.value)

    def test_schema_validation_invalid_stage_order_references(self):
        """Test schema validation for stage_order referencing non-existent stages."""
        yaml_content = dedent("""
            name: test
            stage_order: [stage1, non_existent]
            stages:
              stage1: {}
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "stage_order references non-existent stages" in str(exc_info.value)
        assert "non_existent" in str(exc_info.value)

    def test_schema_validation_invalid_gate_logic(self):
        """Test schema validation for invalid gate logic."""
        yaml_content = dedent("""
            name: test
            stages:
              stage1:
                gates:
                  gate1:
                    logic: invalid_logic
                    locks: []
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        # Gates are now AND-only by design, so empty locks trigger component validation first
        assert "Gate requires at least one component" in str(exc_info.value)

    def test_schema_validation_invalid_locks_type(self):
        """Test schema validation for invalid locks type."""
        yaml_content = dedent("""
            name: test
            stages:
              stage1:
                gates:
                  gate1:
                    locks: not_a_list
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "must be a list" in str(exc_info.value)

    def test_schema_validation_lock_missing_property(self):
        """Test schema validation for lock missing property field."""
        yaml_content = dedent("""
            name: test
            stages:
              stage1:
                gates:
                  gate1:
                    locks:
                      - type: exists
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "must include 'property' or 'property_path' field" in str(exc_info.value)

    def test_schema_validation_lock_missing_type(self):
        """Test schema validation for lock missing type field."""
        yaml_content = dedent("""
            name: test
            stages:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: test
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "must include 'type' or 'lock_type' field" in str(exc_info.value)

    def test_schema_validation_invalid_lock_type(self):
        """Test schema validation for invalid lock type."""
        yaml_content = dedent("""
            name: test
            stages:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: test
                        type: invalid_type
        """).strip()

        with pytest.raises(YAMLSchemaError) as exc_info:
            load_process_from_string(yaml_content)

        assert "Invalid lock type 'invalid_type'" in str(exc_info.value)

    def test_save_process_with_comments(self):
        """Test saving process with preserved formatting."""
        yaml_content = dedent("""
            name: test_process
            stages:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: field1
                        type: exists
        """).strip()

        process = load_process_from_string(yaml_content)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            loader = YamlLoader()
            loader.save_process(process, temp_path)

            # Check that file was created and contains header comments
            content = Path(temp_path).read_text()
            assert "# StageFlow Process Definition: test_process" in content
            assert "# Generated by StageFlow YAML Loader" in content
            assert "name: test_process" in content
        finally:
            Path(temp_path).unlink()

    def test_comment_preservation(self):
        """Test that comments are preserved during round-trip."""
        yaml_content = dedent("""
            # Main process definition
            name: test_process

            # Stage definitions
            stages:
              stage1:  # First stage
                gates:
                  gate1:
                    locks:
                      - property: field1  # Required field
                        type: exists
        """).strip()

        process = load_process_from_string(yaml_content)

        # Save and reload to test round-trip
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            loader = YamlLoader()
            loader.save_process(process, temp_path)

            # Reload the process
            reloaded_process = load_process(temp_path)
            assert reloaded_process.name == process.name
            assert len(reloaded_process.stages) == len(process.stages)
        finally:
            Path(temp_path).unlink()


class TestYAMLIncludes:
    """Test cases for YAML include functionality."""

    def test_simple_include(self):
        """Test simple file include."""
        # Create included file
        included_content = dedent("""
            stage1:
              gates:
                gate1:
                  locks:
                    - property: included_field
                      type: exists
        """).strip()

        # Create main file
        main_content = dedent("""
            name: test_process
            stages:
              !include: included.yaml
        """).strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write included file
            included_file = temp_path / "included.yaml"
            included_file.write_text(included_content)

            # Write main file
            main_file = temp_path / "main.yaml"
            main_file.write_text(main_content)

            # Test loading
            process = load_process(main_file)
            assert process.name == "test_process"
            assert len(process.stages) == 1
            assert "stage1" in [s.name for s in process.stages]

    def test_include_with_key_selection(self):
        """Test include with specific key selection."""
        # Create included file with multiple sections
        included_content = dedent("""
            development:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: dev_field
                        type: exists
            production:
              stage1:
                gates:
                  gate1:
                    locks:
                      - property: prod_field
                        type: exists
        """).strip()

        # Create main file that includes specific key
        main_content = dedent("""
            name: test_process
            stages:
              !include:
                file: environments.yaml
                key: development
        """).strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write included file
            included_file = temp_path / "environments.yaml"
            included_file.write_text(included_content)

            # Write main file
            main_file = temp_path / "main.yaml"
            main_file.write_text(main_content)

            # Test loading
            process = load_process(main_file)
            assert process.name == "test_process"
            # Should have loaded the development section
            stage = process.stages[0]
            lock_wrapper = stage.gates[0].components[0]
            assert lock_wrapper.lock.property_path == "dev_field"

    def test_include_file_not_found(self):
        """Test error handling for missing include files."""
        main_content = dedent("""
            name: test_process
            stages:
              !include: missing.yaml
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(main_content)
            temp_path = f.name

        try:
            with pytest.raises(YAMLIncludeError) as exc_info:
                load_process(temp_path)

            assert "Include file not found" in str(exc_info.value)
            assert "missing.yaml" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_circular_include_detection(self):
        """Test detection of circular include dependencies."""
        # Create file A that includes file B
        content_a = dedent("""
            name: test_process
            stages:
              !include: file_b.yaml
        """).strip()

        # Create file B that includes file A
        content_b = dedent("""
            stage1:
              gates:
                gate1:
                  locks:
                    - !include: file_a.yaml
        """).strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            file_a = temp_path / "file_a.yaml"
            file_b = temp_path / "file_b.yaml"

            file_a.write_text(content_a)
            file_b.write_text(content_b)

            with pytest.raises(YAMLIncludeError) as exc_info:
                load_process(file_a)

            assert "Circular include dependency detected" in str(exc_info.value)

    def test_include_missing_key(self):
        """Test error handling for missing keys in included files."""
        included_content = dedent("""
            existing_key:
              value: test
        """).strip()

        main_content = dedent("""
            name: test_process
            stages:
              !include:
                file: included.yaml
                key: missing_key
        """).strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            included_file = temp_path / "included.yaml"
            included_file.write_text(included_content)

            main_file = temp_path / "main.yaml"
            main_file.write_text(main_content)

            with pytest.raises(YAMLIncludeError) as exc_info:
                load_process(main_file)

            assert "Key 'missing_key' not found" in str(exc_info.value)


class TestErrorReporting:
    """Test cases for enhanced error reporting."""

    def test_error_with_file_path(self):
        """Test that errors include file path information."""
        yaml_content = "name: test\nstages: invalid_structure"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(YAMLSchemaError) as exc_info:
                load_process(temp_path)

            assert temp_path in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_error_with_line_numbers(self):
        """Test that YAML parsing errors include line numbers."""
        invalid_yaml = "name: test\n  invalid: [unclosed"

        with pytest.raises(YAMLLoadError) as exc_info:
            load_process_from_string(invalid_yaml, "test.yaml")

        error = exc_info.value
        assert error.file_path == "test.yaml"
        assert error.line is not None
        assert "at line" in str(error)

    def test_custom_error_classes(self):
        """Test custom error class hierarchy."""
        # Test YAMLLoadError
        error = YAMLLoadError("test message", "file.yaml", 10, 5)
        assert error.message == "test message"
        assert error.file_path == "file.yaml"
        assert error.line == 10
        assert error.column == 5
        assert "test message in file 'file.yaml' at line 10, column 5" == str(error)

        # Test YAMLSchemaError inheritance
        schema_error = YAMLSchemaError("schema error")
        assert isinstance(schema_error, YAMLLoadError)

        # Test YAMLIncludeError inheritance
        include_error = YAMLIncludeError("include error")
        assert isinstance(include_error, YAMLLoadError)


class TestIntegration:
    """Integration tests with other StageFlow components."""

    def test_integration_with_process_evaluation(self):
        """Test that loaded processes work correctly with evaluation."""
        yaml_content = dedent("""
            name: integration_test
            stage_order: [initial, final]
            stages:
              initial:
                gates:
                  ready:
                    logic: and
                    locks:
                      - property: status
                        type: equals
                        value: ready
              final:
                gates:
                  complete:
                    logic: and
                    locks:
                      - property: status
                        type: equals
                        value: complete
        """).strip()

        process = load_process_from_string(yaml_content)

        # Verify process structure
        assert process.name == "integration_test"
        assert len(process.stages) == 2
        assert process.stage_order == ["initial", "final"]

        # Verify stages
        initial_stage = next(s for s in process.stages if s.name == "initial")
        final_stage = next(s for s in process.stages if s.name == "final")

        assert len(initial_stage.gates) == 1
        assert len(final_stage.gates) == 1

        # Verify locks (accessed through components)
        ready_gate = initial_stage.gates[0]
        assert ready_gate.name == "ready"
        assert len(ready_gate.components) == 1
        lock_wrapper = ready_gate.components[0]
        assert hasattr(lock_wrapper, 'lock')
        assert lock_wrapper.lock.property_path == "status"
        assert lock_wrapper.lock.expected_value == "ready"

    def test_complex_process_structure(self):
        """Test loading a complex process with nested structures."""
        yaml_content = dedent("""
            name: complex_process
            stage_order: [registration, verification, activation]
            allow_stage_skipping: false
            regression_detection: true
            metadata:
              version: "1.0"
              description: "Complex test process"

            stages:
              registration:
                allow_partial: true
                metadata:
                  description: "User registration stage"
                schema:
                  required_fields: [email, password]
                  field_types:
                    email: string
                    password: string
                  validation_rules:
                    email: email_format
                gates:
                  basic_info:
                    logic: and
                    metadata:
                      description: "Basic information validation"
                    locks:
                      - property: email
                        type: exists
                        metadata:
                          description: "Email address required"
                      - property: password
                        type: exists
                        metadata:
                          description: "Password required"
                  email_format:
                    logic: and
                    locks:
                      - property: email
                        type: regex
                        value: "^[^@]+@[^@]+\\\\.[^@]+$"

              verification:
                gates:
                  verified:
                    logic: and
                    locks:
                      - property: email_verified
                        type: equals
                        value: true
                      - property: phone_verified
                        type: equals
                        value: true

              activation:
                gates:
                  active:
                    logic: and
                    locks:
                      - property: status
                        type: equals
                        value: active
        """).strip()

        process = load_process_from_string(yaml_content)

        # Verify top-level properties
        assert process.name == "complex_process"
        assert not process.allow_stage_skipping
        assert process.regression_detection
        assert process.metadata["version"] == "1.0"

        # Verify registration stage
        reg_stage = next(s for s in process.stages if s.name == "registration")
        assert reg_stage.allow_partial
        assert reg_stage.schema is not None
        assert "email" in reg_stage.schema.required_fields
        assert len(reg_stage.gates) == 2

        # Verify gates and locks
        basic_info_gate = next(g for g in reg_stage.gates if g.name == "basic_info")
        assert len(basic_info_gate.components) == 2
        assert basic_info_gate.components[0].lock.property_path == "email"
        assert basic_info_gate.components[1].lock.property_path == "password"
