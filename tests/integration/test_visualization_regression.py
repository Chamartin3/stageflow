"""Regression tests for specific visualization bugs that were previously fixed.

This module contains tests that reproduce specific bugs that were found and fixed
in the visualization system. These tests ensure the bugs don't regress.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest


class TestVisualizationRegression:
    """Regression test suite for previously fixed visualization bugs."""

    def run_stageflow_cli(self, args: list[str], expect_success: bool = True) -> dict[str, Any]:
        """Run StageFlow CLI and return structured result."""
        cmd = ["uv", "run", "stageflow"] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).parent.parent.parent
            )

            if expect_success:
                assert result.returncode == 0, f"Expected success but got exit code {result.returncode}. stderr: {result.stderr}"

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            pytest.fail("CLI command timed out after 30 seconds")
        except Exception as e:
            pytest.fail(f"Failed to run CLI command: {e}")

    def test_convergence_flow_not_linear_regression(self):
        """
        Regression test for the bug where convergence flows were visualized as linear
        chains instead of proper branching/convergence patterns.

        Bug: Visualization generated S0->S1->S2->S3->S4->S5->S6->S7->S8 instead of
        the correct branching pattern where S0 branches to S1, S6, S8 and they
        converge at S2.
        """
        examples_dir = Path(__file__).parent.parent.parent / "examples"
        convergence_file = examples_dir / "case3_visualization" / "complex" / "convergence_flow.yaml"

        if not convergence_file.exists():
            pytest.skip("Convergence flow example not found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            output_file = Path(tmp.name)

        try:
            # Generate visualization
            result = self.run_stageflow_cli([
                str(convergence_file),
                "--diagram", str(output_file)
            ], expect_success=True)

            assert result["exit_code"] == 0
            assert output_file.exists()

            # Parse transitions
            content = output_file.read_text()
            lines = content.split('\n')

            transitions = []
            for line in lines:
                if "-->" in line and line.strip().startswith("S"):
                    parts = line.strip().split(" --> ")
                    if len(parts) == 2:
                        source = parts[0].strip()
                        target = parts[1].strip()
                        transitions.append((source, target))

            # Detect the specific bug pattern: linear progression
            # The bug would create: S0->S1, S1->S2, S2->S3, S3->S4, S4->S5, S5->S6, S6->S7, S7->S8
            consecutive_linear_transitions = 0
            for i in range(8):  # S0 through S7
                linear_transition = (f"S{i}", f"S{i+1}")
                if linear_transition in transitions:
                    consecutive_linear_transitions += 1

            # Should NOT have more than 6 consecutive linear transitions in a convergence flow
            # (The broken version would have 8 consecutive linear transitions)
            assert consecutive_linear_transitions <= 6, f"Found {consecutive_linear_transitions} consecutive linear transitions, indicating linear bug regression. Transitions: {transitions}"

            # Should have branching from S0 (order_received)
            s0_targets = [target for source, target in transitions if source == "S0"]
            assert len(s0_targets) >= 2, f"S0 should branch to multiple targets, but only found: {s0_targets}"

            # Should have convergence at S2 (inventory_check)
            s2_sources = [source for source, target in transitions if target == "S2"]
            assert len(s2_sources) >= 2, f"S2 should be target of multiple sources (convergence), but only found: {s2_sources}"

        finally:
            output_file.unlink(missing_ok=True)

    def test_final_stage_styling_position_bug_regression(self):
        """
        Regression test for the bug where final stage styling was based on
        stage_order array position instead of actual process.final_stage.

        Bug: The last stage in the sorted array was marked as 'final' instead of
        the actual final stage from the process configuration.
        """
        examples_dir = Path(__file__).parent.parent.parent / "examples"
        convergence_file = examples_dir / "case3_visualization" / "complex" / "convergence_flow.yaml"

        if not convergence_file.exists():
            pytest.skip("Convergence flow example not found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            output_file = Path(tmp.name)

        try:
            # Generate visualization
            result = self.run_stageflow_cli([
                str(convergence_file),
                "--diagram", str(output_file)
            ], expect_success=True)

            assert result["exit_code"] == 0
            assert output_file.exists()

            # Parse the visualization
            content = output_file.read_text()
            lines = content.split('\n')

            # Extract stage-to-node mappings
            stage_mappings = {}
            for line in lines:
                if "[" in line and "]" in line and line.strip().startswith("S"):
                    parts = line.strip().split("[", 1)
                    if len(parts) == 2:
                        node_id = parts[0].strip()
                        stage_name = parts[1].rstrip("]")
                        stage_mappings[stage_name] = node_id

            # Find which node is styled as final
            final_styled_nodes = []
            for line in lines:
                if "class" in line and "final" in line:
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[0] == "class" and parts[2] == "final":
                        final_styled_nodes.append(parts[1])

            # Should have exactly one final-styled node
            assert len(final_styled_nodes) == 1, f"Should have exactly one final-styled node, found: {final_styled_nodes}"

            final_node = final_styled_nodes[0]

            # Find which stage this node represents
            final_stage_name = None
            for stage_name, node_id in stage_mappings.items():
                if node_id == final_node:
                    final_stage_name = stage_name
                    break

            # The final stage should be 'order_fulfilled', not any other stage
            # This would catch the bug where 'store_validation' was marked as final
            # because it was last in the stage_order array
            assert final_stage_name == "order_fulfilled", f"Final stage should be 'order_fulfilled', but '{final_stage_name}' was marked as final"

            # Specifically check that 'store_validation' is NOT marked as final
            # (this was the specific bug symptom)
            store_validation_node = stage_mappings.get("store_validation")
            if store_validation_node:
                assert store_validation_node not in final_styled_nodes, "store_validation should not be marked as final (position-based bug)"

        finally:
            output_file.unlink(missing_ok=True)

    def test_transition_generation_follows_gates_not_ordering(self):
        """
        Regression test for the bug where transitions were generated based on
        sequential stage ordering instead of actual gate target relationships.

        Bug: Transitions were generated as stage[i] -> stage[i+1] instead of
        following gate.target_stage relationships.
        """
        examples_dir = Path(__file__).parent.parent.parent / "examples"

        # Test with a simple branching flow that should NOT be linear
        branching_file = examples_dir / "case3_visualization" / "simple" / "branching_flow.yaml"

        if not branching_file.exists():
            pytest.skip("Branching flow example not found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            output_file = Path(tmp.name)

        try:
            # Generate visualization
            result = self.run_stageflow_cli([
                str(branching_file),
                "--diagram", str(output_file)
            ], expect_success=True)

            assert result["exit_code"] == 0
            assert output_file.exists()

            # Parse transitions
            content = output_file.read_text()
            lines = content.split('\n')

            transitions = []
            for line in lines:
                if "-->" in line and line.strip().startswith("S"):
                    parts = line.strip().split(" --> ")
                    if len(parts) == 2:
                        source = parts[0].strip()
                        target = parts[1].strip()
                        transitions.append((source, target))

            # For a branching flow, the first stage should connect to multiple targets
            # This would catch the bug where only S0->S1 was shown instead of proper branching

            # Find transitions from the first stage (S0)
            s0_transitions = [target for source, target in transitions if source == "S0"]

            # Should have branching (multiple transitions from S0)
            assert len(s0_transitions) > 1, f"First stage should branch to multiple stages, but only found transitions to: {s0_transitions}"

            # Verify transitions match actual process logic, not just linear ordering
            # The bug would show S0->S1->S2->S3->S4 instead of actual gate relationships

            # Count how many transitions follow the pattern Si -> S(i+1)
            linear_pattern_count = 0
            for i in range(len(transitions)):
                linear_transition = (f"S{i}", f"S{i+1}")
                if linear_transition in transitions:
                    linear_pattern_count += 1

            total_transitions = len(transitions)
            linear_percentage = (linear_pattern_count / total_transitions) if total_transitions > 0 else 0

            # For a branching flow, shouldn't be more than 50% linear transitions
            assert linear_percentage < 0.5, f"Too many linear transitions ({linear_pattern_count}/{total_transitions} = {linear_percentage:.1%}), suggests ordering-based bug regression"

        finally:
            output_file.unlink(missing_ok=True)

    def test_stage_order_independence(self):
        """
        Test that visualization results are independent of the internal stage ordering
        and depend only on the actual process structure.

        This is a meta-test that verifies the visualization system correctly represents
        the logical process structure regardless of how stages are internally ordered.
        """
        from stageflow.schema.loader import load_process

        examples_dir = Path(__file__).parent.parent.parent / "examples"
        convergence_file = examples_dir / "case3_visualization" / "complex" / "convergence_flow.yaml"

        if not convergence_file.exists():
            pytest.skip("Convergence flow example not found")

        # Load the process to understand its structure
        process = load_process(str(convergence_file))

        # Generate visualization
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            output_file = Path(tmp.name)

        try:
            self.run_stageflow_cli([
                str(convergence_file),
                "--diagram", str(output_file)
            ], expect_success=True)

            content = output_file.read_text()
            lines = content.split('\n')

            # Parse actual transitions from visualization
            actual_transitions = []
            for line in lines:
                if "-->" in line and line.strip().startswith("S"):
                    parts = line.strip().split(" --> ")
                    if len(parts) == 2:
                        source = parts[0].strip()
                        target = parts[1].strip()
                        actual_transitions.append((source, target))

            # Extract stage mappings from visualization
            stage_to_node = {}
            for line in lines:
                if "[" in line and "]" in line and line.strip().startswith("S"):
                    parts = line.strip().split("[", 1)
                    if len(parts) == 2:
                        node_id = parts[0].strip()
                        stage_name = parts[1].rstrip("]")
                        stage_to_node[stage_name] = node_id

            # Build expected transitions based on actual process structure
            expected_stage_transitions = []
            for stage in process.stages:
                if stage.gates:
                    for gate in stage.gates:
                        if hasattr(gate, 'target_stage') and gate.target_stage:
                            source_stage = stage._id
                            target_stage = gate.target_stage
                            expected_stage_transitions.append((source_stage, target_stage))

            # Convert expected stage transitions to node transitions
            expected_node_transitions = []
            for source_stage, target_stage in expected_stage_transitions:
                if source_stage in stage_to_node and target_stage in stage_to_node:
                    source_node = stage_to_node[source_stage]
                    target_node = stage_to_node[target_stage]
                    expected_node_transitions.append((source_node, target_node))

            # Verify that actual transitions match expected transitions
            actual_set = set(actual_transitions)
            expected_set = set(expected_node_transitions)

            missing_transitions = expected_set - actual_set
            extra_transitions = actual_set - expected_set

            assert len(missing_transitions) == 0, f"Missing expected transitions: {missing_transitions}"
            assert len(extra_transitions) == 0, f"Unexpected extra transitions: {extra_transitions}"

        finally:
            output_file.unlink(missing_ok=True)
