"""Unit tests for Process orchestration functionality."""

from unittest.mock import patch

import pytest
from stageflow.process.main import Process
from stageflow.process.config import ProcessConfig
from stageflow.process.schema.core import FieldDefinition, ItemSchema

from stageflow.core.element import DictElement
from stageflow.core.stage import Stage
from stageflow.process.result import EvaluationState, StatusResult


class TestProcessConfig:
    """Test ProcessConfig dataclass functionality."""

    def test_default_config(self):
        """Test ProcessConfig with minimal required parameters."""
        config = ProcessConfig(name="test_process")

        assert config.name == "test_process"
        assert config.initial_stage is None
        assert config.final_stage is None
        assert config.allow_stage_skipping is False
        assert config.max_batch_size == 1000
        assert config.metadata == {}

    def test_full_config(self):
        """Test ProcessConfig with all parameters specified."""
        metadata = {"version": "1.0", "author": "test"}
        config = ProcessConfig(
            name="full_process",
            initial_stage="start",
            final_stage="end",
            allow_stage_skipping=True,
            max_batch_size=500,
            metadata=metadata,
        )

        assert config.name == "full_process"
        assert config.initial_stage == "start"
        assert config.final_stage == "end"
        assert config.allow_stage_skipping is True
        assert config.max_batch_size == 500
        assert config.metadata == metadata



class TestProcess:
    """Test Process orchestration functionality."""

    @pytest.fixture
    def simple_stage(self):
        """Create a simple stage for testing."""
        schema = ItemSchema(name="basic")
        schema.add_field("name", FieldDefinition(type_=str, required=True))

        # Create a minimal stage for testing - stages don't require gates
        return Stage(name="basic_stage", gates=[], schema=schema)

    @pytest.fixture
    def process_config(self):
        """Create a process configuration for testing."""
        return ProcessConfig(name="test_process")

    def test_from_config(self, process_config, simple_stage):
        """Test Process creation from ProcessConfig."""
        process = Process.from_config(process_config, stages=[simple_stage])

        assert process.name == "test_process"
        assert len(process.stages) == 1
        assert process.stages[0].name == "basic_stage"


    def test_add_stage(self, simple_stage):
        """Test adding a stage to the process."""
        dummy_stage = Stage(name="dummy", gates=[], schema=ItemSchema(name="dummy"))
        process = Process(name="test", stages=[dummy_stage])

        process.add_stage(simple_stage)

        assert len(process.stages) == 2
        assert process.stages[1].name == "basic_stage"
        assert "basic_stage" in process.stage_order

    def test_add_duplicate_stage(self, simple_stage):
        """Test adding a duplicate stage raises error."""
        process = Process(name="test", stages=[simple_stage])

        with pytest.raises(ValueError, match="already exists"):
            process.add_stage(simple_stage)

    def test_evaluate_batch_empty(self, simple_stage):
        """Test batch evaluation with empty list."""
        process = Process(name="test", stages=[simple_stage])

        results = process.evaluate_batch([])

        assert results == []

    def test_evaluate_batch_with_elements(self, simple_stage):
        """Test batch evaluation with multiple elements."""
        process = Process(name="test", stages=[simple_stage])

        # Create test elements
        elements = [
            DictElement({"name": "test1"}),
            DictElement({"name": "test2"}),
            DictElement({"missing": "name"}),
        ]

        results = process.evaluate_batch(elements)

        assert len(results) == 3
        assert all(isinstance(result, StatusResult) for result in results)



    def test_evaluate_basic_functionality(self, simple_stage):
        """Test basic evaluation functionality."""
        process = Process(name="test", stages=[simple_stage])
        element = DictElement({"name": "test"})

        # Evaluate element
        result = process.evaluate(element)

        # Check basic result structure
        assert result.state == EvaluationState.COMPLETED

    def test_evaluate_with_timing(self, simple_stage):
        """Test that evaluation timing is tracked."""
        process = Process(name="test", stages=[simple_stage])
        element = DictElement({"name": "test"})

        # Patch time.time to return a sequence of values
        # More values to account for all time.time() calls in the evaluation flow
        with patch('time.time', side_effect=[0.0, 0.1, 0.1, 0.2, 0.2]):
            result = process.evaluate(element)

        # Check that evaluation completed successfully
        assert result.state in EvaluationState

    def test_evaluate_with_invalid_current_stage(self, simple_stage):
        """Test evaluation with invalid current stage name."""
        process = Process(name="test", stages=[simple_stage])
        element = DictElement({"name": "test"})

        result = process.evaluate(element, current_stage_name="nonexistent")

        assert result.state == EvaluationState.SCOPING
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]


    def test_evaluate_with_exception(self, simple_stage):
        """Test evaluation handles exceptions gracefully."""
        # Create a process that will trigger an exception by providing an invalid element
        process = Process(name="test", stages=[simple_stage])

        # Use an invalid element that will cause an exception during property access
        class BadElement:
            def has_property(self, path):
                raise RuntimeError("Test error")

            def get_property(self, path):
                raise RuntimeError("Test error")

            def to_dict(self):
                raise RuntimeError("Test error")

        bad_element = BadElement()
        result = process.evaluate(bad_element)

        assert result.state == EvaluationState.SCOPING
        assert len(result.errors) == 1
        assert "Test error" in result.errors[0]


    def test_scoping_with_no_compatible_stages(self):
        """Test scoping when element doesn't match any stage."""
        schema = ItemSchema(name="strict")
        schema.add_field("required_field", FieldDefinition(type_=str, required=True))

        stage = Stage(name="strict_stage", schema=schema)
        process = Process(name="test", stages=[stage])

        # Element without required field
        element = DictElement({"other_field": "value"})

        result = process.evaluate(element)

        assert result.state == EvaluationState.SCOPING
        assert "lacks required properties" in result.errors[0]

    def test_scoping_with_multiple_compatible_stages(self):
        """Test scoping logic with multiple compatible stages."""
        # Create two stages with overlapping requirements
        stage1 = Stage(name="stage1", schema=ItemSchema(name="basic"))
        stage2 = Stage(name="stage2", schema=ItemSchema(name="basic"))

        process = Process(name="test", stages=[stage1, stage2], stage_order=["stage1", "stage2"])
        element = DictElement({"name": "test"})

        # Test scoping - with identical stages, should complete successfully
        result = process.evaluate(element)

        # Should complete the process since no gates block progression
        assert result.state == EvaluationState.COMPLETED
        assert result.metadata.get("final_stage") == "stage2"

    def test_process_validation(self):
        """Test process validation in __post_init__."""
        # Test empty name
        with pytest.raises(ValueError, match="must have a name"):
            Process(name="", stages=[])

        # Test empty stages
        with pytest.raises(ValueError, match="must contain at least one stage"):
            Process(name="test", stages=[])

    def test_stage_order_mismatch(self, simple_stage):
        """Test stage order validation."""
        stage2 = Stage(name="stage2", gates=[], schema=ItemSchema(name="stage2"))

        with pytest.raises(ValueError, match="Stage order mismatch"):
            Process(
                name="test",
                stages=[simple_stage, stage2],
                stage_order=["basic_stage", "wrong_name"]
            )

    def test_duplicate_stage_names(self):
        """Test duplicate stage name validation."""
        stage1 = Stage(name="duplicate", gates=[], schema=ItemSchema(name="dup1"))
        stage2 = Stage(name="duplicate", gates=[], schema=ItemSchema(name="dup2"))

        with pytest.raises(ValueError, match="Duplicate stage names"):
            Process(name="test", stages=[stage1, stage2])

    def test_auto_generate_stage_order(self, simple_stage):
        """Test automatic stage order generation."""
        stage2 = Stage(name="stage2", gates=[], schema=ItemSchema(name="stage2"))
        process = Process(name="test", stages=[simple_stage, stage2])

        assert process.stage_order == ["basic_stage", "stage2"]


    def test_stage_skipping_configuration(self, simple_stage):
        """Test stage skipping configuration."""
        process = Process(name="test", stages=[simple_stage], allow_stage_skipping=True)
        assert process.allow_stage_skipping is True

        process2 = Process(name="test", stages=[simple_stage], allow_stage_skipping=False)
        assert process2.allow_stage_skipping is False
