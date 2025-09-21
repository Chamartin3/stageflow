"""GraphViz diagram generation for StageFlow processes."""


from stageflow.core.stage import Stage


class GraphVizGenerator:
    """Generates GraphViz DOT diagrams for process visualization."""

    def __init__(self):
        self._indent = "    "

    def generate_process_flow(self, stages: list[Stage], process_name: str = "Process") -> str:
        """
        Generate GraphViz DOT diagram for process stages.

        Args:
            stages: List of stages in the process
            process_name: Name of the process

        Returns:
            GraphViz DOT diagram as string
        """
        lines = [
            "digraph Process {",
            f'{self._indent}label="{process_name}";',
            f"{self._indent}rankdir=LR;",
            f"{self._indent}node [shape=box, style=rounded];",
            "",
        ]

        # Add nodes for each stage
        for i, stage in enumerate(stages):
            stage_id = f"stage_{i}"
            stage_label = stage.name
            lines.append(f'{self._indent}{stage_id} [label="{stage_label}"];')

        lines.append("")

        # Add connections between stages
        for i in range(len(stages) - 1):
            current_id = f"stage_{i}"
            next_id = f"stage_{i + 1}"
            lines.append(f"{self._indent}{current_id} -> {next_id};")

        lines.append("}")
        return "\n".join(lines)

    def generate_stage_detail(self, stage: Stage) -> str:
        """
        Generate detailed GraphViz diagram for a single stage.

        Args:
            stage: Stage to visualize

        Returns:
            GraphViz diagram showing stage gates and locks
        """
        lines = [
            "digraph StageDetail {",
            f'{self._indent}label="Stage: {stage.name}";',
            f"{self._indent}rankdir=TD;",
            "",
        ]

        # Define node styles
        lines.extend([
            f"{self._indent}node [shape=box, style=rounded];",
            f"{self._indent}stage [label=\"{stage.name}\", style=filled, fillcolor=lightblue];",
            "",
        ])

        # Add gates
        gate_nodes = []
        for i, gate in enumerate(stage.gates):
            gate_id = f"gate_{i}"
            gate_nodes.append(gate_id)
            gate_label = gate.name
            lines.append(f'{self._indent}{gate_id} [label="{gate_label}", style=filled, fillcolor=lightgreen];')
            lines.append(f"{self._indent}stage -> {gate_id};")

            # Add locks for this gate
            for j, lock in enumerate(gate.locks):
                lock_id = f"lock_{i}_{j}"
                lock_label = f"{lock.type.value}\\n{lock.property}"
                lines.append(f'{self._indent}{lock_id} [label="{lock_label}", shape=ellipse, style=filled, fillcolor=lightyellow];')
                lines.append(f"{self._indent}{gate_id} -> {lock_id};")

        lines.append("}")
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
