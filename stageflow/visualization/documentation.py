"""Process documentation generator for StageFlow."""

import re
from pathlib import Path
from typing import Any

from stageflow.gate import Gate
from stageflow.models import ActionDefinition
from stageflow.process import Process
from stageflow.stage import Stage
from stageflow.visualization.mermaid import MermaidDiagramGenerator


class ProcessDocumentGenerator:
    """
    Generate comprehensive markdown documentation for StageFlow processes.

    Uses template files to render process, stage, gate, and action documentation.
    Supports both single-file and split-file output modes.
    """

    DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "doc_templates"

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize generator with templates directory.

        Args:
            templates_dir: Custom templates directory. Uses default if None.
        """
        self.templates_dir = templates_dir or self.DEFAULT_TEMPLATES_DIR
        self._templates: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all template files from templates directory."""
        template_files = ["process.md", "stage.md", "gate.md", "action.md", "lock.md"]
        for template_file in template_files:
            template_path = self.templates_dir / template_file
            if template_path.exists():
                self._templates[template_file.replace(".md", "")] = template_path.read_text()

    def _to_anchor(self, text: str) -> str:
        """Convert text to markdown anchor format.

        Uses Obsidian-style anchors (preserves case, encodes spaces as %20).
        """
        return text.replace(" ", "%20")

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with given context using simple substitution.

        Args:
            template_name: Name of template (without .md extension)
            context: Dictionary of values to substitute

        Returns:
            Rendered template string
        """
        template = self._templates.get(template_name, "")
        result = template

        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value) if value else "")

        return result

    def _format_schema(self, schema: dict[str, Any] | None, schema_type: str = "initial") -> str:
        """Format schema properties as human-readable tree structure."""
        if not schema:
            return "*(no properties defined)*"

        # Different icons/titles for initial vs final schema
        if schema_type == "initial":
            icon = "info"
            title = "⬇️ Input Schema"
        else:
            icon = "check"
            title = "⬆️ Output Schema"

        lines: list[str] = []

        def format_prop(name: str, prop_def: Any, indent: int = 0) -> None:
            """Format a property as nested markdown list."""
            # Extract type and required
            if isinstance(prop_def, dict):
                prop_type = prop_def.get("type", "any")
                required = prop_def.get("required", False)
                nested = prop_def.get("properties", {})
            else:
                prop_type = getattr(prop_def, "type", "any")
                if hasattr(prop_type, "value"):
                    prop_type = prop_type.value
                required = getattr(prop_def, "required", False)
                nested = getattr(prop_def, "properties", {}) or {}

            # Format the line with markdown list inside callout
            req_mark = "✱" if required else "○"
            indent_str = "\t" * indent
            lines.append(f"> {indent_str}- `{name}` ({prop_type}) {req_mark}")

            # Handle nested properties
            if nested:
                for child_name, child_prop in nested.items():
                    format_prop(child_name, child_prop, indent + 1)

        for prop_name, prop_def in schema.items():
            format_prop(prop_name, prop_def)

        # All inside callout
        tree_content = "\n".join(lines)
        return f"> [!{icon}] {title}\n{tree_content}\n>\n> ✱ required · ○ optional"

    # Lock type to icon/emoji mapping
    LOCK_CONFIG: dict[str, tuple[str, str]] = {
        "exists": ("tip", "✅"),
        "equals": ("info", "🎯"),
        "not_empty": ("tip", "📝"),
        "type_check": ("warning", "🔤"),
        "greater_than": ("note", "📈"),
        "less_than": ("note", "📉"),
        "range": ("note", "📊"),
        "regex": ("warning", "🔍"),
        "contains": ("info", "📦"),
        "length": ("note", "📏"),
        "in_list": ("info", "📋"),
        "not_in_list": ("caution", "🚫"),
        "conditional": ("important", "🔀"),
        "or_logic": ("important", "🔃"),
    }

    def _render_lock(self, lock: Any) -> str:
        """Render a single lock using the lock template."""
        lock_type = lock.lock_type.value if hasattr(lock, "lock_type") else str(type(lock).__name__)
        property_path = getattr(lock, "property_path", "")
        expected = getattr(lock, "expected_value", None)
        error_msg = getattr(lock, "error_message", None)

        # Get icon and emoji for lock type
        icon, emoji = self.LOCK_CONFIG.get(lock_type.lower(), ("note", "🔒"))

        details_parts = []
        if expected is not None:
            details_parts.append(f"  - Expected: `{expected}`")
        if error_msg:
            details_parts.append(f"  - Message: {error_msg}")
        lock_details = "\n".join(details_parts)

        return self._render_template("lock", {
            "lock_type": lock_type.upper(),
            "icon": icon,
            "emoji": emoji,
            "property_path": property_path,
            "lock_details": lock_details,
        })

    def _render_gate(self, gate: Gate, process: Process) -> str:
        """Render a single gate using the gate template."""
        # Render locks
        locks_content = ""
        if hasattr(gate, "_locks") and gate._locks:
            locks_content = "\n".join(self._render_lock(lock) for lock in gate._locks)
        else:
            locks_content = "*(no locks defined)*"

        # Get final schema (cumulative schema at target stage)
        final_schema = process.get_schema(gate.target_stage, partial=False)
        final_schema_str = self._format_schema(final_schema, schema_type="final")

        # Get target stage name and create link
        target_stage = process.get_stage(gate.target_stage)
        target_stage_name = target_stage.name if target_stage else gate.target_stage
        target_stage_slug = self._to_anchor(target_stage_name)

        return self._render_template("gate", {
            "name": gate.name,
            "description": getattr(gate, "description", ""),
            "target_stage": gate.target_stage,
            "target_stage_name": target_stage_name,
            "target_stage_link": f"#{target_stage_slug}",
            "locks": locks_content,
            "final_schema": final_schema_str,
        })

    # Action type to emoji mapping
    ACTION_EMOJIS: dict[str, str] = {
        "update": "✏️",
        "execute": "⚡",
        "transition": "➡️",
    }

    def _render_action(self, action: ActionDefinition) -> str:
        """Render a single action using the action template."""
        name = action.get("name", "Action")
        description = action.get("description", "")
        action_type = action.get("type", "execute")
        related_props = action.get("related_properties", [])
        instructions = action.get("instructions", [])

        emoji = self.ACTION_EMOJIS.get(action_type, "📌")

        # Format instructions as multiline
        instructions_str = ""
        if instructions:
            instructions_str = "\n".join(f"> - {inst}" for inst in instructions)

        # Format properties as nested list (like schema)
        if related_props:
            props_lines = [">", "> **Properties:**"]
            # Build tree from dot-notation paths
            tree: dict[str, Any] = {}
            for prop in related_props:
                parts = prop.split(".")
                current = tree
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            def render_tree(node: dict[str, Any], indent: int = 0) -> None:
                indent_str = "\t" * indent
                for key, children in node.items():
                    props_lines.append(f"> {indent_str}- `{key}`")
                    if children:
                        render_tree(children, indent + 1)

            render_tree(tree)
            props_str = "\n".join(props_lines)
        else:
            props_str = ">\n> **Properties:** *(none)*"

        return self._render_template("action", {
            "name": name,
            "emoji": emoji,
            "description": description,
            "action_type": action_type,
            "instructions": instructions_str,
            "related_properties": props_str,
        })

    def _render_stage(self, stage: Stage, process: Process) -> str:
        """Render a single stage using the stage template."""
        # Get initial schema for this stage
        initial_schema = stage.get_schema() if hasattr(stage, "get_schema") else {}
        initial_schema_str = self._format_schema(initial_schema)

        # Render actions
        actions_content = ""
        if stage.stage_actions:
            actions_content = "\n".join(
                self._render_action(action) for action in stage.stage_actions
            )
        else:
            actions_content = "*(no expected actions defined)*"

        # Create gate list with links
        gate_list_parts = []
        if stage.gates:
            for gate in stage.gates:
                target_stage_obj = process.get_stage(gate.target_stage)
                target_name = target_stage_obj.name if target_stage_obj else gate.target_stage
                target_slug = self._to_anchor(target_name)
                gate_slug = self._to_anchor(gate.name)
                gate_list_parts.append(f"- [{gate.name}](#{gate_slug}) → [{target_name}](#{target_slug})")
        gate_list = "\n".join(gate_list_parts) if gate_list_parts else ""

        # Render gates
        gates_content = ""
        if stage.gates:
            gates_content = "\n\n".join(
                self._render_gate(gate, process) for gate in stage.gates
            )
        else:
            gates_content = "*(no gates - this is a terminal stage)*"

        return self._render_template("stage", {
            "name": stage.name,
            "description": stage.description or "*(no description)*",
            "initial_schema": initial_schema_str,
            "actions": actions_content,
            "gate_list": gate_list,
            "gates": gates_content,
        })

    def generate(self, process: Process) -> str:
        """
        Generate complete documentation for a process as a single markdown file.

        Args:
            process: Process to document

        Returns:
            Complete markdown documentation string
        """
        # Generate mermaid diagram
        diagram_gen = MermaidDiagramGenerator()
        diagram = diagram_gen.generate_process_diagram(process, style="detailed")

        # Render all stages
        stage_order = process.get_sorted_stages()
        stages_content_parts = []
        stage_list_parts = []
        for stage_name in stage_order:
            stage = process.get_stage(stage_name)
            if stage:
                stages_content_parts.append(self._render_stage(stage, process))
                # Create anchor-friendly slug from stage name
                slug = self._to_anchor(stage.name)
                stage_list_parts.append(f"1. [{stage.name}](#{slug})")
        stages_content = "\n\n".join(stages_content_parts)
        stage_list = "\n".join(stage_list_parts)

        # Get initial and final stage names
        initial_stage_name = process.initial_stage.name if process.initial_stage else "*(not set)*"
        final_stage_name = process.final_stage.name if process.final_stage else "*(not set)*"
        regression_policy_raw = getattr(process, "regression_policy", "warn")
        regression_policy = getattr(regression_policy_raw, "value", str(regression_policy_raw))

        return self._render_template("process", {
            "name": process.name,
            "description": getattr(process, "description", "") or "*(no description)*",
            "initial_stage": initial_stage_name,
            "final_stage": final_stage_name,
            "regression_policy": regression_policy,
            "stage_list": stage_list,
            "diagram": diagram,
            "stages": stages_content,
        })

    def generate_split(self, process: Process, output_dir: Path) -> dict[str, str]:
        """
        Generate documentation split into separate files per stage.

        Args:
            process: Process to document
            output_dir: Directory to write files to

        Returns:
            Dictionary mapping file paths to content
        """
        files: dict[str, str] = {}

        # Generate mermaid diagram
        diagram_gen = MermaidDiagramGenerator()
        diagram = diagram_gen.generate_process_diagram(process, style="detailed")

        # Get stage order and create links
        stage_order = process.get_sorted_stages()
        stage_links_parts = []
        for s in stage_order:
            stage = process.get_stage(s)
            if stage:
                stage_links_parts.append(f"- [{stage.name}](stages/{s}.md)")
        stage_links = "\n".join(stage_links_parts)

        # Get initial and final stage names
        initial_stage_name = process.initial_stage.name if process.initial_stage else "*(not set)*"
        final_stage_name = process.final_stage.name if process.final_stage else "*(not set)*"
        regression_policy_raw = getattr(process, "regression_policy", "warn")
        regression_policy = getattr(regression_policy_raw, "value", str(regression_policy_raw))

        # Create index file
        index_content = self._render_template("process", {
            "name": process.name,
            "description": getattr(process, "description", "") or "*(no description)*",
            "initial_stage": initial_stage_name,
            "final_stage": final_stage_name,
            "regression_policy": regression_policy,
            "diagram": diagram,
            "stages": stage_links,
        })
        files[str(output_dir / "index.md")] = index_content

        # Create individual stage files
        stages_dir = output_dir / "stages"
        for stage_name in stage_order:
            stage = process.get_stage(stage_name)
            if stage:
                stage_content = self._render_stage(stage, process)
                # Add navigation header
                stage_content = f"[← Back to Process](../index.md)\n\n{stage_content}"
                files[str(stages_dir / f"{stage_name}.md")] = stage_content

        return files
