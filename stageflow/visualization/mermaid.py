"""Mermaid diagram generation for StageFlow."""

from typing import Any

# Use relative imports for the process models
from stageflow.lock import SimpleLock
from stageflow.process import Process


class MermaidDiagramGenerator:
    """
    Enhanced generator for Mermaid flowchart diagrams from StageFlow processes.

    Creates comprehensive Mermaid-compatible markdown for visualizing process flows,
    stages, gates, and locks with multiple diagram types and styling options.
    """

    def __init__(self):
        """Initialize Mermaid generator."""
        self.node_counter = 0

    def generate_process_diagram(
        self, process: Process, style: str = "overview", include_details: bool = False
    ) -> str:
        """
        Generate Mermaid flowchart for a process with enhanced visualization.

        Args:
            process: Process to visualize
            style: Diagram style - "overview", "detailed", or "full"
            include_details: Whether to include gate and lock details (legacy parameter)

        Returns:
            Mermaid markdown string
        """
        # Map legacy parameter to style
        if include_details and style == "overview":
            style = "detailed"

        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")

        # Add process title as a subgraph if style permits
        if style in ["detailed", "full"]:
            lines.append(f'    subgraph "Process: {process.name}"')
            lines.append("    direction TB")

        # Generate stage nodes with proper transitions
        stage_nodes = {}
        stage_order = process.get_sorted_stages()
        for i, stage_name in enumerate(stage_order):
            stage = process.get_stage(stage_name)
            if not stage:
                continue

            node_id = f"S{i}"
            stage_nodes[stage_name] = node_id

            # Create stage node with styling based on type
            stage_label = self._generate_stage_label(stage, style)

            # Determine stage type for styling
            is_initial = (
                (stage_name == process.initial_stage._id)
                if process.initial_stage
                else (i == 0)
            )
            is_final = (
                (stage_name == process.final_stage._id)
                if process.final_stage
                else (i == len(stage_order) - 1)
            )

            if is_initial:
                lines.append(f"    {node_id}[{stage_label}]")
            elif is_final:
                lines.append(f"    {node_id}[{stage_label}]")
            else:
                lines.append(f"    {node_id}[{stage_label}]")

        # Generate stage transitions based on actual gate relationships
        for stage_name in stage_order:
            stage = process.get_stage(stage_name)
            if not stage or not stage.gates:
                continue

            current_node = stage_nodes[stage_name]

            # Generate transitions for each gate from this stage
            for gate in stage.gates:
                if hasattr(gate, "target_stage") and gate.target_stage:
                    target_stage_name = gate.target_stage
                    # Only create transition if target stage exists in our nodes
                    if target_stage_name in stage_nodes:
                        target_node = stage_nodes[target_stage_name]

                        # Generate transition label based on gate
                        gate_label = self._generate_gate_label(gate, style)
                        if gate_label and style in ["detailed", "full"]:
                            lines.append(
                                f"    {current_node} -->|{gate_label}| {target_node}"
                            )
                        else:
                            lines.append(f"    {current_node} --> {target_node}")

        # Add gate details as subgraphs for full style
        if style == "full":
            lines.append("")
            lines.append("    %% Gate Details")
            for stage_name in stage_order:
                stage = process.get_stage(stage_name)
                if not stage or not stage.gates:
                    continue

                stage_node = stage_nodes[stage_name]
                lines.append(f'    subgraph G{stage_node} ["Gates for {stage.name}"]')

                for j, gate in enumerate(stage.gates):
                    gate_node = f"G{stage_node}_{j}"
                    gate_label = self._generate_gate_label(gate, style)
                    lines.append(f"        {gate_node}[{gate_label}]")

                    # Add lock details if gate has locks
                    if hasattr(gate, "_locks") and gate._locks:
                        try:
                            # Ensure locks is iterable (handles Mock objects)
                            lock_list = (
                                list(gate._locks)
                                if hasattr(gate._locks, "__iter__")
                                else []
                            )
                            for k, lock in enumerate(lock_list):
                                lock_node = f"L{gate_node}_{k}"
                                lock_label = (
                                    f"{lock.property_path}\\n{lock.lock_type.value}"
                                )
                                if isinstance(lock, SimpleLock) and lock.expected_value is not None:
                                    lock_label += f"\\n= {lock.expected_value}"
                                lines.append(f"        {lock_node}[{lock_label}]")
                                lines.append(f"        {gate_node} --> {lock_node}")
                        except (TypeError, AttributeError):
                            # Skip if locks can't be processed (e.g., in tests with mocks)
                            pass

                lines.append("    end")

        # Close subgraph if opened
        if style in ["detailed", "full"]:
            lines.append("    end")

        # Add comprehensive styling
        lines.extend(self._generate_styling(stage_nodes, process, style))

        lines.append("```")
        return "\n".join(lines)

    def generate_stage_detail(self, stage: Any, include_locks: bool = True) -> str:
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
                gate_label = self._generate_gate_label(gate, "full")
                lines.append(f"    {gate_node}[{gate_label}]")
                lines.append(f"    Stage --> {gate_node}")

                if include_locks and hasattr(gate, "locks") and gate.locks:
                    for j, lock in enumerate(gate.locks):
                        lock_node = f"L{i}_{j}"
                        lock_desc = f"{lock.property}<br/>{lock.type.value}"
                        if (
                            hasattr(lock, "expected_value")
                            and lock.expected_value is not None
                        ):
                            lock_desc += f"<br/>Expected: {lock.expected_value}"
                        lines.append(f"    {lock_node}[{lock_desc}]")
                        lines.append(f"    {gate_node} --> {lock_node}")

        # Add styling
        lines.append("")
        lines.append("    %% Styling")
        lines.append("    classDef stage fill:#f3e5f5")
        lines.append("    classDef gate fill:#e8f5e8")
        lines.append("    classDef lock fill:#fff3e0")
        lines.append("    classDef nogate fill:#f5f5f5")
        lines.append("")
        lines.append("    class Stage stage")

        # Apply gate styling
        for i in range(len(stage.gates)):
            lines.append(f"    class G{i} gate")

        # Apply lock styling
        for i, gate in enumerate(stage.gates):
            if hasattr(gate, "locks") and gate.locks:
                for j in range(len(gate.locks)):
                    lines.append(f"    class L{i}_{j} lock")

        if not stage.gates:
            lines.append("    class NoGates nogate")

        lines.append("```")
        return "\n".join(lines)

    def generate_gate_flowchart(self, gates: list[Any]) -> str:
        """
        Generate Mermaid flowchart for gate relationships.

        Args:
            gates: List of gates to visualize

        Returns:
            Mermaid markdown string
        """
        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")
        lines.append("    Start([Gate Evaluation])")

        if not gates:
            lines.append("    Start --> NoGates[No Gates Defined]")
        else:
            for i, gate in enumerate(gates):
                gate_node = f"G{i}"
                gate_label = self._generate_gate_label(gate, "detailed")
                lines.append(f"    {gate_node}[{gate_label}]")

                if i == 0:
                    lines.append(f"    Start --> {gate_node}")
                else:
                    prev_gate = f"G{i - 1}"
                    lines.append(f"    {prev_gate} --> {gate_node}")

        lines.append("    End([Evaluation Complete])")
        if gates:
            last_gate = f"G{len(gates) - 1}"
            lines.append(f"    {last_gate} --> End")
        else:
            lines.append("    NoGates --> End")

        # Add styling
        lines.append("")
        lines.append("    %% Styling")
        lines.append("    classDef startEnd fill:#e1f5fe")
        lines.append("    classDef gate fill:#e8f5e8")
        lines.append("    classDef nogate fill:#f5f5f5")
        lines.append("")
        lines.append("    class Start,End startEnd")

        for i in range(len(gates)):
            lines.append(f"    class G{i} gate")

        if not gates:
            lines.append("    class NoGates nogate")

        lines.append("```")
        return "\n".join(lines)

    def generate_state_flow(self) -> str:
        """
        Generate Mermaid diagram showing the 7-state evaluation flow.

        Returns:
            Mermaid diagram of state transitions
        """
        return """```mermaid
flowchart TD
    SCOPING[Scoping]
    FULFILLING[Fulfilling]
    QUALIFYING[Qualifying]
    AWAITING[Awaiting]
    ADVANCING[Advancing]
    REGRESSING[Regressing]
    COMPLETED[Completed]

    SCOPING --> FULFILLING
    FULFILLING --> QUALIFYING
    FULFILLING --> AWAITING
    QUALIFYING --> ADVANCING
    AWAITING --> FULFILLING
    AWAITING --> QUALIFYING
    ADVANCING --> COMPLETED
    QUALIFYING --> REGRESSING
    FULFILLING --> REGRESSING
    REGRESSING --> SCOPING
    REGRESSING --> FULFILLING
```"""

    def _generate_stage_label(self, stage: Any, style: str) -> str:
        """Generate appropriate label for a stage based on style."""
        if style == "overview":
            return stage.name
        elif style == "detailed":
            gate_count = len(stage.gates) if stage.gates else 0
            if gate_count > 0:
                return f"{stage.name}<br/>{gate_count} gate(s)"
            else:
                return f"{stage.name}<br/>No gates"
        else:  # full
            parts = [stage.name]
            if stage.gates:
                parts.append(f"{len(stage.gates)} gate(s)")
            if hasattr(stage, "schema") and stage.schema:
                parts.append("Schema required")
            return "<br/>".join(parts)

    def _generate_transition_label(self, stage: Any, style: str) -> str:
        """Generate transition label based on stage gates."""
        if style == "overview":
            return ""
        elif not stage.gates:
            return "auto"
        elif len(stage.gates) == 1:
            gate_name = (
                list(stage.gates.keys())[0]
                if isinstance(stage.gates, dict)
                else stage.gates[0].name
            )
            if style == "detailed":
                return gate_name
            else:  # full
                return f"{gate_name}<br/>({self._get_gate_summary_from_stage(stage)})"
        else:
            if style == "detailed":
                return f"{len(stage.gates)} gates"
            else:  # full
                return f"{len(stage.gates)} gates<br/>(all must pass)"

    def _generate_gate_label(self, gate: Any, style: str) -> str:
        """Generate appropriate label for a gate."""
        gate_name = gate if isinstance(gate, str) else getattr(gate, "name", str(gate))

        if style == "overview":
            return gate_name
        elif style == "detailed":
            return f"{gate_name}<br/>gate"
        else:  # full
            return f"{gate_name}<br/>validation gate"

    def _get_gate_summary_from_stage(self, stage: Any) -> str:
        """Get a summary of gates from a stage."""
        if not stage.gates:
            return "No gates"
        return f"{len(stage.gates)} gates"

    def _generate_styling(
        self, stage_nodes: dict[str, str], process: Process, style: str
    ) -> list[str]:
        """Generate comprehensive styling for the diagram."""
        lines = []
        lines.append("")
        lines.append("    %% Styling")
        lines.append(
            "    classDef initial fill:#e1f5fe,stroke:#01579b,stroke-width:2px"
        )
        lines.append("    classDef final fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px")
        lines.append("    classDef stage fill:#f3e5f5,stroke:#7b1fa2")
        lines.append("    classDef gate fill:#fff3e0,stroke:#ef6c00")
        lines.append("    classDef lock fill:#fce4ec,stroke:#c2185b")
        lines.append("")

        # Apply stage type styling
        stage_order = process.get_sorted_stages()
        for i, stage_name in enumerate(stage_order):
            if stage_name in stage_nodes:
                node_id = stage_nodes[stage_name]

                # Check actual initial and final stages from process
                is_initial = (
                    (stage_name == process.initial_stage._id)
                    if process.initial_stage
                    else (i == 0)
                )
                is_final = (
                    (stage_name == process.final_stage._id)
                    if process.final_stage
                    else (i == len(stage_order) - 1)
                )

                if is_initial:
                    lines.append(f"    class {node_id} initial")
                elif is_final:
                    lines.append(f"    class {node_id} final")
                else:
                    lines.append(f"    class {node_id} stage")

        return lines


# Maintain backward compatibility
class MermaidGenerator(MermaidDiagramGenerator):
    """Legacy alias for MermaidDiagramGenerator."""

    pass
