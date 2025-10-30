"""Comprehensive unit tests for the stageflow.visualization.mermaid module.

This test suite covers all functionality in the MermaidDiagramGenerator class,
including process diagram generation, stage detail visualization, gate flowcharts,
and error handling scenarios.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from stageflow.process import Process
from stageflow.visualization.mermaid import MermaidDiagramGenerator, MermaidGenerator


class TestMermaidDiagramGeneratorCreation:
    """Test suite for MermaidDiagramGenerator creation and initialization."""

    def test_create_mermaid_generator_with_default_settings(self):
        """Verify MermaidDiagramGenerator can be created with default settings."""
        # Arrange & Act
        generator = MermaidDiagramGenerator()

        # Assert
        assert isinstance(generator, MermaidDiagramGenerator)
        assert generator.node_counter == 0

    def test_mermaid_generator_alias_compatibility(self):
        """Verify MermaidGenerator alias works correctly."""
        # Arrange & Act
        generator = MermaidGenerator()

        # Assert
        assert isinstance(generator, MermaidDiagramGenerator)
        assert isinstance(generator, MermaidGenerator)
        assert generator.node_counter == 0


class TestMermaidProcessDiagramGeneration:
    """Test suite for process diagram generation functionality."""

    @pytest.fixture
    def mock_process(self) -> Mock:
        """Create a mock process with basic structure for testing."""
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(return_value=["stage1", "stage2", "stage3"])

        # Create mock initial and final stages
        initial_stage = Mock()
        initial_stage._id = "stage1"
        initial_stage.name = "First Stage"
        process.initial_stage = initial_stage

        final_stage = Mock()
        final_stage._id = "stage3"
        final_stage.name = "Final Stage"
        process.final_stage = final_stage

        # Create mock stages
        stage1 = Mock()
        stage1.name = "First Stage"
        gate1 = Mock()
        gate1.name = "gate1"
        gate1.target_stage = "stage2"
        stage1.gates = [gate1]  # List of gate objects

        stage2 = Mock()
        stage2.name = "Second Stage"
        gate2 = Mock()
        gate2.name = "gate2"
        gate2.target_stage = "stage3"
        stage2.gates = [gate2]  # List of gate objects

        stage3 = Mock()
        stage3.name = "Final Stage"
        stage3.gates = []  # No gates for final stage

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
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    def test_generate_process_diagram_overview_style(self, generator, mock_process):
        """Verify process diagram generation with overview style."""
        # Arrange
        expected_elements = [
            "```mermaid",
            "flowchart TD",
            "S0[First Stage]",
            "S1[Second Stage]",
            "S2[Final Stage]",
            "S0 --> S1",
            "S1 --> S2",
            "```",
        ]

        # Act
        result = generator.generate_process_diagram(mock_process, style="overview")

        # Assert
        for element in expected_elements:
            assert element in result
        assert result.startswith("```mermaid")
        assert result.endswith("```")

    def test_generate_process_diagram_detailed_style(self, generator, mock_process):
        """Verify process diagram generation with detailed style."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, style="detailed")

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert 'subgraph "Process: test_process"' in result
        assert "direction TB" in result
        assert "```" in result

    def test_generate_process_diagram_full_style(self, generator, mock_process):
        """Verify process diagram generation with full style including gate details."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, style="full")

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert 'subgraph "Process: test_process"' in result
        assert "%% Gate Details" in result
        assert "```" in result

    def test_generate_process_diagram_legacy_include_details_parameter(
        self, generator, mock_process
    ):
        """Verify legacy include_details parameter maps to detailed style."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, include_details=True)

        # Assert
        assert "```mermaid" in result
        assert 'subgraph "Process: test_process"' in result

    def test_generate_process_diagram_empty_process(self, generator):
        """Verify process diagram generation handles empty process gracefully."""
        # Arrange
        empty_process = Mock(spec=Process)
        empty_process.name = "empty_process"
        empty_process.get_sorted_stages = Mock(return_value=[])
        empty_process.get_stage = Mock(return_value=None)

        # Act
        result = generator.generate_process_diagram(empty_process)

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "```" in result

    def test_generate_process_diagram_includes_styling(self, generator, mock_process):
        """Verify process diagram includes comprehensive styling."""
        # Arrange & Act
        result = generator.generate_process_diagram(mock_process, style="detailed")

        # Assert
        assert "%% Styling" in result
        assert "classDef initial" in result
        assert "classDef final" in result
        assert "classDef stage" in result

    def test_generate_process_diagram_with_none_stages(self, generator):
        """Verify process diagram handles stages that return None."""
        # Arrange
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(
            return_value=["missing_stage1", "missing_stage2"]
        )
        process.get_stage = Mock(return_value=None)

        # Act
        result = generator.generate_process_diagram(process)

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "```" in result


class TestMermaidStageDetailGeneration:
    """Test suite for stage detail diagram generation."""

    @pytest.fixture
    def mock_stage_with_gates(self) -> Mock:
        """Create a mock stage with gates for testing."""
        stage = Mock()
        stage.name = "Test Stage"

        # Create mock gates
        gate1 = Mock()
        gate1.name = "validation_gate"
        gate1.locks = []

        gate2 = Mock()
        gate2.name = "completion_gate"
        gate2.locks = []

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
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    def test_generate_stage_detail_with_gates_and_locks(
        self, generator, mock_stage_with_gates
    ):
        """Verify stage detail generation with gates and locks."""
        # Arrange
        mock_lock = Mock()
        mock_lock.property = "email"
        mock_lock.type = Mock()
        mock_lock.type.value = "EXISTS"
        mock_lock.expected_value = None

        mock_stage_with_gates.gates[0].locks = [mock_lock]

        # Act
        result = generator.generate_stage_detail(
            mock_stage_with_gates, include_locks=True
        )

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "Stage[Test Stage]" in result
        assert "G0[validation_gate<br/>validation gate]" in result
        assert "G1[completion_gate<br/>validation gate]" in result
        assert "```" in result

    def test_generate_stage_detail_without_gates(
        self, generator, mock_stage_without_gates
    ):
        """Verify stage detail generation for stage without gates."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_without_gates)

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "Stage[Simple Stage]" in result
        assert "Stage --> NoGates[No Gates Defined]" in result
        assert "class NoGates nogate" in result
        assert "```" in result

    def test_generate_stage_detail_excludes_locks_when_requested(
        self, generator, mock_stage_with_gates
    ):
        """Verify stage detail generation excludes locks when include_locks=False."""
        # Arrange
        mock_lock = Mock()
        mock_lock.property = "email"
        mock_lock.type = Mock()
        mock_lock.type.value = "EXISTS"

        mock_stage_with_gates.gates[0].locks = [mock_lock]

        # Act
        result = generator.generate_stage_detail(
            mock_stage_with_gates, include_locks=False
        )

        # Assert
        assert "```mermaid" in result
        assert "Stage[Test Stage]" in result
        assert "G0[validation_gate<br/>validation gate]" in result
        # Should not contain lock node details in the diagram structure
        assert "L0_0[" not in result
        # Should not have lock connections
        assert "G0 --> L0_0" not in result

    def test_generate_stage_detail_includes_styling(
        self, generator, mock_stage_with_gates
    ):
        """Verify stage detail includes comprehensive styling classes."""
        # Arrange & Act
        result = generator.generate_stage_detail(mock_stage_with_gates)

        # Assert
        assert "%% Styling" in result
        assert "classDef stage fill:#f3e5f5" in result
        assert "classDef gate fill:#e8f5e8" in result
        assert "classDef lock fill:#fff3e0" in result
        assert "class Stage stage" in result
        assert "class G0 gate" in result


class TestMermaidGateFlowchartGeneration:
    """Test suite for gate flowchart generation."""

    @pytest.fixture
    def mock_gates(self) -> list[Mock]:
        """Create mock gates for testing."""
        gate1 = Mock()
        gate1.name = "input_validation"

        gate2 = Mock()
        gate2.name = "business_rules"

        gate3 = Mock()
        gate3.name = "final_check"

        return [gate1, gate2, gate3]

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    def test_generate_gate_flowchart_with_multiple_gates(self, generator, mock_gates):
        """Verify gate flowchart generation with multiple gates."""
        # Arrange & Act
        result = generator.generate_gate_flowchart(mock_gates)

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "Start([Gate Evaluation])" in result
        assert "G0[input_validation<br/>gate]" in result
        assert "G1[business_rules<br/>gate]" in result
        assert "G2[final_check<br/>gate]" in result
        assert "Start --> G0" in result
        assert "G0 --> G1" in result
        assert "G1 --> G2" in result
        assert "G2 --> End" in result
        assert "End([Evaluation Complete])" in result
        assert "```" in result

    def test_generate_gate_flowchart_with_empty_gates(self, generator):
        """Verify gate flowchart generation handles empty gate list."""
        # Arrange
        empty_gates = []

        # Act
        result = generator.generate_gate_flowchart(empty_gates)

        # Assert
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "Start([Gate Evaluation])" in result
        assert "Start --> NoGates[No Gates Defined]" in result
        assert "NoGates --> End" in result
        assert "End([Evaluation Complete])" in result
        assert "class NoGates nogate" in result
        assert "```" in result

    def test_generate_gate_flowchart_with_single_gate(self, generator):
        """Verify gate flowchart generation with single gate."""
        # Arrange
        single_gate = Mock()
        single_gate.name = "only_gate"
        gates = [single_gate]

        # Act
        result = generator.generate_gate_flowchart(gates)

        # Assert
        assert "```mermaid" in result
        assert "Start --> G0" in result
        assert "G0[only_gate<br/>gate]" in result
        assert "G0 --> End" in result
        assert "```" in result

    def test_generate_gate_flowchart_includes_styling(self, generator, mock_gates):
        """Verify gate flowchart includes proper styling."""
        # Arrange & Act
        result = generator.generate_gate_flowchart(mock_gates)

        # Assert
        assert "%% Styling" in result
        assert "classDef startEnd fill:#e1f5fe" in result
        assert "classDef gate fill:#e8f5e8" in result
        assert "class Start,End startEnd" in result
        assert "class G0 gate" in result


class TestMermaidStateFlowGeneration:
    """Test suite for state flow diagram generation."""

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    def test_generate_state_flow_returns_expected_structure(self, generator):
        """Verify state flow generation returns proper 7-state diagram."""
        # Arrange & Act
        result = generator.generate_state_flow()

        # Assert
        assert result.startswith("```mermaid")
        assert "flowchart TD" in result
        assert "SCOPING[Scoping]" in result
        assert "FULFILLING[Fulfilling]" in result
        assert "QUALIFYING[Qualifying]" in result
        assert "AWAITING[Awaiting]" in result
        assert "ADVANCING[Advancing]" in result
        assert "REGRESSING[Regressing]" in result
        assert "COMPLETED[Completed]" in result
        assert result.endswith("```")

    def test_generate_state_flow_includes_proper_transitions(self, generator):
        """Verify state flow includes all expected state transitions."""
        # Arrange & Act
        result = generator.generate_state_flow()

        # Assert
        expected_transitions = [
            "SCOPING --> FULFILLING",
            "FULFILLING --> QUALIFYING",
            "FULFILLING --> AWAITING",
            "QUALIFYING --> ADVANCING",
            "AWAITING --> FULFILLING",
            "AWAITING --> QUALIFYING",
            "ADVANCING --> COMPLETED",
            "QUALIFYING --> REGRESSING",
            "FULFILLING --> REGRESSING",
            "REGRESSING --> SCOPING",
            "REGRESSING --> FULFILLING",
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


class TestMermaidLabelGeneration:
    """Test suite for label generation helper methods."""

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

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
        assert "2 gate(s)" in result

    def test_generate_stage_label_full_style(self, generator, mock_stage):
        """Verify stage label generation for full style."""
        # Arrange & Act
        result = generator._generate_stage_label(mock_stage, "full")

        # Assert
        assert "Test Stage" in result
        assert "2 gate(s)" in result
        assert "Schema required" in result

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
        assert "No gates" in result

    def test_generate_transition_label_overview_style(self, generator, mock_stage):
        """Verify transition label generation for overview style."""
        # Arrange & Act
        result = generator._generate_transition_label(mock_stage, "overview")

        # Assert
        assert result == ""

    def test_generate_transition_label_no_gates(self, generator):
        """Verify transition label generation for stage without gates."""
        # Arrange
        stage = Mock()
        stage.gates = []

        # Act
        result = generator._generate_transition_label(stage, "detailed")

        # Assert
        assert result == "auto"

    def test_generate_gate_label_different_styles(self, generator):
        """Verify gate label generation for different styles."""
        # Arrange
        mock_gate = Mock()
        mock_gate.name = "test_gate"

        # Act & Assert
        overview_result = generator._generate_gate_label(mock_gate, "overview")
        assert overview_result == "test_gate"

        detailed_result = generator._generate_gate_label(mock_gate, "detailed")
        assert "test_gate" in detailed_result
        assert "gate" in detailed_result

        full_result = generator._generate_gate_label(mock_gate, "full")
        assert "test_gate" in full_result
        assert "validation gate" in full_result

    def test_generate_gate_label_string_input(self, generator):
        """Verify gate label generation handles string input."""
        # Arrange & Act
        result = generator._generate_gate_label("string_gate", "overview")

        # Assert
        assert result == "string_gate"


class TestMermaidStylingGeneration:
    """Test suite for styling generation functionality."""

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    @pytest.fixture
    def mock_process_for_styling(self) -> Mock:
        """Create a mock process for styling tests."""
        process = Mock(spec=Process)
        process.name = "styling_process"
        process.get_sorted_stages = Mock(return_value=["initial", "middle", "final"])

        # Create mock initial and final stages
        initial_stage = Mock()
        initial_stage._id = "initial"
        initial_stage.name = "Initial Stage"
        process.initial_stage = initial_stage

        final_stage = Mock()
        final_stage._id = "final"
        final_stage.name = "Final Stage"
        process.final_stage = final_stage

        return process

    def test_generate_styling_includes_all_style_classes(
        self, generator, mock_process_for_styling
    ):
        """Verify styling generation includes all required style classes."""
        # Arrange
        stage_nodes = {"initial": "S0", "middle": "S1", "final": "S2"}

        # Act
        result = generator._generate_styling(
            stage_nodes, mock_process_for_styling, "detailed"
        )

        # Assert
        styling_lines = "\n".join(result)
        assert "%% Styling" in styling_lines
        assert "classDef initial" in styling_lines
        assert "classDef final" in styling_lines
        assert "classDef stage" in styling_lines
        assert "classDef gate" in styling_lines
        assert "classDef lock" in styling_lines

    def test_generate_styling_applies_stage_classifications(
        self, generator, mock_process_for_styling
    ):
        """Verify styling correctly classifies initial, middle, and final stages."""
        # Arrange
        stage_nodes = {"initial": "S0", "middle": "S1", "final": "S2"}

        # Act
        result = generator._generate_styling(
            stage_nodes, mock_process_for_styling, "detailed"
        )

        # Assert
        styling_lines = "\n".join(result)
        assert "class S0 initial" in styling_lines
        assert "class S1 stage" in styling_lines
        assert "class S2 final" in styling_lines

    def test_generate_styling_handles_missing_stages(
        self, generator, mock_process_for_styling
    ):
        """Verify styling handles missing stages gracefully."""
        # Arrange
        stage_nodes = {"initial": "S0"}  # Missing middle and final

        # Act
        result = generator._generate_styling(
            stage_nodes, mock_process_for_styling, "detailed"
        )

        # Assert
        styling_lines = "\n".join(result)
        assert "class S0 initial" in styling_lines
        # Should not crash or include undefined stage references


class TestMermaidErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

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

    def test_generate_gate_flowchart_with_none_gates(self, generator):
        """Verify gate flowchart handles None gates list."""
        # Arrange & Act & Assert
        with pytest.raises((AttributeError, TypeError)):
            generator.generate_gate_flowchart(None)

    def test_parse_path_invalid_style_parameter(self, generator):
        """Verify methods handle invalid style parameters gracefully."""
        # Arrange
        mock_stage = Mock()
        mock_stage.name = "Test"
        mock_stage.gates = []

        # Act
        result = generator._generate_stage_label(mock_stage, "invalid_style")

        # Assert
        # Should default to full style behavior
        assert "Test" in result

    def test_get_gate_summary_from_stage_with_none_gates(self, generator):
        """Verify gate summary handles stage with None gates."""
        # Arrange
        stage = Mock()
        stage.gates = None

        # Act
        result = generator._get_gate_summary_from_stage(stage)

        # Assert
        assert result == "No gates"

    def test_gate_label_generation_with_mock_objects(self, generator):
        """Verify gate label generation handles various mock object types."""
        # Arrange
        string_gate = "string_gate"
        mock_gate = Mock()
        mock_gate.name = "mock_gate"
        object_gate = object()

        # Act & Assert
        assert generator._generate_gate_label(string_gate, "overview") == "string_gate"
        assert "mock_gate" in generator._generate_gate_label(mock_gate, "overview")
        assert isinstance(generator._generate_gate_label(object_gate, "overview"), str)


@pytest.mark.integration
class TestMermaidIntegrationScenarios:
    """Integration tests for Mermaid generator with realistic scenarios."""

    @pytest.fixture
    def realistic_process_config(self) -> dict[str, Any]:
        """Create a realistic process configuration for integration testing."""
        return {
            "name": "user_onboarding",
            "description": "User onboarding workflow",
            "stages": {
                "registration": {
                    "name": "User Registration",
                    "expected_properties": {"email": {"type": "str"}},
                    "gates": [
                        {
                            "name": "email_provided",
                            "target_stage": "verification",
                            "locks": [{"exists": "email"}],
                        }
                    ],
                },
                "verification": {
                    "name": "Email Verification",
                    "expected_properties": {"email_verified": {"type": "bool"}},
                    "gates": [
                        {
                            "name": "email_verified",
                            "target_stage": "profile_setup",
                            "locks": [{"exists": "email_verified"}],
                        }
                    ],
                },
                "profile_setup": {
                    "name": "Profile Setup",
                    "expected_properties": {
                        "first_name": {"type": "str"},
                        "last_name": {"type": "str"},
                    },
                    "gates": [
                        {
                            "name": "profile_complete",
                            "target_stage": "active",
                            "locks": [
                                {"exists": "first_name"},
                                {"exists": "last_name"},
                            ],
                        }
                    ],
                },
                "active": {"name": "Active User", "gates": [], "is_final": True},
            },
            "initial_stage": "registration",
            "final_stage": "active",
        }

    @pytest.fixture
    def generator(self) -> MermaidDiagramGenerator:
        """Create a MermaidDiagramGenerator instance for testing."""
        return MermaidDiagramGenerator()

    def test_complete_workflow_diagram_generation(
        self, generator, realistic_process_config
    ):
        """Verify complete workflow diagram generation with realistic process."""
        # Arrange
        mock_process = Mock(spec=Process)
        mock_process.name = realistic_process_config["name"]
        mock_process.get_sorted_stages = Mock(
            return_value=["registration", "verification", "profile_setup", "active"]
        )

        # Create mock initial and final stages
        initial_stage = Mock()
        initial_stage._id = "registration"
        initial_stage.name = "User Registration"
        mock_process.initial_stage = initial_stage

        final_stage = Mock()
        final_stage._id = "active"
        final_stage.name = "Active User"
        mock_process.final_stage = final_stage

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
                gate_mock.locks = []
                stage.gates.append(gate_mock)
            stages[stage_name] = stage

        mock_process.get_stage = Mock(side_effect=lambda name: stages.get(name))

        # Act
        overview_result = generator.generate_process_diagram(
            mock_process, style="overview"
        )
        detailed_result = generator.generate_process_diagram(
            mock_process, style="detailed"
        )
        full_result = generator.generate_process_diagram(mock_process, style="full")

        # Assert
        for result in [overview_result, detailed_result, full_result]:
            assert "```mermaid" in result
            assert "User Registration" in result
            assert "Email Verification" in result
            assert "Profile Setup" in result
            assert "Active User" in result
            assert "```" in result

    def test_stage_detail_with_complex_gates(self, generator):
        """Verify stage detail generation with complex gate structures."""
        # Arrange
        stage = Mock()
        stage.name = "Complex Validation Stage"

        # Create gates with locks
        gate1 = Mock()
        gate1.name = "input_validation"
        mock_lock1 = Mock()
        mock_lock1.property = "email"
        mock_lock1.type = Mock()
        mock_lock1.type.value = "REGEX"
        mock_lock1.expected_value = r"^[^@]+@[^@]+\.[^@]+$"
        gate1.locks = [mock_lock1]

        gate2 = Mock()
        gate2.name = "business_rules"
        mock_lock2 = Mock()
        mock_lock2.property = "age"
        mock_lock2.type = Mock()
        mock_lock2.type.value = "GREATER_THAN"
        mock_lock2.expected_value = 18
        gate2.locks = [mock_lock2]

        stage.gates = [gate1, gate2]

        # Act
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Assert
        assert "```mermaid" in result
        assert "Complex Validation Stage" in result
        assert "input_validation" in result
        assert "business_rules" in result
        assert "```" in result

    def test_error_recovery_with_malformed_stage_data(self, generator):
        """Verify generator recovers gracefully from malformed stage data."""
        # Arrange
        process = Mock(spec=Process)
        process.name = "test_process"
        process.get_sorted_stages = Mock(return_value=["stage1", "stage2"])

        # Create mock initial and final stages
        initial_stage = Mock()
        initial_stage._id = "stage1"
        initial_stage.name = "Valid Stage"
        process.initial_stage = initial_stage

        final_stage = Mock()
        final_stage._id = "stage2"
        final_stage.name = "Final Stage"
        process.final_stage = final_stage

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
        assert "```mermaid" in result
        assert "Valid Stage" in result
        assert "```" in result
        # Should not crash despite missing stage2


@pytest.mark.parametrize(
    "style,expected_elements",
    [
        ("overview", ["flowchart TD", "S0[", "S1[", "S0 --> S1"]),
        ("detailed", ["subgraph", "direction TB", "gate(s)"]),
        ("full", ["%% Gate Details", "subgraph G", "validation gate"]),
    ],
)
class TestMermaidParametrizedStyleGeneration:
    """Parametrized tests for different style generation scenarios."""

    @pytest.fixture
    def simple_process(self) -> Mock:
        """Create a simple process for parametrized testing."""
        process = Mock(spec=Process)
        process.name = "simple_process"
        process.get_sorted_stages = Mock(return_value=["stage1", "stage2"])

        # Create mock initial and final stages
        initial_stage = Mock()
        initial_stage._id = "stage1"
        initial_stage.name = "First"
        process.initial_stage = initial_stage

        final_stage = Mock()
        final_stage._id = "stage2"
        final_stage.name = "Second"
        process.final_stage = final_stage

        stage1 = Mock()
        stage1.name = "First"
        gate_mock = Mock()
        gate_mock.name = "gate1"
        gate_mock.target_stage = "stage2"  # Add target stage for transitions
        stage1.gates = [gate_mock]  # Properly iterable list

        stage2 = Mock()
        stage2.name = "Second"
        stage2.gates = []

        def get_stage_side_effect(name):
            if name == "stage1":
                return stage1
            elif name == "stage2":
                return stage2
            return None

        process.get_stage = Mock(side_effect=get_stage_side_effect)
        return process

    def test_style_specific_elements_present(
        self, style, expected_elements, simple_process
    ):
        """Verify specific style elements are present in generated diagrams."""
        # Arrange
        generator = MermaidDiagramGenerator()

        # For parametrized tests, ensure stage1 gates are properly set up
        stage1 = simple_process.get_stage("stage1")
        if stage1 and hasattr(stage1, "gates"):
            # Make sure gates is a proper list
            if not isinstance(stage1.gates, list):
                stage1.gates = [stage1.gates] if stage1.gates else []

        # Act
        result = generator.generate_process_diagram(simple_process, style=style)

        # Assert
        for element in expected_elements:
            # For full style gate details, only check if there are actually gates
            if element in ["subgraph G", "validation gate"] and style == "full":
                stage1 = simple_process.get_stage("stage1")
                if not (stage1 and hasattr(stage1, "gates") and stage1.gates):
                    continue  # Skip this check if no gates
            elif element == "validation gate" and style == "full":
                # validation gate text only appears if gates have actual content
                continue
            assert element in result, (
                f"Expected element '{element}' not found in {style} style"
            )
