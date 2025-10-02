"""Tests for Graphviz DOT generation."""


from stageflow.stage import Stage
from stageflow.gates import Gate, Lock, LockType
from stageflow.process.main import Process
from stageflow.process.visualization.graphviz import GraphvizDotGenerator


class TestGraphvizDotGenerator:
    """Test Graphviz DOT generation functionality."""

    def test_init_default(self):
        """Test generator initialization with default layout."""
        generator = GraphvizDotGenerator()
        assert generator.layout_engine == "dot"

    def test_init_custom_layout(self):
        """Test generator initialization with custom layout."""
        generator = GraphvizDotGenerator(layout_engine="circo")
        assert generator.layout_engine == "circo"

    def test_generate_process_diagram_simple(self):
        """Test basic DOT diagram generation."""
        stage1 = Stage(name="initial_stage")
        stage2 = Stage(name="final_stage")

        process = Process(
            name="simple_process",
            stages=[stage1, stage2],
            stage_order=["initial_stage", "final_stage"]
        )

        generator = GraphvizDotGenerator()
        result = generator.generate_process_diagram(process, style="overview")

        # Check DOT format
        assert result.startswith("digraph StageFlow {")
        assert result.endswith("}")
        assert "layout=dot;" in result
        assert "simple_process Process Flow" in result
        assert "initial_stage" in result
        assert "final_stage" in result

    def test_generate_process_diagram_detailed(self):
        """Test detailed DOT diagram generation."""
        lock = Lock(property_path="user.status", lock_type=LockType.EQUALS, expected_value="active")
        gate = Gate.create(lock, name="status_check")
        stage1 = Stage(name="user_validation", gates=[gate])
        stage2 = Stage(name="approved")

        process = Process(
            name="approval_process",
            stages=[stage1, stage2],
            stage_order=["user_validation", "approved"]
        )

        generator = GraphvizDotGenerator()
        result = generator.generate_process_diagram(process, style="detailed")

        # Check detailed content
        assert "digraph StageFlow {" in result
        assert "user_validation" in result
        assert "1 gates" in result or "gate" in result.lower()

    def test_generate_process_diagram_full(self):
        """Test full DOT diagram generation with subgraphs."""
        lock1 = Lock(property_path="data.complete", lock_type=LockType.EXISTS)
        lock2 = Lock(property_path="data.valid", lock_type=LockType.EQUALS, expected_value=True)
        gate = Gate.create(lock1, lock2, name="data_validation")

        stage1 = Stage(name="data_processing", gates=[gate])
        stage2 = Stage(name="completed")

        process = Process(
            name="data_pipeline",
            stages=[stage1, stage2],
            stage_order=["data_processing", "completed"]
        )

        generator = GraphvizDotGenerator()
        result = generator.generate_process_diagram(process, style="full")

        # Check full style with subgraphs
        assert "digraph StageFlow {" in result
        assert "subgraph cluster_" in result
        assert "data_validation" in result
        assert "data.complete" in result or "data_complete" in result

    def test_generate_stage_detail(self):
        """Test stage detail DOT generation."""
        lock = Lock(property_path="verification.complete", lock_type=LockType.EQUALS, expected_value=True)
        gate = Gate.create(lock, name="verification_gate")
        stage = Stage(name="verification_stage", gates=[gate])

        generator = GraphvizDotGenerator()
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Check stage detail content
        assert "digraph StageDetail {" in result
        assert "verification_stage" in result
        assert "verification_gate" in result
        assert "verification.complete" in result or "verification_complete" in result

    def test_generate_stage_detail_no_gates(self):
        """Test stage detail for stage without gates."""
        stage = Stage(name="simple_stage")

        generator = GraphvizDotGenerator()
        result = generator.generate_stage_detail(stage, include_locks=True)

        # Check content for stage without gates
        assert "digraph StageDetail {" in result
        assert "simple_stage" in result
        assert "nogates" in result.lower()

    def test_generate_dot_file(self):
        """Test DOT file generation method."""
        stage = Stage(name="test_stage")
        process = Process(name="test_process", stages=[stage], stage_order=["test_stage"])

        generator = GraphvizDotGenerator()
        result = generator.generate_dot_file(process, style="overview")

        # Should be same as generate_process_diagram
        expected = generator.generate_process_diagram(process, style="overview")
        assert result == expected

    def test_generate_stage_subgraph(self):
        """Test stage subgraph generation."""
        stage = Stage(name="test stage")

        generator = GraphvizDotGenerator()
        result = generator.generate_stage_subgraph(stage)

        # Check subgraph format
        assert "subgraph cluster_test_stage" in result
        assert 'label="test stage"' in result
        assert "test_stage_node" in result

    def test_generate_gate_nodes(self):
        """Test gate nodes generation."""
        lock1 = Lock(property_path="field1", lock_type=LockType.EXISTS)
        lock2 = Lock(property_path="field2", lock_type=LockType.EQUALS, expected_value="value")

        gate1 = Gate.create(lock1, name="gate_one")
        gate2 = Gate.create(lock2, name="gate_two")
        gates = [gate1, gate2]

        generator = GraphvizDotGenerator()
        result = generator.generate_gate_nodes(gates)

        # Check gate nodes
        assert "gate_0" in result
        assert "gate_1" in result
        assert "gate_one" in result
        assert "gate_two" in result
        assert "hexagon" in result

    def test_stage_styling(self):
        """Test stage node styling based on position."""
        generator = GraphvizDotGenerator()

        # Test initial stage styling
        shape, color = generator._get_stage_styling(is_initial=True, is_final=False)
        assert shape == "house"
        assert color == "lightblue"

        # Test final stage styling
        shape, color = generator._get_stage_styling(is_initial=False, is_final=True)
        assert shape == "invhouse"
        assert color == "lightgreen"

        # Test middle stage styling
        shape, color = generator._get_stage_styling(is_initial=False, is_final=False)
        assert shape == "box"
        assert color == "lightgray"

    def test_legacy_include_details_parameter(self):
        """Test backward compatibility with include_details parameter."""
        stage = Stage(name="legacy_test")
        process = Process(name="legacy", stages=[stage], stage_order=["legacy_test"])

        generator = GraphvizDotGenerator()

        # Test legacy parameter mapping
        result_legacy = generator.generate_process_diagram(process, include_details=True)
        result_new = generator.generate_process_diagram(process, style="detailed")

        # Both should contain similar level of detail
        assert "digraph StageFlow {" in result_legacy
        assert "digraph StageFlow {" in result_new

    def test_different_layout_engines(self):
        """Test different Graphviz layout engines."""
        stage = Stage(name="test")
        process = Process(name="test", stages=[stage], stage_order=["test"])

        # Test different layout engines
        for engine in ["dot", "circo", "fdp", "neato"]:
            generator = GraphvizDotGenerator(layout_engine=engine)
            result = generator.generate_process_diagram(process)
            assert f"layout={engine};" in result

    def test_label_generation_methods(self):
        """Test various label generation methods."""
        lock = Lock(property_path="test.field", lock_type=LockType.EXISTS)
        gate = Gate.create(lock, name="test_gate")
        stage = Stage(name="test_stage", gates=[gate])

        generator = GraphvizDotGenerator()

        # Test stage label generation
        overview_label = generator._generate_stage_label(stage, "overview")
        assert overview_label == "test_stage"

        detailed_label = generator._generate_stage_label(stage, "detailed")
        assert "test_stage" in detailed_label
        assert "1 gates" in detailed_label

        # Test edge label generation
        edge_label = generator._generate_edge_label(stage, "detailed")
        assert "test_gate" in edge_label

        # Test gate label generation
        gate_label = generator._generate_gate_label(gate, "detailed")
        assert "test_gate" in gate_label

        # Test lock label generation
        lock_label = generator._generate_lock_label(lock)
        assert "test.field" in lock_label
        assert "EXISTS" in lock_label

    def test_gate_summary_generation(self):
        """Test gate summary generation."""
        lock = Lock(property_path="field", lock_type=LockType.EXISTS)
        gate = Gate.create(lock, name="test_gate")

        generator = GraphvizDotGenerator()

        # Test gate summary
        summary = generator._get_gate_summary(gate)
        assert "1 locks" in summary

        # Test lock count
        count = generator._get_lock_count(gate)
        assert count == 1

    def test_process_with_mixed_stages(self):
        """Test process with stages having different gate configurations."""
        # Stage with gates
        lock = Lock(property_path="status", lock_type=LockType.EXISTS)
        gate = Gate.create(lock, name="status_gate")
        stage_with_gates = Stage(name="validation", gates=[gate])

        # Stage without gates
        stage_without_gates = Stage(name="simple")

        process = Process(
            name="mixed_process",
            stages=[stage_with_gates, stage_without_gates],
            stage_order=["validation", "simple"]
        )

        generator = GraphvizDotGenerator()
        result = generator.generate_process_diagram(process, style="detailed")

        # Should handle both types of stages
        assert "validation" in result
        assert "simple" in result
        assert "1 gates" in result
        assert "0 gates" in result or "auto" in result
