"""
Common types and utilities for StageFlow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from rich.repr import auto


class ErrorType(Enum):
    PROCESS_VALIDATION = auto()

    def get_message(self) -> str:
        if self == self.PROCESS_VALIDATION:
            return "Invalid process definition"
        return ""


ErrorData = dict[str, str | list[str]]


class ErrorResultDict(TypedDict, total=False):
    type: str
    message: str  # Optional via total=False
    data: ErrorData


@dataclass
class ErrorResult:
    type: ErrorType
    data: ErrorData
    info: str | None

    def to_dict(self) -> ErrorResultDict:
        error_dict = ErrorResultDict(type=self.type.get_message(), data=self.data)
        if self.info:
            error_dict["message"] = self.info
        return error_dict


# ============================================================================
# Action Builder Utilities
# ============================================================================


def sanitize_action_name(name: str) -> str:
    """Sanitize action name for use in action ID.

    Replace spaces and special characters with underscores.

    Args:
        name: Original action name

    Returns:
        Sanitized name safe for IDs

    Examples:
        >>> sanitize_action_name("provide email")
        "provide_email"
        >>> sanitize_action_name("transition to profile")
        "transition_to_profile"
        >>> sanitize_action_name("resolve__email___verified")
        "resolve_email_verified"
    """
    import re

    # Replace spaces and special chars with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Remove duplicate underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores
    return sanitized.strip("_").lower()


def generate_action_name(
    action_type: "ActionType",  # type: ignore
    gate_name: str | None = None,
    target_stage: str | None = None,
    property_path: str | None = None,
    configured_name: str | None = None,
) -> str:
    """Generate a unique action name following naming conventions.

    Naming conventions:
    - Configured actions: Use configured name directly
    - Transition actions: "transition_to_{target_stage}"
    - Resolve validation: "resolve_{gate_name}"
    - Provide data: "provide_{property_path}" (dots replaced with underscores)

    Args:
        action_type: Type of action
        gate_name: Gate name (for resolve_validation, transition)
        target_stage: Target stage (for transition)
        property_path: Property path (for provide_data)
        configured_name: Configured name from YAML (for execute_action)

    Returns:
        Unique action name following conventions

    Examples:
        >>> from stageflow.models import ActionType
        >>> generate_action_name(ActionType.PROVIDE_DATA, property_path="email")
        "provide_email"
        >>> generate_action_name(ActionType.TRANSITION, target_stage="profile_setup")
        "transition_to_profile_setup"
        >>> generate_action_name(ActionType.RESOLVE_VALIDATION, gate_name="email_verified")
        "resolve_email_verified"
        >>> generate_action_name(ActionType.EXECUTE_ACTION, configured_name="send_email")
        "send_email"
    """
    from stageflow.models import ActionType

    if configured_name:
        return configured_name

    if action_type == ActionType.TRANSITION and target_stage:
        return f"transition_to_{target_stage}"

    if action_type == ActionType.RESOLVE_VALIDATION and gate_name:
        return f"resolve_{gate_name}"

    if action_type == ActionType.PROVIDE_DATA and property_path:
        # Replace dots with underscores for nested paths
        safe_path = property_path.replace(".", "_")
        return f"provide_{safe_path}"

    # Fallback
    return f"{action_type.value}_action"


def generate_action_id(
    index: int,
    stage_id: str,
    name: str,
) -> str:
    """Generate a unique, deterministic action ID.

    Format: {index}:{stage_id}:{action_name}

    Args:
        index: Sequential index within stage evaluation (0-based)
        stage_id: Current stage ID
        name: Action name (will be sanitized)

    Returns:
        Unique action ID

    Examples:
        >>> generate_action_id(0, "registration", "provide_email")
        "0:registration:provide_email"
        >>> generate_action_id(1, "email_verification", "transition to profile")
        "1:email_verification:transition_to_profile"
    """
    sanitized_name = sanitize_action_name(name)
    return f"{index}:{stage_id}:{sanitized_name}"


def ensure_unique_action_names(actions: list[dict]) -> list[dict]:
    """Ensure all action names in a list are unique.

    If duplicates found, append numeric suffix to subsequent occurrences.

    Args:
        actions: List of action dictionaries (mutable)

    Returns:
        Same list with unique names (modified in place)

    Examples:
        >>> actions = [
        ...     {"name": "provide_email"},
        ...     {"name": "provide_email"},
        ...     {"name": "provide_password"}
        ... ]
        >>> ensure_unique_action_names(actions)
        [{'name': 'provide_email'}, {'name': 'provide_email_2'}, {'name': 'provide_password'}]
    """
    seen_names: dict[str, int] = {}

    for action in actions:
        original_name = action["name"]

        if original_name not in seen_names:
            seen_names[original_name] = 1
        else:
            # Collision detected - append suffix
            counter = seen_names[original_name] + 1
            seen_names[original_name] = counter
            action["name"] = f"{original_name}_{counter}"

    return actions
