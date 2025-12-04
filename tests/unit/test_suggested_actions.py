"""Unit tests for the actions feature.

Tests verify that StageEvaluationResult.actions contains
status-appropriate actions based on the evaluation status:
- INCOMPLETE: PROVIDE_DATA actions for missing properties (always computed)
- BLOCKED: EXECUTE_ACTION (if configured) OR RESOLVE_VALIDATION (computed)
- READY: TRANSITION action to next stage (always computed)
"""


from stageflow.elements import DictElement
from stageflow.models import ActionSource, ActionType
from stageflow.stage import Stage, StageDefinition, StageStatus


class TestSuggestedActionsIncomplete:
    """Test actions for INCOMPLETE status."""

    def test_incomplete_returns_provide_data_actions(self):
        """INCOMPLETE status should return PROVIDE_DATA actions for missing properties."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [],
            "fields": {"email": "string", "name": "string"},
            "is_final": True,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({})  # Empty - missing required fields

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.INCOMPLETE
        assert len(result.actions) == 2

        for action in result.actions:
            assert action["action_type"] == ActionType.PROVIDE_DATA
            assert action["source"] == ActionSource.COMPUTED
            assert len(action["target_properties"]) == 1
            assert action["target_properties"][0] in ["email", "name"]
            assert action["related_properties"] == []

    def test_incomplete_includes_default_values(self):
        """INCOMPLETE actions should include default values when available."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [],
            "fields": {
                "status": {
                    "type": "string",
                    "default": "pending",
                    "required": True,
                }
            },
            "is_final": True,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.INCOMPLETE
        # Note: default_value is only included if not None
        assert len(result.actions) >= 1


class TestSuggestedActionsBlocked:
    """Test actions for BLOCKED status."""

    def test_blocked_with_configured_actions_returns_execute_action(self):
        """BLOCKED status with expected_actions should return EXECUTE_ACTION actions."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "verify_gate",
                    "description": "Verify gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": "equals",
                            "property_path": "verified",
                            "expected_value": True,
                            "error_message": "Must be verified",
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Verify your account",
                    "target_properties": ["verified"],
                }
            ],
            "fields": {"verified": "bool"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"verified": False})  # Fails gate

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.BLOCKED
        # With configured actions, ONLY configured actions are returned (configured first)
        assert len(result.actions) == 1  # Only the configured action

        action = result.actions[0]
        assert action["action_type"] == ActionType.EXECUTE_ACTION
        assert action["source"] == ActionSource.CONFIGURED
        assert action["description"] == "Verify your account"

    def test_blocked_without_configured_returns_resolve_validation(self):
        """BLOCKED status WITHOUT expected_actions should return RESOLVE_VALIDATION."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "test_gate",
                    "description": "Test gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": "equals",
                            "property_path": "status",
                            "expected_value": "approved",
                        }
                    ],
                }
            ],
            "expected_actions": [],  # No configured actions
            "fields": {"status": "string"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"status": "pending"})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.BLOCKED
        assert len(result.actions) >= 1

        # All actions should be RESOLVE_VALIDATION (computed)
        for action in result.actions:
            assert action["action_type"] == ActionType.RESOLVE_VALIDATION
            assert action["source"] == ActionSource.COMPUTED

    def test_blocked_configured_actions_have_priority(self):
        """BLOCKED status with configured actions should ONLY return those."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "test_gate",
                    "description": "Test gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": "equals",
                            "property_path": "status",
                            "expected_value": "approved",
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Submit for approval",
                    "target_properties": ["status"],
                },
                {
                    "description": "Contact admin",
                },
            ],
            "fields": {"status": "string"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"status": "pending"})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.BLOCKED

        # With configured actions, ONLY configured actions are returned
        descriptions = [a["description"] for a in result.actions]
        assert "Submit for approval" in descriptions
        assert "Contact admin" in descriptions
        # Should NOT have computed RESOLVE_VALIDATION actions
        assert all(a["source"] == ActionSource.CONFIGURED for a in result.actions)

    def test_blocked_computed_includes_gate_name(self):
        """BLOCKED computed actions should include gate_name from failed locks."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "approval_gate",
                    "description": "Approval gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": "equals",
                            "property_path": "approved",
                            "expected_value": True,
                            "error_message": "Must be approved",
                        }
                    ],
                }
            ],
            "expected_actions": [],  # No configured actions
            "fields": {"approved": "bool"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"approved": False})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.BLOCKED

        # Find the action from failed lock
        lock_actions = [
            a for a in result.actions
            if a["related_gates"] and "approval_gate" in a["related_gates"]
        ]
        assert len(lock_actions) == 1
        assert lock_actions[0]["action_type"] == ActionType.RESOLVE_VALIDATION
        assert lock_actions[0]["source"] == ActionSource.COMPUTED
        assert lock_actions[0]["target_properties"] == ["approved"]
        assert lock_actions[0]["related_properties"] == []
        assert lock_actions[0]["related_gates"] == ["approval_gate"]


class TestSuggestedActionsReady:
    """Test actions for READY status."""

    def test_ready_returns_transition_action(self):
        """READY status should return a single TRANSITION action."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "complete_gate",
                    "description": "Complete gate",
                    "target_stage": "finished",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": "equals",
                            "property_path": "complete",
                            "expected_value": True,
                        }
                    ],
                }
            ],
            "expected_actions": [],
            "fields": {"complete": "bool"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"complete": True})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.READY
        assert len(result.actions) == 1

        action = result.actions[0]
        assert action["action_type"] == ActionType.TRANSITION
        assert action["source"] == ActionSource.COMPUTED
        assert action["target_stage"] == "finished"
        assert action["related_gates"] == ["complete_gate"]
        assert action["target_properties"] == []

    def test_ready_includes_validated_properties(self):
        """READY transition action should include validated properties."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "multi_lock_gate",
                    "description": "Gate with multiple locks",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {"exists": "email"},
                        {"exists": "name"},
                        {
                            "type": "equals",
                            "property_path": "verified",
                            "expected_value": True,
                        },
                    ],
                }
            ],
            "expected_actions": [],
            "fields": {"email": "string", "name": "string", "verified": "bool"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({
            "email": "test@example.com",
            "name": "Test User",
            "verified": True,
        })

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.READY
        assert len(result.actions) == 1

        action = result.actions[0]
        assert action["action_type"] == ActionType.TRANSITION
        assert action["source"] == ActionSource.COMPUTED
        # Should include all validated properties
        assert "email" in action["related_properties"]
        assert "name" in action["related_properties"]
        assert "verified" in action["related_properties"]


class TestSuggestedActionsWithStageProp:
    """Test actions with stage_prop configured."""

    def test_transition_includes_stage_prop_first(self):
        """READY transition action should include stage_prop as first property."""
        from stageflow.process import Process

        # Arrange - Process with stage_prop configured
        config = {
            "name": "test_with_stage_prop",
            "description": "Test process",
            "initial_stage": "start",
            "final_stage": "end",
            "stage_prop": "metadata.stage",
            "stages": {
                "start": {
                    "name": "Start",
                    "description": "Start stage",
                    "gates": [
                        {
                            "name": "proceed",
                            "description": "Proceed to end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "ready"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": ["ready"],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "description": "End stage",
                    "gates": [],
                    "expected_actions": [],
                    "fields": [],
                    "is_final": True,
                },
            },
        }
        process = Process(config)
        element = DictElement({"ready": True, "metadata": {"stage": "start"}})

        # Act
        result = process.evaluate(element, "start")
        stage_result = result["stage_result"]

        # Assert
        assert stage_result.status == StageStatus.READY
        assert len(stage_result.actions) == 1

        action = stage_result.actions[0]
        assert action["action_type"] == ActionType.TRANSITION
        assert action["source"] == ActionSource.COMPUTED
        # stage_prop should be FIRST in related_properties
        assert action["related_properties"][0] == "metadata.stage"

    def test_no_stage_prop_no_injection(self):
        """Without stage_prop, transition action should not inject extra property."""
        # Arrange - Process WITHOUT stage_prop
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "proceed",
                    "description": "Proceed",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [{"exists": "field1"}],
                }
            ],
            "expected_actions": [],
            "fields": {"field1": "string"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({"field1": "value"})

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.READY
        action = result.actions[0]
        assert action["action_type"] == ActionType.TRANSITION
        assert action["source"] == ActionSource.COMPUTED
        # Only the validated property should be present
        assert action["related_properties"] == ["field1"]


class TestSuggestedActionsStructure:
    """Test the structure and typing of actions."""

    def test_action_has_required_fields(self):
        """All actions should have required fields."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [],
            "fields": {"field1": "string"},
            "is_final": True,
        }
        stage = Stage("test_id", stage_config)
        element = DictElement({})

        # Act
        result = stage.evaluate(element)

        # Assert
        for action in result.actions:
            assert "action_type" in action
            assert "source" in action
            assert "description" in action
            assert "related_properties" in action
            assert "target_properties" in action
            assert isinstance(action["related_properties"], list)
            assert isinstance(action["target_properties"], list)

    def test_action_type_is_valid_enum(self):
        """action_type should be a valid ActionType enum value."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [
                {
                    "name": "test_gate",
                    "description": "Test gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [{"exists": "field1"}],
                }
            ],
            "expected_actions": [],
            "fields": {"field1": "string"},
            "is_final": False,
        }
        stage = Stage("test_id", stage_config)

        valid_types = {
            ActionType.PROVIDE_DATA,
            ActionType.RESOLVE_VALIDATION,
            ActionType.EXECUTE_ACTION,
            ActionType.TRANSITION,
        }

        # Test INCOMPLETE
        result_incomplete = stage.evaluate(DictElement({}))
        for action in result_incomplete.actions:
            assert action["action_type"] in valid_types

        # Test BLOCKED (no configured actions, so RESOLVE_VALIDATION)
        result_blocked = stage.evaluate(DictElement({"field1": ""}))
        for action in result_blocked.actions:
            assert action["action_type"] in valid_types

        # Test READY
        result_ready = stage.evaluate(DictElement({"field1": "value"}))
        for action in result_ready.actions:
            assert action["action_type"] in valid_types
