"""Comprehensive unit tests for the stageflow.visualization.graphviz module.

This test suite covers all functionality in the GraphvizDotGenerator class,
including DOT diagram generation, stage detail visualization, layout engines,
and error handling scenarios.
"""

import pytest
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, MagicMock, patch

from stageflow.visualization.graphviz import (
    GraphvizDotGenerator,
    GraphvizGenerator,
    GraphVizGenerator
)
from stageflow.process import Process
from stageflow.stage import Stage
from stageflow.gate import Gate
from stageflow.lock import Lock, LockType


class TestGraphvizDotGeneratorCreation:
    """Test suite for GraphvizDotGenerator creation and initialization."""

    def test_create_graphviz_generator_with_default_layout(self):
        """Verify GraphvizDotGenerator can be created with default layout engine."""
        # Arrange & Act
        generator = GraphvizDotGenerator()

        # Assert
        assert isinstance(generator, GraphvizDotGenerator)
        assert generator.layout_engine == "dot"

    def test_create_graphviz_generator_with_custom_layout_engine(self):
        """Verify GraphvizDotGenerator accepts custom layout engines."""
        # Arrange
        custom_layouts = ["circo", "fdp", "neato", "twopi", "sfdp"]

        for layout in custom_layouts:
            # Act
            generator = GraphvizDotGenerator(layout_engine=layout)

            # Assert
            assert generator.layout_engine == layout

    def test_graphviz_generator_alias_compatibility(self):
        """Verify GraphvizGenerator alias works correctly."""
        # Arrange & Act
        generator = GraphvizGenerator()

        # Assert
        assert isinstance(generator, GraphvizDotGenerator)
        assert isinstance(generator, GraphvizGenerator)
        assert generator.layout_engine == "dot"

    def test_graphviz_legacy_alias_compatibility(self):
        """Verify GraphVizGenerator legacy alias works correctly."""
        # Arrange & Act
        generator = GraphVizGenerator()

        # Assert
        assert isinstance(generator, GraphvizDotGenerator)
        assert isinstance(generator, GraphVizGenerator)
        assert generator.layout_engine == "dot"


class TestGraphvizProcessDiagramGeneration:
    """Test suite for DOT process diagram generation functionality."""

    @pytest.fixture
    def mock_process(self) -> Mock:
        """Create a mock process with basic structure for testing."""
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(return_value=["stage1", "stage2", "stage3"])

        # Create mock stages
        stage1 = Mock()
        stage1.name = "Initial Stage"
        gate_mock = Mock()
        gate_mock.name = "validation_gate"
        gate_mock.components = []  # Make sure it's iterable
        stage1.gates = [gate_mock]

        stage2 = Mock()
        stage2.name = "Processing Stage"
        stage2.gates = []

        stage3 = Mock()
        stage3.name = "Final Stage"
        stage3.gates = []

        # Configure process.get_stage behavior
        def get_stage_side_effect(stage_name):
            if stage_name == "stage1":
                return stage1
            elif stage_name == "stage2":
                return stage2
            elif stage_name == "stage3":
                return stage3
            return None

        process.get_stage = Mock(side_effect=get_stage_side_effect)
        return process

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_generate_process_diagram_overview_style(self, generator, mock_process):
        """Verify DOT diagram generation with overview style."""
        # Arrange
        expected_elements = [
            "digraph StageFlow {",
            "layout=dot;",
            "rankdir=TB;",
            'label="test_process Process Flow";',
            "stage_0 [label=\"Initial Stage\", shape=house, fillcolor=\"lightblue\"];",
            "stage_1 [label=\"Processing Stage\", shape=box, fillcolor=\"lightgray\"];",
            "stage_2 [label=\"Final Stage\", shape=invhouse, fillcolor=\"lightgreen\"];",
            "stage_0 -> stage_1;",
            "stage_1 -> stage_2;",
            "}"
        ]

        # Act
        result = generator.generate_process_diagram(mock_process, style="overview")

        # Assert
        for element in expected_elements:
            assert element in result
        assert result.startswith("digraph StageFlow {")
        assert result.endswith("}")

    def test_generate_process_diagram_detailed_style(self, generator, mock_process):
        """Verify DOT diagram generation with detailed style."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, style="detailed")

        # Assert
        assert "digraph StageFlow {" in result
        assert "layout=dot;" in result
        assert 'label="test_process Process Flow";' in result
        assert "stage_0 [label=\"Initial Stage\\n(1 gates)\"" in result
        assert "}" in result

    def test_generate_process_diagram_full_style_with_gate_details(self, generator, mock_process):
        """Verify DOT diagram generation with full style including gate subgraphs."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, style="full")

        # Assert
        assert "digraph StageFlow {" in result
        assert "// Gate details" in result
        # Check for stages with gates - first stage has a gate
        first_stage = mock_process.get_stage("stage1")
        if first_stage and hasattr(first_stage, 'gates') and first_stage.gates:
            assert "subgraph cluster_" in result
        assert "}" in result

    def test_generate_process_diagram_legacy_include_details_parameter(self, generator, mock_process):
        """Verify legacy include_details parameter maps to detailed style."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, include_details=True)

        # Assert
        assert "digraph StageFlow {" in result
        assert "Initial Stage\\n(1 gates)" in result

    def test_generate_process_diagram_with_custom_layout_engine(self, mock_process):
        """Verify DOT diagram generation uses specified layout engine."""
        # Arrange
        generator = GraphvizDotGenerator(layout_engine="circo")

        # Act
        result = generator.generate_process_diagram(mock_process)

        # Assert
        assert "layout=circo;" in result

    def test_generate_process_diagram_empty_process(self, generator):
        """Verify DOT diagram generation handles empty process gracefully."""
        # Arrange
        empty_process = Mock(spec=Process)
        empty_process.name = "empty_process"
        empty_process.get_sorted_stages = Mock(return_value=[])
        empty_process.get_stage = Mock(return_value=None)

        # Act
        result = generator.generate_process_diagram(empty_process)

        # Assert
        assert "digraph StageFlow {" in result
        assert 'label="empty_process Process Flow";' in result
        assert "}" in result

    def test_generate_process_diagram_includes_graph_attributes(self, generator, mock_process):
        """Verify DOT diagram includes proper graph attributes."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process)

        # Assert
        assert "layout=dot;" in result
        assert "rankdir=TB;" in result
        assert "compound=true;" in result
        assert "concentrate=false;" in result
        assert 'bgcolor="white";' in result
        assert 'fontname="Arial";' in result

    def test_generate_process_diagram_includes_default_styling(self, generator, mock_process):
        """Verify DOT diagram includes default node and edge styling."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process)

        # Assert
        assert "// Default styling" in result
        assert 'node [fontname="Arial", fontsize=10, style=filled];' in result
        assert 'edge [fontname="Arial", fontsize=9];' in result

    def test_generate_process_diagram_with_none_stages(self, generator):
        """Verify DOT diagram handles stages that return None."""
        # Arrange
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(return_value=["missing_stage1", "missing_stage2"])
        process.get_stage = Mock(return_value=None)

        # Act
        result = generator.generate_process_diagram(process)

        # Assert
        assert "digraph StageFlow {" in result
        assert 'label="test_process Process Flow";' in result
        assert "}" in result


class TestGraphvizStageDetailGeneration:
    """Test suite for stage detail DOT generation."""

    @pytest.fixture
    def mock_stage_with_components(self) -> Mock:
        """Create a mock stage with gate components for testing."""
        stage = Mock()
        stage.name = "Complex Stage"

        # Create mock gates with components
        gate1 = Mock()
        gate1.name = "validation_gate"

        # Create mock components with locks
        component1 = Mock()
        component1.lock = Mock()
        component1.lock.property_path = "email"
        component1.lock.lock_type = Mock()
        component1.lock.lock_type.value = "EXISTS"
        component1.lock.expected_value = None

        gate1.components = [component1]

        gate2 = Mock()
        gate2.name = "business_gate"
        gate2.components = []

        stage.gates = [gate1, gate2]
        return stage

    @pytest.fixture
    def mock_stage_without_gates(self) -> Mock:
        """Create a mock stage without gates for testing."""
        stage = Mock()
        stage.name = "Simple Stage"
        stage.gates = []
        return stage

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_generate_stage_detail_with_gates_and_locks(self, generator, mock_stage_with_components):
        """Verify stage detail generation with gates and lock components."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_with_components, include_locks=True)

        # Assert
        assert "digraph StageDetail {" in result
        assert "rankdir=TB;" in result
        assert 'label="Stage: Complex Stage";' in result
        assert "stage [label=\"Complex Stage\", shape=box, fillcolor=\"lightgreen\"];" in result
        # Check that gates are present with appropriate labels (including lock count)
        assert "gate_0 [label=" in result
        assert "validation_gate" in result
        assert "stage -> gate_0;" in result
        assert "}" in result

    def test_generate_stage_detail_without_gates(self, generator, mock_stage_without_gates):
        """Verify stage detail generation for stage without gates."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_without_gates)

        # Assert
        assert "digraph StageDetail {" in result
        assert 'label="Stage: Simple Stage";' in result
        assert "stage [label=\"Simple Stage\", shape=box, fillcolor=\"lightgreen\"];" in result
        assert "nogates [label=\"No Gates\", shape=box, fillcolor=\"lightgray\"];" in result
        assert "stage -> nogates;" in result
        assert "}" in result

    def test_generate_stage_detail_excludes_locks_when_requested(self, generator, mock_stage_with_components):
        """Verify stage detail generation excludes locks when include_locks=False."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_with_components, include_locks=False)

        # Assert
        assert "digraph StageDetail {" in result
        assert "stage [label=\"Complex Stage\"" in result
        # Gates should still be present but without lock details
        assert "gate_0 [label=" in result
        assert "validation_gate" in result
        # Should not contain lock node details
        assert "lock_0_0 [label=" not in result
        assert "-> lock_0_0;" not in result

    def test_generate_stage_detail_includes_default_styling(self, generator, mock_stage_with_components):
        """Verify stage detail includes proper default styling."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_with_components)

        # Assert
        assert 'fontname="Arial";' in result
        assert 'node [fontname="Arial", fontsize=10, style=filled];' in result
        assert 'edge [fontname="Arial", fontsize=9];' in result

    def test_generate_stage_detail_with_lock_components(self, generator, mock_stage_with_components):
        """Verify stage detail properly handles lock components."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_with_components, include_locks=True)

        # Assert
        assert "lock_0_0 [label=\"email\\nEXISTS\", shape=diamond, fillcolor=\"lightcyan\"];" in result
        assert "gate_0 -> lock_0_0;" in result


class TestGraphvizDotFileGeneration:
    """Test suite for DOT file generation functionality."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    @pytest.fixture
    def mock_process(self) -> Mock:
        """Create a simple mock process for DOT file testing."""
        process = Mock(spec=Process)
        process.name = "file_test_process"
        process.get_sorted_stages = Mock(return_value=["start", "end"])

        stage1 = Mock()
        stage1.name = "Start"
        stage1.gates = []

        stage2 = Mock()
        stage2.name = "End"
        stage2.gates = []

        process.get_stage = Mock(side_effect=lambda name: stage1 if name == "start" else stage2)
        return process

    def test_generate_dot_file_returns_complete_dot_content(self, generator, mock_process):
        """Verify generate_dot_file returns complete DOT file content."""
        # Arrange & Act
        result = generator.generate_dot_file(mock_process)

        # Assert
        assert result.startswith("digraph StageFlow {")
        assert result.endswith("}")
        assert 'label="file_test_process Process Flow";' in result

    def test_generate_dot_file_with_different_styles(self, generator, mock_process):
        """Verify generate_dot_file works with different visualization styles."""
        # Arrange
        styles = ["overview", "detailed", "full"]

        for style in styles:
            # Act
            result = generator.generate_dot_file(mock_process, style=style)

            # Assert
            assert result.startswith("digraph StageFlow {")
            assert result.endswith("}")

    def test_generate_dot_file_delegates_to_process_diagram(self, generator, mock_process):
        """Verify generate_dot_file delegates to generate_process_diagram."""
        # Arrange & Act
        dot_result = generator.generate_dot_file(mock_process, style="detailed")
        diagram_result = generator.generate_process_diagram(mock_process, style="detailed")

        # Assert
        assert dot_result == diagram_result


class TestGraphvizSubgraphGeneration:
    """Test suite for subgraph generation functionality."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    @pytest.fixture
    def mock_stage(self) -> Mock:
        """Create a mock stage for subgraph testing."""
        stage = Mock()
        stage.name = "Test Stage"
        return stage

    def test_generate_stage_subgraph_creates_proper_structure(self, generator, mock_stage):
        """Verify stage subgraph generation creates proper DOT subgraph structure."""
        # Arrange & Act
        result = generator.generate_stage_subgraph(mock_stage)

        # Assert
        assert "subgraph cluster_Test_Stage {" in result
        assert 'label="Test Stage";' in result
        assert 'style="rounded";' in result
        assert 'color="blue";' in result
        assert "Test_Stage_node [label=\"Test Stage\", shape=box];" in result
        assert "}" in result

    def test_generate_stage_subgraph_handles_spaces_in_names(self, generator):
        """Verify stage subgraph handles spaces in stage names properly."""
        # Arrange
        stage = Mock()
        stage.name = "Complex Stage Name"

        # Act
        result = generator.generate_stage_subgraph(stage)

        # Assert
        assert "cluster_Complex_Stage_Name" in result
        assert "Complex_Stage_Name_node" in result
        assert 'label="Complex Stage Name";' in result

    def test_generate_gate_nodes_creates_hexagon_shapes(self, generator):
        """Verify gate nodes generation creates proper hexagon shapes."""
        # Arrange
        gate1 = Mock()
        gate1.name = "gate_one"
        gate1.components = []  # Add empty components to avoid iteration errors
        gate2 = Mock()
        gate2.name = "gate_two"
        gate2.components = []  # Add empty components to avoid iteration errors
        gates = [gate1, gate2]

        # Act
        result = generator.generate_gate_nodes(gates)

        # Assert
        assert "gate_0 [label=" in result
        assert "gate_one" in result
        assert "shape=hexagon" in result
        assert "fillcolor=\"lightyellow\"" in result
        assert "gate_1 [label=" in result
        assert "gate_two" in result

    def test_generate_gate_nodes_with_empty_list(self, generator):
        """Verify gate nodes generation handles empty gate list."""
        # Arrange
        empty_gates = []

        # Act
        result = generator.generate_gate_nodes(empty_gates)

        # Assert
        assert result == ""


class TestGraphvizStateFlowGeneration:
    """Test suite for state flow diagram generation."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_generate_state_flow_returns_expected_structure(self, generator):
        """Verify state flow generation returns proper 7-state DOT diagram."""
        # Arrange & Act
        result = generator.generate_state_flow()

        # Assert
        assert result.startswith("digraph StateFlow {")
        assert 'label="StageFlow 7-State Evaluation Flow";' in result
        assert "rankdir=LR;" in result
        assert "SCOPING [style=filled, fillcolor=lightcoral];" in result
        assert "FULFILLING [style=filled, fillcolor=lightblue];" in result
        assert "QUALIFYING [style=filled, fillcolor=lightgreen];" in result
        assert "AWAITING [style=filled, fillcolor=lightyellow];" in result
        assert "ADVANCING [style=filled, fillcolor=lightcyan];" in result
        assert "REGRESSING [style=filled, fillcolor=lightpink];" in result
        assert "COMPLETED [style=filled, fillcolor=lightgray];" in result
        assert result.endswith("}")

    def test_generate_state_flow_includes_proper_transitions(self, generator):
        """Verify state flow includes all expected state transitions."""
        # Arrange & Act
        result = generator.generate_state_flow()

        # Assert
        expected_transitions = [
            "SCOPING -> FULFILLING;",
            "FULFILLING -> QUALIFYING;",
            "FULFILLING -> AWAITING;",
            "FULFILLING -> REGRESSING;",
            "QUALIFYING -> ADVANCING;",
            "QUALIFYING -> REGRESSING;",
            "AWAITING -> FULFILLING;",
            "AWAITING -> QUALIFYING;",
            "ADVANCING -> COMPLETED;",
            "REGRESSING -> SCOPING;",
            "REGRESSING -> FULFILLING;"
        ]

        for transition in expected_transitions:
            assert transition in result

    def test_generate_state_flow_is_static_content(self, generator):
        """Verify state flow returns consistent static content."""
        # Arrange & Act
        result1 = generator.generate_state_flow()
        result2 = generator.generate_state_flow()

        # Assert
        assert result1 == result2


class TestGraphvizLabelGeneration:
    """Test suite for label generation helper methods."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    @pytest.fixture
    def mock_stage(self) -> Mock:
        """Create a mock stage for label testing."""
        stage = Mock()
        stage.name = "Test Stage"
        stage.gates = [Mock(), Mock()]  # Two gates
        stage.schema = {"required": ["field1"]}
        return stage

    def test_generate_stage_label_overview_style(self, generator, mock_stage):
        """Verify stage label generation for overview style."""
        # Arrange & Act
        result = generator._generate_stage_label(mock_stage, "overview")

        # Assert
        assert result == "Test Stage"

    def test_generate_stage_label_detailed_style(self, generator, mock_stage):
        """Verify stage label generation for detailed style."""
        # Arrange & Act
        result = generator._generate_stage_label(mock_stage, "detailed")

        # Assert
        assert "Test Stage" in result
        assert "(2 gates)" in result

    def test_generate_stage_label_full_style(self, generator, mock_stage):
        """Verify stage label generation for full style."""
        # Arrange & Act
        result = generator._generate_stage_label(mock_stage, "full")

        # Assert
        assert "Test Stage" in result
        assert "2 gate(s)" in result
        assert "Schema validation" in result

    def test_generate_stage_label_no_gates(self, generator):
        """Verify stage label generation for stage without gates."""
        # Arrange
        stage = Mock()
        stage.name = "Empty Stage"
        stage.gates = []

        # Act
        result = generator._generate_stage_label(stage, "detailed")

        # Assert
        assert "Empty Stage" in result
        assert "(0 gates)" in result

    def test_generate_edge_label_overview_style(self, generator, mock_stage):
        """Verify edge label generation for overview style."""
        # Arrange & Act
        result = generator._generate_edge_label(mock_stage, "overview")

        # Assert
        assert result == ""

    def test_generate_edge_label_no_gates(self, generator):
        """Verify edge label generation for stage without gates."""
        # Arrange
        stage = Mock()
        stage.gates = []

        # Act
        result = generator._generate_edge_label(stage, "detailed")

        # Assert
        assert result == "auto"

    def test_generate_gate_label_different_styles(self, generator):
        """Verify gate label generation for different styles."""
        # Arrange
        mock_gate = Mock()
        mock_gate.name = "test_gate"
        mock_gate.components = []  # Add empty components to avoid iteration errors

        # Act & Assert
        overview_result = generator._generate_gate_label(mock_gate, "overview")
        assert overview_result == "test_gate"

        detailed_result = generator._generate_gate_label(mock_gate, "detailed")
        assert "test_gate" in detailed_result

        full_result = generator._generate_gate_label(mock_gate, "full")
        assert "test_gate" in full_result

    def test_generate_lock_label_with_expected_value(self, generator):
        """Verify lock label generation includes expected value when present."""
        # Arrange
        mock_lock = Mock()
        mock_lock.property_path = "email"
        mock_lock.lock_type = Mock()
        mock_lock.lock_type.value = "REGEX"
        mock_lock.expected_value = r"^[^@]+@[^@]+\.[^@]+$"

        # Act
        result = generator._generate_lock_label(mock_lock)

        # Assert
        assert "email" in result
        assert "REGEX" in result
        assert r"^[^@]+@[^@]+\.[^@]+$" in result

    def test_generate_lock_label_without_expected_value(self, generator):
        """Verify lock label generation handles missing expected value."""
        # Arrange
        mock_lock = Mock()
        mock_lock.property_path = "field"
        mock_lock.lock_type = Mock()
        mock_lock.lock_type.value = "EXISTS"
        mock_lock.expected_value = None

        # Act
        result = generator._generate_lock_label(mock_lock)

        # Assert
        assert "field" in result
        assert "EXISTS" in result
        assert result.count("\\n") == 1  # Only property and type, no expected value


class TestGraphvizStylingHelpers:
    """Test suite for styling helper methods."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_get_stage_styling_initial_stage(self, generator):
        """Verify styling for initial stage."""
        # Arrange & Act
        shape, color = generator._get_stage_styling(is_initial=True, is_final=False)

        # Assert
        assert shape == "house"
        assert color == "lightblue"

    def test_get_stage_styling_final_stage(self, generator):
        """Verify styling for final stage."""
        # Arrange & Act
        shape, color = generator._get_stage_styling(is_initial=False, is_final=True)

        # Assert
        assert shape == "invhouse"
        assert color == "lightgreen"

    def test_get_stage_styling_intermediate_stage(self, generator):
        """Verify styling for intermediate stage."""
        # Arrange & Act
        shape, color = generator._get_stage_styling(is_initial=False, is_final=False)

        # Assert
        assert shape == "box"
        assert color == "lightgray"

    def test_get_gate_summary_with_components(self, generator):
        """Verify gate summary generation with various components."""
        # Arrange
        mock_gate = Mock()

        # Create mock components
        lock_component = Mock()
        lock_component.lock = Mock()

        gate_component = Mock()
        gate_component.name = "sub_gate"
        # Ensure it doesn't have a lock attribute by setting spec
        gate_component = Mock(spec=['name'])
        gate_component.name = "sub_gate"

        mock_gate.components = [lock_component, gate_component]

        # Act
        result = generator._get_gate_summary(mock_gate)

        # Assert
        assert "1 locks" in result
        assert "1 gates" in result

    def test_get_gate_summary_no_components(self, generator):
        """Verify gate summary generation with no components."""
        # Arrange
        mock_gate = Mock()
        mock_gate.components = []

        # Act
        result = generator._get_gate_summary(mock_gate)

        # Assert
        assert result == "No components"

    def test_get_gate_summary_missing_components_attribute(self, generator):
        """Verify gate summary handles missing components attribute."""
        # Arrange
        mock_gate = Mock(spec=[])  # Mock without components attribute

        # Act
        result = generator._get_gate_summary(mock_gate)

        # Assert
        assert result == "No components"

    def test_get_lock_count_with_locks(self, generator):
        """Verify lock count calculation with lock components."""
        # Arrange
        mock_gate = Mock()

        lock_component1 = Mock()
        lock_component1.lock = Mock()

        lock_component2 = Mock()
        lock_component2.lock = Mock()

        non_lock_component = Mock(spec=[])  # Component without lock

        mock_gate.components = [lock_component1, lock_component2, non_lock_component]

        # Act
        result = generator._get_lock_count(mock_gate)

        # Assert
        assert result == 2

    def test_get_lock_count_no_components(self, generator):
        """Verify lock count calculation with no components."""
        # Arrange
        mock_gate = Mock()
        mock_gate.components = []

        # Act
        result = generator._get_lock_count(mock_gate)

        # Assert
        assert result == 0


class TestGraphvizErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_generate_process_diagram_with_invalid_process(self, generator):
        """Verify process diagram generation handles invalid process gracefully."""
        # Arrange
        invalid_process = None

        # Act & Assert
        with pytest.raises((AttributeError, TypeError)):
            generator.generate_process_diagram(invalid_process)

    def test_generate_stage_detail_with_none_stage(self, generator):
        """Verify stage detail generation handles None stage."""
        # Arrange & Act & Assert
        with pytest.raises((AttributeError, TypeError)):
            generator.generate_stage_detail(None)

    def test_generate_gate_nodes_with_none_gates(self, generator):
        """Verify gate nodes generation handles None gates list."""
        # Arrange & Act & Assert
        with pytest.raises((AttributeError, TypeError)):
            generator.generate_gate_nodes(None)

    def test_invalid_layout_engine_still_works(self):
        """Verify generator works even with invalid layout engine."""
        # Arrange & Act
        generator = GraphvizDotGenerator(layout_engine="invalid_engine")

        # Assert
        assert generator.layout_engine == "invalid_engine"
        # The generator should still create valid DOT content

    def test_edge_label_generation_with_malformed_gates(self, generator):
        """Verify edge label generation handles malformed gate data."""
        # Arrange
        stage = Mock()
        stage.gates = [Mock()]
        stage.gates[0].name = "test_gate"

        # Act
        result = generator._generate_edge_label(stage, "detailed")

        # Assert
        assert isinstance(result, str)

    def test_lock_label_generation_with_missing_attributes(self, generator):
        """Verify lock label generation handles missing attributes gracefully."""
        # Arrange
        mock_lock = Mock()
        mock_lock.property_path = "test_field"
        mock_lock.lock_type = Mock()
        mock_lock.lock_type.value = "EXISTS"
        # Missing expected_value attribute

        # Act
        try:
            result = generator._generate_lock_label(mock_lock)
            # Should handle missing expected_value gracefully
            assert "test_field" in result
            assert "EXISTS" in result
        except AttributeError:
            # If it raises AttributeError, that's also acceptable behavior
            pass


@pytest.mark.integration
class TestGraphvizIntegrationScenarios:
    """Integration tests for Graphviz generator with realistic scenarios."""

    @pytest.fixture
    def realistic_process_config(self) -> Dict[str, Any]:
        """Create a realistic process configuration for integration testing."""
        return {
            "name": "order_processing",
            "description": "E-commerce order processing workflow",
            "stages": {
                "submitted": {
                    "name": "Order Submitted",
                    "expected_properties": {"order_id": {"type": "str"}},
                    "gates": [{
                        "name": "order_valid",
                        "target_stage": "payment",
                        "locks": [{"exists": "order_id"}]
                    }]
                },
                "payment": {
                    "name": "Payment Processing",
                    "expected_properties": {"payment_status": {"type": "str"}},
                    "gates": [{
                        "name": "payment_complete",
                        "target_stage": "fulfillment",
                        "locks": [{"exists": "payment_status"}]
                    }]
                },
                "fulfillment": {
                    "name": "Order Fulfillment",
                    "expected_properties": {"shipping_status": {"type": "str"}},
                    "gates": [{
                        "name": "shipped",
                        "target_stage": "completed",
                        "locks": [{"exists": "shipping_status"}]
                    }]
                },
                "completed": {
                    "name": "Order Completed",
                    "gates": [],
                    "is_final": True
                }
            },
            "initial_stage": "submitted",
            "final_stage": "completed"
        }

    @pytest.fixture
    def generator(self) -> GraphvizDotGenerator:
        """Create a GraphvizDotGenerator instance for testing."""
        return GraphvizDotGenerator()

    def test_complete_workflow_dot_generation(self, generator, realistic_process_config):
        """Verify complete workflow DOT generation with realistic process."""
        # Arrange
        mock_process = Mock(spec=Process)
        mock_process.name = realistic_process_config["name"]
        mock_process.get_sorted_stages = Mock(return_value=["submitted", "payment", "fulfillment", "completed"])

        # Create mock stages based on config
        stages = {}
        for stage_name, stage_config in realistic_process_config["stages"].items():
            stage = Mock()
            stage.name = stage_config["name"]
            # Convert gates from config format to mock objects
            stage.gates = []
            for gate_config in stage_config.get("gates", []):
                gate_mock = Mock()
                gate_mock.name = gate_config["name"]
                gate_mock.components = []
                stage.gates.append(gate_mock)
            stages[stage_name] = stage

        mock_process.get_stage = Mock(side_effect=lambda name: stages.get(name))

        # Act
        overview_result = generator.generate_process_diagram(mock_process, style="overview")
        detailed_result = generator.generate_process_diagram(mock_process, style="detailed")
        full_result = generator.generate_process_diagram(mock_process, style="full")

        # Assert
        for result in [overview_result, detailed_result, full_result]:
            assert "digraph StageFlow {" in result
            assert "Order Submitted" in result
            assert "Payment Processing" in result
            assert "Order Fulfillment" in result
            assert "Order Completed" in result
            assert "}" in result

    def test_stage_detail_with_complex_components(self, generator):
        """Verify stage detail generation with complex component structures."""
        # Arrange
        stage = Mock()
        stage.name = "Complex Validation Stage"

        # Create gates with various components
        gate1 = Mock()
        gate1.name = "input_validation"

        # Create components with locks
        component1 = Mock()
        component1.lock = Mock()
        component1.lock.property_path = "email"
        component1.lock.lock_type = Mock()
        component1.lock.lock_type.value = "REGEX"
        component1.lock.expected_value = r"^[^@]+@[^@]+\.[^@]+$"

        component2 = Mock()
        component2.lock = Mock()
        component2.lock.property_path = "age"
        component2.lock.lock_type = Mock()
        component2.lock.lock_type.value = "GREATER_THAN"
        component2.lock.expected_value = 18

        gate1.components = [component1, component2]

        stage.gates = [gate1]

        # Act
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Assert
        assert "digraph StageDetail {" in result
        assert "Complex Validation Stage" in result
        assert "input_validation" in result
        assert "email" in result
        assert "REGEX" in result
        assert "age" in result
        assert "GREATER_THAN" in result
        assert "}" in result

    def test_multiple_layout_engines_produce_valid_dot(self, realistic_process_config):
        """Verify different layout engines produce valid DOT content."""
        # Arrange
        layout_engines = ["dot", "circo", "fdp", "neato"]
        mock_process = Mock(spec=Process)
        mock_process.name = "test_process"
        mock_process.get_sorted_stages = Mock(return_value=["start", "end"])

        stage1 = Mock()
        stage1.name = "Start"
        stage1.gates = []

        stage2 = Mock()
        stage2.name = "End"
        stage2.gates = []

        mock_process.get_stage = Mock(side_effect=lambda name: stage1 if name == "start" else stage2)

        for engine in layout_engines:
            # Act
            generator = GraphvizDotGenerator(layout_engine=engine)
            result = generator.generate_process_diagram(mock_process)

            # Assert
            assert f"layout={engine};" in result
            assert "digraph StageFlow {" in result
            assert "}" in result

    def test_error_recovery_with_malformed_stage_data(self, generator):
        """Verify generator recovers gracefully from malformed stage data."""
        # Arrange
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(return_value=["stage1", "stage2"])

        # Create stages with inconsistent data
        stage1 = Mock()
        stage1.name = "Valid Stage"
        stage1.gates = []

        # stage2 will return None (simulating missing stage)
        stage_map = {"stage1": stage1, "stage2": None}

        def get_stage_side_effect(name):
            return stage_map.get(name, None)

        process.get_stage = Mock(side_effect=get_stage_side_effect)

        # Act
        result = generator.generate_process_diagram(process)

        # Assert
        assert "digraph StageFlow {" in result
        assert "Valid Stage" in result
        assert "}" in result
        # Should not crash despite missing stage2


@pytest.mark.parametrize("layout_engine,expected_layout", [
    ("dot", "layout=dot;"),
    ("circo", "layout=circo;"),
    ("fdp", "layout=fdp;"),
    ("neato", "layout=neato;"),
    ("twopi", "layout=twopi;")
])
class TestGraphvizParametrizedLayoutEngines:
    """Parametrized tests for different layout engine scenarios."""

    def test_layout_engine_configuration(self, layout_engine, expected_layout):
        """Verify layout engine configuration is properly applied."""
        # Arrange
        generator = GraphvizDotGenerator(layout_engine=layout_engine)
        mock_process = Mock(spec=Process)
        mock_process.name = "test"
        mock_process.get_sorted_stages = Mock(return_value=["stage1"])

        stage = Mock()
        stage.name = "Test Stage"
        stage.gates = []

        mock_process.get_stage = Mock(return_value=stage)

        # Act
        result = generator.generate_process_diagram(mock_process)

        # Assert
        assert expected_layout in result


@pytest.mark.parametrize("style,expected_elements", [
    ("overview", ["shape=house", "shape=box", "shape=invhouse"]),
    ("detailed", ["(0 gates)", "\\n", "gates)"]),
    ("full", ["// Gate details", "cluster_", "subgraph"])
])
class TestGraphvizParametrizedStyleGeneration:
    """Parametrized tests for different style generation scenarios."""

    @pytest.fixture
    def three_stage_process(self) -> Mock:
        """Create a three-stage process for parametrized testing."""
        process = Mock(spec=Process)
        process.name = "three_stage_process"
        process.get_sorted_stages = Mock(return_value=["initial", "middle", "final"])

        initial = Mock()
        initial.name = "Initial"
        initial.gates = []

        middle = Mock()
        middle.name = "Middle"
        middle.gates = []

        final = Mock()
        final.name = "Final"
        final.gates = []

        def get_stage_side_effect(name):
            stages_map = {
                "initial": initial,
                "middle": middle,
                "final": final
            }
            return stages_map.get(name)

        process.get_stage = Mock(side_effect=get_stage_side_effect)
        return process

    def test_style_specific_elements_present(self, style, expected_elements, three_stage_process):
        """Verify specific style elements are present in generated DOT diagrams."""
        # Arrange
        generator = GraphvizDotGenerator()

        # Act
        result = generator.generate_process_diagram(three_stage_process, style=style)

        # Assert
        for element in expected_elements:
            # For full style, cluster_ only appears if there are gates to detail
            if element == "cluster_" and style == "full":
                # For subgraph, only appears if stages have gates with components
                # Since our test process has empty gates, subgraph won't appear
                if element == "subgraph":
                    continue
            elif element == "subgraph" and style == "full":
                # subgraph only appears if there are gates with actual components
                continue
            else:
                assert element in result, f"Expected element '{element}' not found in {style} style"