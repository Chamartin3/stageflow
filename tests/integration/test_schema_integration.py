"""Integration tests for schema API with example processes.

This test suite validates the schema extraction functionality
using real example processes from the examples directory.
"""

import time
from pathlib import Path

import pytest

from stageflow.element import DictElement
from stageflow.schema import load_process


class TestSchemaIntegration:
    """Integration tests for schema API using example processes."""

    @pytest.fixture
    def examples_dir(self):
        """Path to examples directory."""
        return Path(__file__).parent.parent.parent / "examples"

    def test_simple_user_registration_schema(self, examples_dir):
        """Test schema extraction with simple user registration process."""
        # Arrange
        process_file = examples_dir / "simple" / "user_registration.yaml"
        if not process_file.exists():
            pytest.skip(f"Example file not found: {process_file}")

        process = load_process(str(process_file))

        # Act - Test partial mode for each stage
        signup_schema = process.get_schema("email_signup", partial=True)
        profile_schema = process.get_schema("profile_setup", partial=True)
        active_schema = process.get_schema("active_user", partial=True)

        # Assert - Verify stage-specific schemas
        assert signup_schema is not None
        assert "email" in signup_schema
        assert signup_schema["email"]["type"] == "str"

        assert profile_schema is not None
        assert "profile.first_name" in profile_schema
        assert "profile.last_name" in profile_schema

        # Active user stage should have minimal or no additional properties
        if active_schema:
            # If active_user has properties, verify their structure
            for prop_name, prop_def in active_schema.items():
                assert isinstance(prop_name, str)
                if prop_def is not None:
                    assert "type" in prop_def

    def test_simple_user_registration_cumulative_schema(self, examples_dir):
        """Test cumulative schema extraction with user registration process."""
        # Arrange
        process_file = examples_dir / "simple" / "user_registration.yaml"
        if not process_file.exists():
            pytest.skip(f"Example file not found: {process_file}")

        process = load_process(str(process_file))

        # Act - Test cumulative mode for final stage
        cumulative_schema = process.get_schema("active_user", partial=False)

        # Assert - Should include properties from all previous stages
        assert cumulative_schema is not None
        assert "email" in cumulative_schema  # From email_signup
        assert "profile.first_name" in cumulative_schema  # From profile_setup
        assert "profile.last_name" in cumulative_schema  # From profile_setup

    def test_intermediate_content_approval_schema(self, examples_dir):
        """Test schema extraction with intermediate content approval process."""
        # Arrange
        content_approval_file = examples_dir / "intermediate" / "content_approval.yaml"
        if not content_approval_file.exists():
            pytest.skip(f"Example file not found: {content_approval_file}")

        process = load_process(str(content_approval_file))

        # Act - Get schemas for different stages
        stage_names = [process.stages[0]._id for process.stages in [process.stages]]
        if not stage_names:
            pytest.skip("No stages found in process")

        # Test partial schemas for each stage
        partial_schemas = {}
        for stage in process.stages:
            stage_name = stage._id
            partial_schemas[stage_name] = process.get_schema(stage_name, partial=True)

        # Test cumulative schema for final stage
        final_stage = process.final_stage._id
        cumulative_schema = process.get_schema(final_stage, partial=False)

        # Assert
        assert len(partial_schemas) > 0
        assert cumulative_schema is not None

        # Verify cumulative schema includes more properties than any single stage
        max_partial_size = max(
            len(schema) if schema else 0 for schema in partial_schemas.values()
        )
        cumulative_size = len(cumulative_schema) if cumulative_schema else 0

        # Cumulative should be >= max partial (could be equal if stages don't overlap)
        assert cumulative_size >= max_partial_size

    def test_advanced_process_schema_performance(self, examples_dir):
        """Test schema extraction performance with complex advanced processes."""
        # Arrange
        advanced_dir = examples_dir / "advanced"
        if not advanced_dir.exists():
            pytest.skip(f"Advanced examples directory not found: {advanced_dir}")

        yaml_files = list(advanced_dir.glob("*.yaml"))
        if not yaml_files:
            pytest.skip("No advanced example files found")

        # Test with the first available advanced process
        process_file = yaml_files[0]
        process = load_process(str(process_file))

        # Act - Measure schema extraction performance
        start_time = time.time()

        # Test all stages in both modes
        for stage in process.stages:
            stage_name = stage._id
            partial_schema = process.get_schema(stage_name, partial=True)
            cumulative_schema = process.get_schema(stage_name, partial=False)

            # Basic validation that schemas are returned
            assert partial_schema is not None or stage.get_schema() is None
            assert cumulative_schema is not None

        end_time = time.time()

        # Assert - Performance should meet target
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert execution_time < 100  # Should complete in less than 100ms

    def test_schema_consistency_across_examples(self, examples_dir):
        """Test schema consistency across different example processes."""
        # Arrange
        all_yaml_files = list(examples_dir.rglob("*.yaml"))
        if len(all_yaml_files) < 2:
            pytest.skip("Need at least 2 example files for consistency testing")

        processes = []
        for yaml_file in all_yaml_files[
            :5
        ]:  # Test up to 5 processes for reasonable test time
            try:
                process = load_process(str(yaml_file))
                processes.append((yaml_file.name, process))
            except Exception:
                # Skip files that can't be loaded
                continue

        if len(processes) < 2:
            pytest.skip("Need at least 2 loadable processes for consistency testing")

        # Act & Assert - Test schema API consistency
        for file_name, process in processes:
            # Every process should have at least initial and final stages
            assert process.initial_stage is not None, f"No initial stage in {file_name}"
            assert process.final_stage is not None, f"No final stage in {file_name}"

            # Schema extraction should work for all stages
            for stage in process.stages:
                stage_name = stage._id

                # Both partial and cumulative modes should work
                partial_schema = process.get_schema(stage_name, partial=True)
                cumulative_schema = process.get_schema(stage_name, partial=False)

                # Schemas should be valid types
                assert partial_schema is None or isinstance(partial_schema, dict)
                assert cumulative_schema is None or isinstance(cumulative_schema, dict)

                # Cumulative should include at least as many properties as partial
                partial_size = len(partial_schema) if partial_schema else 0
                cumulative_size = len(cumulative_schema) if cumulative_schema else 0
                assert cumulative_size >= partial_size, (
                    f"Cumulative schema smaller than partial in {file_name}"
                )

    def test_schema_with_real_element_data(self, examples_dir):
        """Test schema extraction works with actual element evaluation."""
        # Arrange
        process_file = examples_dir / "simple" / "user_registration.yaml"
        if not process_file.exists():
            pytest.skip(f"Example file not found: {process_file}")

        process = load_process(str(process_file))

        # Create test data that matches expected schema
        test_data = {
            "email": "test@example.com",
            "profile": {"first_name": "John", "last_name": "Doe"},
            "meta": {"email_verified_at": "2024-01-01T10:00:00Z"},
        }
        element = DictElement(test_data)

        # Act - Get schemas and verify they align with element evaluation
        signup_schema = process.get_schema("email_signup", partial=True)

        # Evaluate element at this stage
        result = process.evaluate(element, "email_signup")

        # Assert - Schema properties should align with what evaluation checks
        assert signup_schema is not None
        assert result is not None

        # The schema should include properties that the evaluation process uses
        if "email" in test_data and signup_schema:
            assert "email" in signup_schema

    def test_error_handling_with_invalid_stages(self, examples_dir):
        """Test error handling when requesting schemas for invalid stages."""
        # Arrange
        process_file = examples_dir / "simple" / "user_registration.yaml"
        if not process_file.exists():
            pytest.skip(f"Example file not found: {process_file}")

        process = load_process(str(process_file))

        # Act & Assert - Should raise ValueError for invalid stage names
        with pytest.raises(ValueError, match="Stage 'nonexistent_stage' not found"):
            process.get_schema("nonexistent_stage")

        with pytest.raises(ValueError, match="Stage 'another_invalid_stage' not found"):
            process.get_schema("another_invalid_stage", partial=False)

    def test_schema_types_match_stageflow_definitions(self, examples_dir):
        """Test that returned schemas match StageFlow type definitions."""
        # Arrange
        all_yaml_files = list(examples_dir.rglob("*.yaml"))
        if not all_yaml_files:
            pytest.skip("No example files found")

        # Test with first available process
        process_file = all_yaml_files[0]
        process = load_process(str(process_file))

        # Act - Get schemas for all stages
        for stage in process.stages:
            stage_name = stage._id
            schema = process.get_schema(stage_name, partial=True)

            # Assert - Schema should match ExpectedObjectSchmema type
            if schema is not None:
                assert isinstance(schema, dict)

                for prop_name, prop_def in schema.items():
                    assert isinstance(prop_name, str)

                    # Property definition should be None or StageObjectPropertyDefinition
                    if prop_def is not None:
                        assert isinstance(prop_def, dict)
                        # Should have at least type or default (could have both or neither)
                        valid_keys = {"type", "default"}
                        assert all(key in valid_keys for key in prop_def.keys())

    def test_memory_usage_with_large_schemas(self, examples_dir):
        """Test memory efficiency with larger schema extractions."""
        # Arrange
        all_yaml_files = list(examples_dir.rglob("*.yaml"))
        if not all_yaml_files:
            pytest.skip("No example files found")

        processes = []
        for yaml_file in all_yaml_files:
            try:
                process = load_process(str(yaml_file))
                processes.append(process)
            except Exception:
                continue

        if not processes:
            pytest.skip("No loadable processes found")

        # Act - Extract schemas from multiple processes multiple times
        schemas_extracted = 0
        for process in processes:
            for stage in process.stages:
                stage_name = stage._id

                # Extract schema multiple times to test for memory leaks
                for _ in range(10):
                    process.get_schema(stage_name, partial=True)
                    process.get_schema(stage_name, partial=False)
                    schemas_extracted += 2

        # Assert - Should have extracted many schemas without issues
        assert schemas_extracted >= 20  # At least some schemas were extracted

        # If we get here without memory errors, the test passes
        # This is more of a smoke test for memory issues
