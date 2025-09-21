"""Mermaid diagram generation for StageFlow processes."""


from stageflow.core.stage import Stage


class MermaidGenerator:
    """Generates Mermaid diagrams for process visualization."""

    def __init__(self):
        self._indent = "    "

    def generate_process_flow(self, stages: list[Stage], process_name: str = "Process") -> str:
        """
        Generate Mermaid flowchart for process stages.

        Args:
            stages: List of stages in the process
            process_name: Name of the process

        Returns:
            Mermaid diagram as string
        """
        lines = [
            "```mermaid",
            "flowchart TD",
            f'{self._indent}subgraph "{process_name}"',
        ]

        # Add nodes for each stage
        for i, stage in enumerate(stages):
            stage_id = f"S{i}"
            stage_label = stage.name.replace(" ", "_")
            lines.append(f'{self._indent}{self._indent}{stage_id}["{stage_label}"]')

        # Add connections between stages
        for i in range(len(stages) - 1):
            current_id = f"S{i}"
            next_id = f"S{i + 1}"
            lines.append(f"{self._indent}{self._indent}{current_id} --> {next_id}")

        lines.extend([
            f"{self._indent}end",
            "```"
        ])

        return "\n".join(lines)

    def generate_stage_detail(self, stage: Stage) -> str:
        """
        Generate detailed Mermaid diagram for a single stage.

        Args:
            stage: Stage to visualize

        Returns:
            Mermaid diagram showing stage gates and locks
        """
        lines = [
            "```mermaid",
            "flowchart LR",
            f'{self._indent}subgraph "Stage: {stage.name}"',
        ]

        # Add stage node
        lines.append(f'{self._indent}{self._indent}STAGE["{stage.name}"]')

        # Add gates
        for i, gate in enumerate(stage.gates):
            gate_id = f"G{i}"
            gate_label = gate.name.replace(" ", "_")
            lines.append(f'{self._indent}{self._indent}{gate_id}["{gate_label}"]')
            lines.append(f"{self._indent}{self._indent}STAGE --> {gate_id}")

            # Add locks for this gate
            for j, lock in enumerate(gate.locks):
                lock_id = f"L{i}_{j}"
                lock_label = f"{lock.type.value}_{lock.property}".replace(" ", "_")
                lines.append(f'{self._indent}{self._indent}{lock_id}["{lock_label}"]')
                lines.append(f"{self._indent}{self._indent}{gate_id} --> {lock_id}")

        lines.extend([
            f"{self._indent}end",
            "```"
        ])

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
