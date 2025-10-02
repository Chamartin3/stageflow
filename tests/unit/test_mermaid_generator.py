"""Tests for Mermaid diagram generation."""

import pytest

from stageflow.stage import Stage
from stageflow.gates import Gate, Lock, LockType
from stageflow.process.main import Process
from stageflow.process.visualization.mermaid import MermaidDiagramGenerator


class TestMermaidDiagramGenerator:
    """Test Mermaid diagram generation functionality."""

    def test_init(self):
        """Test generator initialization."""
        generator = MermaidDiagramGenerator()
        assert generator.node_counter == 0

    def test_generate_process_diagram_simple(self):
        """Test basic process diagram generation."""
        # Create a simple process with two stages
        stage1 = Stage(name="stage1")
        stage2 = Stage(name="stage2")

        process = Process(
            name="test_process",
            stages=[stage1, stage2],
            stage_order=["stage1", "stage2"]
        )

        generator = MermaidDiagramGenerator()
        result = generator.generate_process_diagram(process, style="overview")

        # Check that result contains Mermaid markup
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "stage1" in result
        assert "stage2" in result
        assert "```" in result.split("\n")[-1]

    def test_generate_process_diagram_detailed(self):
        """Test detailed process diagram generation."""
        # Create stages with gates and locks
        lock = Lock(
            property_path="user.name",
            lock_type=LockType.EXISTS
        )
        gate = Gate.create(lock, name="name_check")
        stage1 = Stage(name="profile_setup", gates=[gate])
        stage2 = Stage(name="completed")

        process = Process(
            name="user_onboarding",
            stages=[stage1, stage2],
            stage_order=["profile_setup", "completed"]
        )

        generator = MermaidDiagramGenerator()
        result = generator.generate_process_diagram(process, style="detailed")

        # Check for detailed content
        assert "```mermaid" in result
        assert "Process: user_onboarding" in result
        assert "profile_setup" in result
        assert "1 gate(s)" in result or "Gates:" in result

    def test_generate_process_diagram_full(self):
        """Test full process diagram generation."""
        # Create complex process
        lock1 = Lock(property_path="user.email", lock_type=LockType.EXISTS)
        lock2 = Lock(property_path="user.verified", lock_type=LockType.EQUALS, expected_value=True)
        gate = Gate.create(lock1, lock2, name="email_verification")

        stage1 = Stage(name="email_signup", gates=[gate])
        stage2 = Stage(name="active_user")

        process = Process(
            name="registration_flow",
            stages=[stage1, stage2],
            stage_order=["email_signup", "active_user"]
        )

        generator = MermaidDiagramGenerator()
        result = generator.generate_process_diagram(process, style="full")

        # Check for full detail content
        assert "```mermaid" in result
        assert "subgraph" in result
        assert "email_verification" in result

    def test_generate_stage_detail(self):
        """Test stage detail diagram generation."""
        lock = Lock(property_path="profile.complete", lock_type=LockType.EQUALS, expected_value=True)
        gate = Gate.create(lock, name="completion_check")
        stage = Stage(name="profile_validation", gates=[gate])

        generator = MermaidDiagramGenerator()
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Check stage detail content
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "profile_validation" in result
        assert "completion_check" in result
        assert "profile.complete" in result

    def test_generate_stage_detail_no_gates(self):
        """Test stage detail for stage with no gates."""
        stage = Stage(name="simple_stage")

        generator = MermaidDiagramGenerator()
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Check content for stage without gates
        assert "```mermaid" in result
        assert "simple_stage" in result
        assert "No Gates Defined" in result

    def test_generate_gate_flowchart(self):
        """Test gate flowchart generation."""
        lock1 = Lock(property_path="user.id", lock_type=LockType.EXISTS)
        lock2 = Lock(property_path="user.active", lock_type=LockType.EQUALS, expected_value=True)

        gate1 = Gate.create(lock1, name="id_check")
        gate2 = Gate.create(lock2, name="active_check")
        gates = [gate1, gate2]

        generator = MermaidDiagramGenerator()
        result = generator.generate_gate_flowchart(gates)

        # Check gate flowchart content
        assert "```mermaid" in result
        assert "flowchart TD" in result
        assert "Gate Evaluation" in result
        assert "id_check" in result
        assert "active_check" in result

    def test_generate_gate_flowchart_empty(self):
        """Test gate flowchart with no gates."""
        generator = MermaidDiagramGenerator()
        result = generator.generate_gate_flowchart([])

        # Check empty gate flowchart
        assert "```mermaid" in result
        assert "No Gates Defined" in result

    def test_legacy_compatibility(self):
        """Test backward compatibility with include_details parameter."""
        stage = Stage(name="test_stage")
        process = Process(name="test", stages=[stage], stage_order=["test_stage"])

        generator = MermaidDiagramGenerator()

        # Test legacy parameter mapping
        result_legacy = generator.generate_process_diagram(process, include_details=True)
        result_new = generator.generate_process_diagram(process, style="detailed")

        # Both should produce similar results (detailed style)
        assert "```mermaid" in result_legacy
        assert "```mermaid" in result_new

    def test_process_with_no_stages(self):
        """Test handling of process with no stages."""
        with pytest.raises(ValueError, match="Process must contain at least one stage"):
            Process(name="empty_process", stages=[])

    def test_stage_labels_generation(self):
        """Test stage label generation for different styles."""
        gate = Gate.create(
            Lock(property_path="test.field", lock_type=LockType.EXISTS),
            name="test_gate"
        )
        stage = Stage(name="test_stage", gates=[gate])

        generator = MermaidDiagramGenerator()

        # Test overview style
        overview_label = generator._generate_stage_label(stage, "overview")
        assert overview_label == "test_stage"

        # Test detailed style
        detailed_label = generator._generate_stage_label(stage, "detailed")
        assert "test_stage" in detailed_label
        assert "gate" in detailed_label.lower()

        # Test full style
        full_label = generator._generate_stage_label(stage, "full")
        assert "test_stage" in full_label
        assert "gate" in full_label.lower()

    def test_transition_labels_generation(self):
        """Test transition label generation."""
        gate = Gate.create(
            Lock(property_path="status", lock_type=LockType.EQUALS, expected_value="ready"),
            name="ready_check"
        )
        stage = Stage(name="validation", gates=[gate])

        generator = MermaidDiagramGenerator()

        # Test overview style (no label)
        overview_label = generator._generate_transition_label(stage, "overview")
        assert overview_label == ""

        # Test detailed style
        detailed_label = generator._generate_transition_label(stage, "detailed")
        assert "ready_check" in detailed_label

        # Test stage with no gates
        empty_stage = Stage(name="empty")
        auto_label = generator._generate_transition_label(empty_stage, "detailed")
        assert auto_label == "auto"
