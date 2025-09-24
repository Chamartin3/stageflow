"""Graphviz DOT generation for StageFlow."""

from stageflow.core.process import Process


class GraphvizGenerator:
    """
    Generator for Graphviz DOT diagrams from StageFlow processes.

    Creates DOT format output for visualizing process flows with
    professional graph layouts.
    """

    def __init__(self):
        """Initialize Graphviz generator."""
        pass

    def generate_process_diagram(self, process: Process, include_details: bool = False) -> str:
        """
        Generate Graphviz DOT diagram for a process.

        Args:
            process: Process to visualize
            include_details: Whether to include gate and lock details

        Returns:
            DOT format string
        """
        lines = []
        lines.append("digraph StageFlow {")
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # Add title
        lines.append(f'    label="{process.name}";')
        lines.append('    labelloc="t";')
        lines.append('    fontsize=16;')
        lines.append("")

        # Define nodes
        lines.append("    // Nodes")
        lines.append('    start [label="Start", shape=ellipse, style=filled, fillcolor=lightblue];')

        stage_nodes = {}
        for i, stage_name in enumerate(process.stage_order):
            stage = process.get_stage(stage_name)
            if not stage:
                continue

            node_id = f"stage_{i}"
            stage_nodes[stage_name] = node_id

            if include_details and stage.gates:
                gate_count = len(stage.gates)
                label = f"{stage.name}\\n({gate_count} gates)"
            else:
                label = stage.name

            lines.append(f'    {node_id} [label="{label}", style=filled, fillcolor=lightgreen];')

        lines.append('    end [label="Complete", shape=ellipse, style=filled, fillcolor=lightcoral];')
        lines.append("")

        # Define edges
        lines.append("    // Edges")
        prev_node = "start"
        for stage_name in process.stage_order:
            if stage_name in stage_nodes:
                current_node = stage_nodes[stage_name]
                lines.append(f"    {prev_node} -> {current_node};")
                prev_node = current_node

        lines.append(f"    {prev_node} -> end;")

        # Add gate details if requested
        if include_details:
            lines.append("")
            lines.append("    // Gate Details")
            for stage_name in process.stage_order:
                stage = process.get_stage(stage_name)
                if not stage or not stage.gates:
                    continue

                stage_node = stage_nodes[stage_name]
                lines.append(f"    subgraph cluster_{stage_node} {{")
                lines.append(f'        label="{stage.name} Gates";')
                lines.append("        style=dashed;")
                lines.append("        color=gray;")

                for j, gate in enumerate(stage.gates):
                    gate_node = f"gate_{stage_node}_{j}"
                    gate_label = f"{gate.name}\\n{len(gate.locks)} locks"
                    lines.append(f'        {gate_node} [label="{gate_label}", style=filled, fillcolor=lightyellow];')

                lines.append("    }")

        lines.append("}")
        return "\n".join(lines)

    def generate_stage_detail(self, stage, include_locks: bool = True) -> str:
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
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # Add title
        lines.append(f'    label="Stage: {stage.name}";')
        lines.append('    labelloc="t";')
        lines.append('    fontsize=16;')
        lines.append("")

        # Stage node
        lines.append(f'    stage [label="{stage.name}", style=filled, fillcolor=lightgreen];')

        if not stage.gates:
            lines.append('    nogates [label="No Gates", style=filled, fillcolor=lightgray];')
            lines.append("    stage -> nogates;")
        else:
            # Gate nodes
            for i, gate in enumerate(stage.gates):
                gate_node = f"gate_{i}"
                gate_label = f"{gate.name}"
                lines.append(f'    {gate_node} [label="{gate_label}", style=filled, fillcolor=lightyellow];')
                lines.append(f"    stage -> {gate_node};")

                if include_locks and gate.locks:
                    # Lock nodes
                    for j, lock in enumerate(gate.locks):
                        lock_node = f"lock_{i}_{j}"
                        lock_label = f"{lock.property_path}\\n{lock.lock_type.value}"
                        if lock.expected_value is not None:
                            lock_label += f"\\nValue: {lock.expected_value}"

                        lines.append(f'    {lock_node} [label="{lock_label}", style=filled, fillcolor=lightcyan];')
                        lines.append(f"    {gate_node} -> {lock_node};")

        lines.append("}")
        return "\n".join(lines)
