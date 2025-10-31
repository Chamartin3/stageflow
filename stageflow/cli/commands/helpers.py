"""Helper functions for formatting CLI output."""

from rich.console import Console

from stageflow.schema import ProcessWithErrors

console = Console()


def build_process_description(process):
    """Build process description dictionary for Process or ProcessWithErrors."""
    if isinstance(process, ProcessWithErrors):
        description = {
            "name": process.name,
            "description": process.description,
            "initial_stage": process.raw_config.get("initial_stage"),
            "final_stage": process.raw_config.get("final_stage"),
            "stages": [],
        }

        consistency_issues = [
            {"type": "validation_error", "description": error}
            for error in process.validation_errors
        ]

        description["valid"] = process.valid
        description["consistency_issues"] = consistency_issues

        stages = process.raw_config.get("stages", {})
        for stage_id, stage_config in stages.items():
            stage_info = {
                "id": stage_id,
                "name": stage_config.get("name", stage_id),
                "expected_properties": list(
                    stage_config.get("expected_properties", {}).keys()
                ),
                "gates": len(stage_config.get("gates", [])),
                "target_stages": [],
                "is_final": stage_config.get("is_final", False),
            }
            description["stages"].append(stage_info)

        return description

    else:
        description = {
            "name": process.name,
            "description": getattr(process, "description", ""),
            "initial_stage": process.initial_stage._id
            if process.initial_stage
            else None,
            "final_stage": process.final_stage._id if process.final_stage else None,
            "stages": [],
        }

        consistency_valid = (
            process.checker.valid
            if hasattr(process, "checker") and process.checker
            else True
        )
        consistency_issues = []
        if (
            hasattr(process, "checker")
            and process.checker
            and hasattr(process.checker, "issues")
        ):
            consistency_issues = [
                {"type": str(issue.issue_type), "description": issue.description}
                for issue in process.checker.issues
            ]

        description["valid"] = consistency_valid
        description["consistency_issues"] = consistency_issues

        visited = set()
        stage_order = []

        def collect_stages(stage_id):
            if stage_id in visited or not stage_id:
                return
            visited.add(stage_id)
            stage_order.append(stage_id)

            stage = process.get_stage(stage_id)
            if stage:
                for gate in stage.gates:
                    if hasattr(gate, "target_stage") and gate.target_stage:
                        collect_stages(gate.target_stage)

        if process.initial_stage:
            collect_stages(process.initial_stage._id)

        for stage in process.stages:
            if stage._id not in visited:
                stage_order.append(stage._id)

        for stage_id in stage_order:
            stage = process.get_stage(stage_id)
            if stage:
                target_stages = []
                for gate in stage.gates:
                    if hasattr(gate, "target_stage") and gate.target_stage:
                        if gate.target_stage not in target_stages:
                            target_stages.append(gate.target_stage)

                stage_info = {
                    "id": stage._id,
                    "name": stage.name,
                    "expected_properties": list(stage._base_schema.keys())
                    if stage._base_schema
                    else [],
                    "gates": len(stage.gates),
                    "target_stages": target_stages,
                    "is_final": stage.is_final,
                }
                description["stages"].append(stage_info)

    return description


def print_process_description(desc, process):
    """Print human-readable process description."""
    if desc["valid"]:
        status_icon = "✅"
        status_text = "Valid"
    else:
        status_icon = "❌"
        status_text = "Invalid"

    console.print(
        f"\n{status_icon} [bold]Process: {desc['name']}[/bold] ({status_text})"
    )
    if desc["description"]:
        console.print(f"   Description: {desc['description']}")
    console.print(f"   Initial Stage: {desc['initial_stage']}")
    console.print(f"   Final Stage: {desc['final_stage']}")
    console.print(f"   Total Stages: {len(desc['stages'])}\n")

    console.print("[bold]Stages:[/bold]")
    for i, stage in enumerate(desc["stages"]):
        prefix = "└─" if i == len(desc["stages"]) - 1 else "├─"
        final_marker = " (final)" if stage["is_final"] else ""

        if stage["target_stages"]:
            targets_text = f" → {', '.join(stage['target_stages'])}"
        else:
            targets_text = ""

        console.print(f"{prefix} {stage['name']}{targets_text}{final_marker}")

        if stage["expected_properties"]:
            console.print(
                f"   Expected properties: {', '.join(stage['expected_properties'])}"
            )

    if desc["consistency_issues"]:
        console.print()
        console.print("[red]❌ Consistency Issues:[/red]")
        for issue in desc["consistency_issues"]:
            console.print(f"   • {issue['description']}")
        console.print()
        console.print(
            "⚠️  This process is not valid for execution due to the above consistency issues."
        )


def print_expected_actions(actions_def, indent="   "):
    """Print enhanced expected_actions with name and instructions.

    Args:
        actions_def: List of ActionDefinition dictionaries
        indent: String prefix for indentation
    """
    if not actions_def:
        return

    console.print(f"\n{indent}📋 [bold]Expected Actions:[/bold]")

    for action in actions_def:
        name = action.get("name")
        description = action.get("description", "No description")
        instructions = action.get("instructions", [])
        related_properties = action.get("related_properties", [])

        # Display action name and description
        if name:
            console.print(f"\n{indent}  ▸ [cyan]{name}[/cyan]")
            console.print(f"{indent}    {description}")
        else:
            console.print(f"\n{indent}  ▸ {description}")

        # Display instructions if available
        if instructions:
            console.print(f"{indent}    [dim]Guidelines:[/dim]")
            for i, instruction in enumerate(instructions, 1):
                console.print(f"{indent}      {i}. {instruction}")

        # Display related properties if available
        if related_properties:
            props_str = ", ".join(related_properties)
            console.print(f"{indent}    [dim]Related properties:[/dim] {props_str}")


def print_evaluation_result(result):
    """Print human-readable evaluation result."""
    stage_result = result["stage_result"]
    status = stage_result.status
    current_stage = result["stage"]

    status_emoji = {
        "ready": "✅",
        "action_required": "⚠️",
        "invalid_schema": "❌",
    }.get(status, "❓")

    console.print(f"\n{status_emoji} [bold]Evaluation Result[/bold]")
    console.print(f"   Current Stage: {current_stage}")
    console.print(f"   Status: {status}")

    actions = stage_result.sugested_action
    if actions:
        console.print("   [yellow]Possible Transitions:[/yellow]")

        # Group actions by gate transitions for better readability
        for i, action in enumerate(actions):
            description = action.description

            # Check if this is a gate header (starts with "To transition via")
            if description.startswith("To transition via"):
                # Add spacing before new transition (except first one)
                if i > 0:
                    console.print()
                # Print the transition header with styling
                console.print(f"     [cyan]•[/cyan] [bold]{description}[/bold]")
            else:
                # This is a required action under the current gate
                # It already has indentation and arrow from the gate result
                console.print(f"       {description}")

    if status == "ready":
        passed_gates = [
            gate_name
            for gate_name, gate_result in stage_result.gate_results.items()
            if gate_result.passed
        ]
        if passed_gates:
            console.print(
                f"   [green]Passed Gate(s):[/green] {', '.join(passed_gates)}"
            )

    # Display enhanced expected_actions from stage definition
    expected_actions = result.get("expected_actions", [])
    if expected_actions and status == "action_required":
        print_expected_actions(expected_actions)
