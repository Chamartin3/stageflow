"""Graphviz DOT generation for StageFlow."""

from typing import Any

# Use relative imports for the process models
from stageflow.process import Process


class GraphvizDotGenerator:
    """
    Enhanced generator for Graphviz DOT diagrams from StageFlow processes.

    Creates professional DOT format output for visualizing process flows with
    multiple layout options and comprehensive styling.
    """

    def __init__(self, layout_engine: str = "dot"):
        """
        Initialize Graphviz generator.

        Args:
            layout_engine: Graphviz layout engine - "dot", "circo", "fdp", "neato"
        """
        self.layout_engine = layout_engine

    def generate_process_diagram(self, process: Process, style: str = "overview", include_details: bool = False) -> str:
        """
        Generate enhanced Graphviz DOT diagram for a process.

        Args:
            process: Process to visualize
            style: Diagram style - "overview", "detailed", or "full"
            include_details: Whether to include gate and lock details (legacy parameter)

        Returns:
            DOT format string
        """
        # Map legacy parameter to style
        if include_details and style == "overview":
            style = "detailed"

        lines = []
        lines.append("digraph StageFlow {")

        # Set layout and general properties
        lines.append(f"    layout={self.layout_engine};")
        lines.append("    rankdir=TB;")
        lines.append("    compound=true;")
        lines.append("    concentrate=false;")
        lines.append("")

        # Graph styling
        lines.append("    // Graph attributes")
        lines.append('    bgcolor="white";')
        lines.append('    fontname="Arial";')
        lines.append('    fontsize=14;')
        lines.append("")

        # Add title
        lines.append(f'    label="{process.name} Process Flow";')
        lines.append('    labelloc="t";')
        lines.append('    fontsize=18;')
        lines.append("")

        # Default node and edge styling
        lines.append("    // Default styling")
        lines.append('    node [fontname="Arial", fontsize=10, style=filled];')
        lines.append('    edge [fontname="Arial", fontsize=9];')
        lines.append("")

        # Generate stage nodes
        stage_nodes = {}
        lines.append("    // Stage nodes")
        stage_order = process.get_sorted_stages()

        for i, stage_name in enumerate(stage_order):
            stage = process.get_stage(stage_name)
            if not stage:
                continue

            node_id = f"stage_{i}"
            stage_nodes[stage_name] = node_id

            # Determine stage styling
            is_initial = i == 0
            is_final = i == len(stage_order) - 1

            label = self._generate_stage_label(stage, style)
            shape, color = self._get_stage_styling(is_initial, is_final)

            lines.append(f'    {node_id} [label="{label}", shape={shape}, fillcolor="{color}"];')

        lines.append("")

        # Generate edges between stages
        lines.append("    // Stage transitions")
        for i, stage_name in enumerate(stage_order):
            stage = process.get_stage(stage_name)
            if not stage:
                continue

            current_node = stage_nodes[stage_name]

            # Connect to next stage
            if i < len(stage_order) - 1:
                next_stage_name = stage_order[i + 1]
                # Skip if next stage doesn't exist in stage_nodes (handles malformed data)
                if next_stage_name not in stage_nodes:
                    continue
                next_node = stage_nodes[next_stage_name]

                edge_label = self._generate_edge_label(stage, style)
                if edge_label:
                    lines.append(f'    {current_node} -> {next_node} [label="{edge_label}"];')
                else:
                    lines.append(f"    {current_node} -> {next_node};")

        # Add detailed gate information for full style
        if style == "full":
            lines.append("")
            lines.append("    // Gate details")
            for stage_name in stage_order:
                stage = process.get_stage(stage_name)
                if not stage or not stage.gates:
                    continue

                stage_node = stage_nodes[stage_name]
                cluster_name = f"cluster_{stage_node}"

                lines.append(f"    subgraph {cluster_name} {{")
                lines.append(f'        label="{stage.name} Gates";')
                lines.append('        style="dashed";')
                lines.append('        color="gray60";')
                lines.append('        fontsize=10;')
                lines.append("")

                # Add gate nodes
                for j, gate in enumerate(stage.gates):
                    gate_node = f"gate_{stage_node}_{j}"
                    gate_label = self._generate_gate_label(gate, style)
                    lines.append(f'        {gate_node} [label="{gate_label}", shape=hexagon, fillcolor="lightyellow"];')

                    # Add lock nodes if gate has locks
                    if hasattr(gate, '_locks') and gate._locks:
                        for k, lock in enumerate(gate._locks):
                            lock_node = f"lock_{gate_node}_{k}"
                            lock_label = self._generate_lock_label(lock)
                            lines.append(f'        {lock_node} [label="{lock_label}", shape=diamond, fillcolor="lightcyan"];')
                            lines.append(f"        {gate_node} -> {lock_node};")

                lines.append("    }")
                lines.append("")

        lines.append("}")
        return "\n".join(lines)

    def generate_stage_detail(self, stage: Any, include_locks: bool = True) -> str:
        """
        Generate detailed Graphviz diagram for a single stage.

        Args:
            stage: Stage to visualize
            include_locks: Whether to include lock details

        Returns:
            DOT format string
        """
        lines = []
        lines.append("digraph StageDetail {")
        lines.append("    rankdir=TB;")
        lines.append('    fontname="Arial";')
        lines.append("")

        # Add title
        lines.append(f'    label="Stage: {stage.name}";')
        lines.append('    labelloc="t";')
        lines.append('    fontsize=16;')
        lines.append("")

        # Default styling
        lines.append('    node [fontname="Arial", fontsize=10, style=filled];')
        lines.append('    edge [fontname="Arial", fontsize=9];')
        lines.append("")

        # Stage node
        lines.append(f'    stage [label="{stage.name}", shape=box, fillcolor="lightgreen"];')

        if not stage.gates:
            lines.append('    nogates [label="No Gates", shape=box, fillcolor="lightgray"];')
            lines.append("    stage -> nogates;")
        else:
            # Gate nodes
            for i, gate in enumerate(stage.gates):
                gate_node = f"gate_{i}"
                gate_label = self._generate_gate_label(gate, "full")
                lines.append(f'    {gate_node} [label="{gate_label}", shape=hexagon, fillcolor="lightyellow"];')
                lines.append(f"    stage -> {gate_node};")

                if include_locks and hasattr(gate, 'components') and gate.components:
                    # Lock nodes
                    for j, component in enumerate(gate.components):
                        if hasattr(component, 'lock'):
                            lock = component.lock
                            lock_node = f"lock_{i}_{j}"
                            lock_label = self._generate_lock_label(lock)
                            lines.append(f'    {lock_node} [label="{lock_label}", shape=diamond, fillcolor="lightcyan"];')
                            lines.append(f"    {gate_node} -> {lock_node};")

        lines.append("}")
        return "\n".join(lines)

    def generate_dot_file(self, process: Process, style: str = "overview") -> str:
        """
        Generate DOT file content for a process.

        Args:
            process: Process to visualize
            style: Visualization style

        Returns:
            Complete DOT file content
        """
        return self.generate_process_diagram(process, style)

    def generate_stage_subgraph(self, stage: Any) -> str:
        """
        Generate DOT subgraph for a single stage.

        Args:
            stage: Stage to visualize

        Returns:
            DOT subgraph string
        """
        lines = []
        subgraph_name = f"cluster_{stage.name.replace(' ', '_')}"

        lines.append(f"    subgraph {subgraph_name} {{")
        lines.append(f'        label="{stage.name}";')
        lines.append('        style="rounded";')
        lines.append('        color="blue";')

        # Add stage content
        stage_node = f"{stage.name.replace(' ', '_')}_node"
        lines.append(f'        {stage_node} [label="{stage.name}", shape=box];')

        lines.append("    }")
        return "\n".join(lines)

    def generate_gate_nodes(self, gates: list[Any]) -> str:
        """
        Generate DOT nodes for gates.

        Args:
            gates: List of gates to visualize

        Returns:
            DOT nodes string
        """
        lines = []
        for i, gate in enumerate(gates):
            gate_node = f"gate_{i}"
            gate_label = self._generate_gate_label(gate, "detailed")
            lines.append(f'    {gate_node} [label="{gate_label}", shape=hexagon, fillcolor="lightyellow"];')

        return "\n".join(lines)

    def generate_state_flow(self) -> str:
        """
        Generate GraphViz diagram showing the 7-state evaluation flow.

        Returns:
            GraphViz diagram of state transitions
        """
        return """digraph StateFlow {
    label="StageFlow 7-State Evaluation Flow";
    rankdir=LR;

    node [shape=box, style=rounded];

    // State nodes
    SCOPING [style=filled, fillcolor=lightcoral];
    FULFILLING [style=filled, fillcolor=lightblue];
    QUALIFYING [style=filled, fillcolor=lightgreen];
    AWAITING [style=filled, fillcolor=lightyellow];
    ADVANCING [style=filled, fillcolor=lightcyan];
    REGRESSING [style=filled, fillcolor=lightpink];
    COMPLETED [style=filled, fillcolor=lightgray];

    // State transitions
    SCOPING -> FULFILLING;
    FULFILLING -> QUALIFYING;
    FULFILLING -> AWAITING;
    FULFILLING -> REGRESSING;
    QUALIFYING -> ADVANCING;
    QUALIFYING -> REGRESSING;
    AWAITING -> FULFILLING;
    AWAITING -> QUALIFYING;
    ADVANCING -> COMPLETED;
    REGRESSING -> SCOPING;
    REGRESSING -> FULFILLING;
}"""

    def _generate_stage_label(self, stage: Any, style: str) -> str:
        """Generate appropriate label for a stage."""
        if style == "overview":
            return stage.name
        elif style == "detailed":
            gate_count = len(stage.gates) if stage.gates else 0
            return f"{stage.name}\\n({gate_count} gates)"
        else:  # full
            parts = [stage.name]
            if stage.gates:
                parts.append(f"{len(stage.gates)} gate(s)")
            if hasattr(stage, 'schema') and stage.schema:
                parts.append("Schema validation")
            return "\\n".join(parts)

    def _generate_edge_label(self, stage: Any, style: str) -> str:
        """Generate edge label based on stage gates."""
        if style == "overview":
            return ""
        elif not stage.gates:
            return "auto"
        elif len(stage.gates) == 1:
            return stage.gates[0].name if style == "detailed" else f"{stage.gates[0].name}\\n({self._get_gate_summary(stage.gates[0])})"
        else:
            return f"{len(stage.gates)} gates" if style == "detailed" else f"{len(stage.gates)} gates\\n(all required)"

    def _generate_gate_label(self, gate: Any, style: str) -> str:
        """Generate appropriate label for a gate."""
        if style == "overview":
            return gate.name
        elif style == "detailed":
            lock_count = self._get_lock_count(gate)
            return f"{gate.name}\\n{lock_count} locks" if lock_count > 0 else gate.name
        else:  # full
            summary = self._get_gate_summary(gate)
            return f"{gate.name}\\n{summary}"

    def _generate_lock_label(self, lock: Any) -> str:
        """Generate label for a lock."""
        label = f"{lock.property_path}\\n{lock.lock_type.value}"
        if hasattr(lock, 'expected_value') and lock.expected_value is not None:
            label += f"\\n= {lock.expected_value}"
        return label

    def _get_stage_styling(self, is_initial: bool, is_final: bool) -> tuple[str, str]:
        """Get shape and color for a stage node."""
        if is_initial:
            return "house", "lightblue"
        elif is_final:
            return "invhouse", "lightgreen"
        else:
            return "box", "lightgray"

    def _get_gate_summary(self, gate: Any) -> str:
        """Get a summary of gate composition."""
        if not hasattr(gate, 'components') or not gate.components:
            return "No components"

        lock_count = sum(1 for comp in gate.components if hasattr(comp, 'lock'))
        gate_count = sum(1 for comp in gate.components if hasattr(comp, 'name') and not hasattr(comp, 'lock'))

        parts = []
        if lock_count > 0:
            parts.append(f"{lock_count} locks")
        if gate_count > 0:
            parts.append(f"{gate_count} gates")

        return ", ".join(parts) if parts else "No components"

    def _get_lock_count(self, gate: Any) -> int:
        """Get the number of locks in a gate."""
        if not hasattr(gate, 'components') or not gate.components:
            return 0
        return sum(1 for comp in gate.components if hasattr(comp, 'lock'))


# Maintain backward compatibility
class GraphvizGenerator(GraphvizDotGenerator):
    """Legacy alias for GraphvizDotGenerator."""
    pass


# Also maintain the legacy class name for compatibility
class GraphVizGenerator(GraphvizDotGenerator):
    """Legacy alias for GraphvizDotGenerator with original naming."""
    pass
