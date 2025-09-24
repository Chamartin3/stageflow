"""Mermaid diagram generation for StageFlow."""

from stageflow.core.process import Process


class MermaidGenerator:
    """
    Generator for Mermaid flowchart diagrams from StageFlow processes.

    Creates Mermaid-compatible markdown for visualizing process flows,
    stages, gates, and locks.
    """

    def __init__(self):
        """Initialize Mermaid generator."""
        self.node_counter = 0

    def generate_process_diagram(self, process: Process, include_details: bool = False) -> str:
        """
        Generate Mermaid flowchart for a process.

        Args:
            process: Process to visualize
            include_details: Whether to include gate and lock details

        Returns:
            Mermaid markdown string
        """
        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")
        lines.append(f"    Start([Start: {process.name}])")

        # Generate nodes for each stage
        stage_nodes = {}
        for i, stage_name in enumerate(process.stage_order):
            stage = process.get_stage(stage_name)
            if not stage:
                continue

            node_id = f"S{i}"
            stage_nodes[stage_name] = node_id

            # Create stage node
            if include_details and stage.gates:
                gate_info = f"<br/>Gates: {len(stage.gates)}"
                lines.append(f"    {node_id}[{stage.name}{gate_info}]")
            else:
                lines.append(f"    {node_id}[{stage.name}]")

        # Connect stages
        prev_node = "Start"
        for i, stage_name in enumerate(process.stage_order):
            if stage_name in stage_nodes:
                current_node = stage_nodes[stage_name]
                lines.append(f"    {prev_node} --> {current_node}")
                prev_node = current_node

        # Add end node
        lines.append("    End([Complete])")
        lines.append(f"    {prev_node} --> End")

        # Add gate details if requested
        if include_details:
            lines.append("")
            lines.append("    %% Gate Details")
            for stage_name in process.stage_order:
                stage = process.get_stage(stage_name)
                if not stage or not stage.gates:
                    continue

                stage_node = stage_nodes[stage_name]
                for j, gate in enumerate(stage.gates):
                    gate_node = f"G{stage_node}{j}"
                    lock_count = f"Locks: {len(gate.locks)}"
                    lines.append(f"    {gate_node}[{gate.name}<br/>{lock_count}]")
                    lines.append(f"    {stage_node} -.-> {gate_node}")

        # Add styling
        lines.append("")
        lines.append("    %% Styling")
        lines.append("    classDef startEnd fill:#e1f5fe")
        lines.append("    classDef stage fill:#f3e5f5")
        lines.append("    classDef gate fill:#e8f5e8")
        lines.append("")
        lines.append("    class Start,End startEnd")

        # Apply stage styling
        for stage_node in stage_nodes.values():
            lines.append(f"    class {stage_node} stage")

        lines.append("```")
        return "\n".join(lines)

    def generate_stage_detail(self, stage, include_locks: bool = True) -> str:
        """
        Generate detailed Mermaid diagram for a single stage.

        Args:
            stage: Stage to visualize
            include_locks: Whether to include lock details

        Returns:
            Mermaid markdown string
        """
        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")
        lines.append(f"    Stage[{stage.name}]")

        if not stage.gates:
            lines.append("    Stage --> NoGates[No Gates Defined]")
        else:
            for i, gate in enumerate(stage.gates):
                gate_node = f"G{i}"
                lines.append(f"    {gate_node}[Gate: {gate.name}]")
                lines.append(f"    Stage --> {gate_node}")

                if include_locks and gate.locks:
                    for j, lock in enumerate(gate.locks):
                        lock_node = f"L{i}{j}"
                        lock_desc = f"{lock.property_path}<br/>{lock.lock_type.value}"
                        if lock.expected_value is not None:
                            lock_desc += f"<br/>Value: {lock.expected_value}"
                        lines.append(f"    {lock_node}[{lock_desc}]")
                        lines.append(f"    {gate_node} --> {lock_node}")

        # Add styling
        lines.append("")
        lines.append("    classDef stage fill:#f3e5f5")
        lines.append("    classDef gate fill:#e8f5e8")
        lines.append("    classDef lock fill:#fff3e0")
        lines.append("")
        lines.append("    class Stage stage")

        # Apply gate styling
        for i in range(len(stage.gates)):
            lines.append(f"    class G{i} gate")

        # Apply lock styling
        for i, gate in enumerate(stage.gates):
            for j in range(len(gate.locks)):
                lines.append(f"    class L{i}{j} lock")

        lines.append("```")
        return "\n".join(lines)
