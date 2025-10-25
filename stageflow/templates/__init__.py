"""
Process Templates Module

Provides template definitions and loading functionality for creating new processes.
Templates are stored as YAML files in this directory and accessed via the ProcessTemplate enum.
"""

import copy
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class ProcessTemplate(str, Enum):
    """
    Enumeration of available process templates.

    Each template provides a pre-configured process structure for common workflows.
    """
    BASIC = "basic"
    APPROVAL = "approval"
    ONBOARDING = "onboarding"

    @classmethod
    def list_templates(cls) -> list[str]:
        """Get list of all available template names."""
        return [template.value for template in cls]

    @classmethod
    def is_valid(cls, template_name: str) -> bool:
        """Check if a template name is valid."""
        return template_name in cls.list_templates()

    @classmethod
    def get_default(cls) -> "ProcessTemplate":
        """Get the default template."""
        return cls.BASIC


def get_template_path(template: ProcessTemplate | str) -> Path:
    """
    Get the file path for a template.

    Args:
        template: ProcessTemplate enum or template name string

    Returns:
        Path to the template YAML file

    Raises:
        ValueError: If template name is invalid
    """
    # Extract the template name string
    if isinstance(template, ProcessTemplate):
        template_name = template.value
    elif isinstance(template, str):
        if not ProcessTemplate.is_valid(template):
            available = ", ".join(ProcessTemplate.list_templates())
            raise ValueError(f"Invalid template '{template}'. Available templates: {available}")
        template_name = template
    else:
        raise TypeError(f"template must be ProcessTemplate or str, not {type(template).__name__}")

    template_dir = Path(__file__).parent
    template_path = template_dir / f"{template_name}.yaml"

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    return template_path


def load_template(template: ProcessTemplate | str) -> dict[str, Any]:
    """
    Load a process template from file.

    Args:
        template: ProcessTemplate enum or template name string

    Returns:
        Template configuration dictionary

    Raises:
        ValueError: If template name is invalid
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_template_path(template)

    yaml = YAML()
    with template_path.open('r') as f:
        template_data = yaml.load(f)

    return template_data


def generate_process_from_template(
    process_name: str,
    template: ProcessTemplate | str = ProcessTemplate.BASIC
) -> dict[str, Any]:
    """
    Generate a complete process schema from a template.

    Args:
        process_name: Name for the new process
        template: ProcessTemplate enum or template name string (default: BASIC)

    Returns:
        Complete process schema dictionary ready to be used or saved

    Raises:
        ValueError: If template name is invalid
        FileNotFoundError: If template file doesn't exist
    """
    template_data = load_template(template)

    # Create a deep copy to avoid modifying the original
    schema = copy.deepcopy(template_data)

    # Populate the process name in the description
    description_template = schema.pop("description_template", "{process_name}")
    description = description_template.format(process_name=process_name)

    # Build the final process schema
    result = {
        "name": process_name,
        "description": description,
        "stages": schema["stages"],
        "initial_stage": schema["initial_stage"],
        "final_stage": schema["final_stage"]
    }

    return result


# Export public API
__all__ = [
    "ProcessTemplate",
    "get_template_path",
    "load_template",
    "generate_process_from_template"
]
