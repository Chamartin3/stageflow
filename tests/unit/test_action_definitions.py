"""Tests for declarative action definition system."""


from stageflow.element import create_element
from stageflow.stage import (
    ActionDefinition,
    Stage,
    StageActionDefinitions,
)
from stageflow.process.result import Action, ActionType, Priority


class TestActionDefinition:
    """Test ActionDefinition class functionality."""

    def test_action_definition_creation(self):
        """Test creating an ActionDefinition with all parameters."""
        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Complete the {field_name} field",
            priority=Priority.HIGH,
            conditions=["field_empty"],
            template_vars={"field_name": "name"},
            metadata={"required": True}
        )

        assert action_def.type == ActionType.COMPLETE_FIELD
        assert action_def.description == "Complete the {field_name} field"
        assert action_def.priority == Priority.HIGH
        assert action_def.conditions == ["field_empty"]
        assert action_def.template_vars == {"field_name": "name"}
        assert action_def.metadata == {"required": True}

    def test_action_definition_defaults(self):
        """Test ActionDefinition with default values."""
        action_def = ActionDefinition(
            type=ActionType.VALIDATE_DATA,
            description="Validate data"
        )

        assert action_def.priority == Priority.NORMAL
        assert action_def.conditions == []
        assert action_def.template_vars == {}
        assert action_def.metadata == {}

    def test_resolve_action_with_template_vars(self):
        """Test resolving action with template variables."""
        element = create_element({"name": "John", "field_type": "email"})

        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Please enter your {field_name}",
            template_vars={"field_name": "field_type"},
            conditions=["Field {field_name} is empty"]
        )

        action = action_def.resolve_action(element)

        assert isinstance(action, Action)
        assert action.type == ActionType.COMPLETE_FIELD
        assert action.description == "Please enter your email"
        assert action.conditions == ["Field email is empty"]

    def test_resolve_action_with_context(self):
        """Test resolving action with additional context."""
        element = create_element({"stage": "profile"})

        action_def = ActionDefinition(
            type=ActionType.TRANSITION_STAGE,
            description="Move from {current_stage} to {next_stage}",
            metadata={"stage_transition": "{current_stage} -> {next_stage}"}
        )

        context = {"current_stage": "profile", "next_stage": "verification"}
        action = action_def.resolve_action(element, context)

        assert action.description == "Move from profile to verification"
        assert action.metadata["stage_transition"] == "profile -> verification"

    def test_resolve_action_with_missing_vars(self):
        """Test resolving action when template variables are missing."""
        element = create_element({"name": "John"})

        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Please complete {missing_field}",
            template_vars={"field_name": "nonexistent_property"}
        )

        action = action_def.resolve_action(element)

        # Should fallback gracefully when template vars can't be resolved
        assert "Please complete {missing_field}" in action.description


class TestStageActionDefinitions:
    """Test StageActionDefinitions class functionality."""

    def test_stage_action_definitions_creation(self):
        """Test creating StageActionDefinitions."""
        fulfilling_action = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Complete required fields"
        )

        qualifying_action = ActionDefinition(
            type=ActionType.TRANSITION_STAGE,
            description="Ready to advance"
        )

        action_defs = StageActionDefinitions(
            fulfilling=[fulfilling_action],
            qualifying=[qualifying_action]
        )

        assert len(action_defs.fulfilling) == 1
        assert len(action_defs.qualifying) == 1
        assert len(action_defs.awaiting) == 0
        assert len(action_defs.advancing) == 0
        assert len(action_defs.regressing) == 0
        assert len(action_defs.completed) == 0

    def test_get_actions_for_state(self):
        """Test getting actions for specific states."""
        fulfilling_action = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Complete fields"
        )

        action_defs = StageActionDefinitions(fulfilling=[fulfilling_action])

        fulfilling_actions = action_defs.get_actions_for_state("fulfilling")
        awaiting_actions = action_defs.get_actions_for_state("awaiting")
        invalid_actions = action_defs.get_actions_for_state("invalid_state")

        assert len(fulfilling_actions) == 1
        assert fulfilling_actions[0] == fulfilling_action
        assert len(awaiting_actions) == 0
        assert len(invalid_actions) == 0


class TestStageWithActionDefinitions:
    """Test Stage class with action definitions."""

    def test_stage_with_action_definitions(self):
        """Test creating Stage with action definitions."""
        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Complete the name field"
        )

        action_definitions = StageActionDefinitions(fulfilling=[action_def])

        stage = Stage(
            name="profile_stage",
            action_definitions=action_definitions
        )

        assert stage.name == "profile_stage"
        assert stage.action_definitions == action_definitions

    def test_stage_resolve_actions_for_state(self):
        """Test resolving actions for specific state."""
        element = create_element({"name": "", "email": "john@example.com"})

        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Please enter your name",
            priority=Priority.HIGH
        )

        action_definitions = StageActionDefinitions(fulfilling=[action_def])
        stage = Stage(name="profile", action_definitions=action_definitions)

        actions = stage.resolve_actions_for_state("fulfilling", element)

        assert len(actions) == 1
        assert isinstance(actions[0], Action)
        assert actions[0].type == ActionType.COMPLETE_FIELD
        assert actions[0].description == "Please enter your name"
        assert actions[0].priority == Priority.HIGH

    def test_stage_has_action_definitions_for_state(self):
        """Test checking if stage has action definitions for a state."""
        action_def = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Complete fields"
        )

        action_definitions = StageActionDefinitions(fulfilling=[action_def])
        stage = Stage(name="test", action_definitions=action_definitions)

        assert stage.has_action_definitions_for_state("fulfilling") is True
        assert stage.has_action_definitions_for_state("qualifying") is False
        assert stage.has_action_definitions_for_state("invalid_state") is False

    def test_stage_multiple_actions_per_state(self):
        """Test stage with multiple actions per state."""
        element = create_element({"name": "", "email": ""})

        action1 = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Enter your name"
        )

        action2 = ActionDefinition(
            type=ActionType.COMPLETE_FIELD,
            description="Enter your email"
        )

        action_definitions = StageActionDefinitions(fulfilling=[action1, action2])
        stage = Stage(name="profile", action_definitions=action_definitions)

        actions = stage.resolve_actions_for_state("fulfilling", element)

        assert len(actions) == 2
        assert actions[0].description == "Enter your name"
        assert actions[1].description == "Enter your email"

    def test_stage_action_template_resolution(self):
        """Test template resolution in stage actions."""
        element = create_element({"user_id": "12345", "status": "pending"})

        action_def = ActionDefinition(
            type=ActionType.WAIT_FOR_CONDITION,
            description="Wait for user {user_id} status to change from {current_status}",
            template_vars={
                "user_id": "user_id",
                "current_status": "status"
            }
        )

        action_definitions = StageActionDefinitions(awaiting=[action_def])
        stage = Stage(name="verification", action_definitions=action_definitions)

        actions = stage.resolve_actions_for_state("awaiting", element)

        assert len(actions) == 1
        assert actions[0].description == "Wait for user 12345 status to change from pending"

    def test_stage_action_with_context(self):
        """Test stage action resolution with context."""
        element = create_element({"name": "John"})

        action_def = ActionDefinition(
            type=ActionType.TRANSITION_STAGE,
            description="Advance from {current_stage} to {next_stage}",
            metadata={"transition": "{current_stage} -> {next_stage}"}
        )

        action_definitions = StageActionDefinitions(advancing=[action_def])
        stage = Stage(name="profile", action_definitions=action_definitions)

        context = {"current_stage": "profile", "next_stage": "verification"}
        actions = stage.resolve_actions_for_state("advancing", element, context)

        assert len(actions) == 1
        assert actions[0].description == "Advance from profile to verification"
        assert actions[0].metadata["transition"] == "profile -> verification"
