"""Comprehensive unit tests for Stage class and stage evaluation logic."""

import pytest

from stageflow.elements import DictElement
from stageflow.lock import LockType
from stageflow.models import Action, ActionSource, ActionType, StageDefinition
from stageflow.stage import (
    Stage,
    StageEvaluationResult,
    StageStatus,
)


class TestAction:
    """Test Action TypedDict."""

    def test_action_creation(self):
        """Verify Action can be created with required fields."""
        # Arrange & Act
        action: Action = {
            "action_type": ActionType.RESOLVE_VALIDATION,
            "source": ActionSource.COMPUTED,
            "description": "Update user email",
            "related_properties": ["user.email"],
            "target_properties": ["email"],
        }

        # Assert
        assert action["description"] == "Update user email"
        assert action["related_properties"] == ["user.email"]
        assert action["action_type"] == ActionType.RESOLVE_VALIDATION
        assert action["source"] == ActionSource.COMPUTED

    def test_action_creation_with_target_stage(self):
        """Verify Action can be created with target stage."""
        # Arrange & Act
        action: Action = {
            "action_type": ActionType.TRANSITION,
            "source": ActionSource.COMPUTED,
            "description": "Ready to proceed",
            "related_properties": [],
            "target_properties": [],
            "target_stage": "next_stage",
        }

        # Assert
        assert action["description"] == "Ready to proceed"
        assert action["related_properties"] == []
        assert action["action_type"] == ActionType.TRANSITION
        assert action["target_stage"] == "next_stage"

    def test_action_with_configured_source(self):
        """Verify Action can be created with configured source."""
        # Arrange & Act
        action: Action = {
            "action_type": ActionType.EXECUTE_ACTION,
            "source": ActionSource.CONFIGURED,
            "description": "Contact support",
            "related_properties": ["ticket_id"],
            "target_properties": ["verified"],
            "name": "contact_support",
            "instructions": ["Open ticket", "Wait for response"],
        }

        # Assert
        assert action["source"] == ActionSource.CONFIGURED
        assert action["name"] == "contact_support"
        assert len(action["instructions"]) == 2


class TestStageEvaluationResult:
    """Test StageEvaluationResult dataclass."""

    def test_stage_evaluation_result_creation(self):
        """Verify StageEvaluationResult can be created with all fields."""
        # Act
        result = StageEvaluationResult(
            status=StageStatus.BLOCKED,
            results={"gate1": "result1"},
            actions=[
                {
                    "action_type": ActionType.RESOLVE_VALIDATION,
                    "source": ActionSource.COMPUTED,
                    "description": "Test action",
                    "related_properties": [],
                    "target_properties": ["field1"],
                }
            ],
            validation_messages=["Test message"],
        )

        # Assert
        assert result.status == StageStatus.BLOCKED
        assert result.results == {"gate1": "result1"}
        assert len(result.actions) == 1
        assert result.actions[0]["action_type"] == ActionType.RESOLVE_VALIDATION
        assert result.validation_messages == ["Test message"]

    def test_stage_evaluation_result_immutability(self):
        """Verify StageEvaluationResult is immutable."""
        # Arrange
        result = StageEvaluationResult(
            status=StageStatus.INCOMPLETE,
            results={},
            actions=[],
            validation_messages=[]
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            result.status = StageStatus.READY  # Should raise


class TestStage:
    """Test Stage class functionality."""

    def test_stage_creation_with_valid_definition(self):
        """Verify Stage can be created with valid StageDefinition."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "user_registration",
            "description": "User registration stage",
            "gates": [
                {
                    "name": "basic_info",
                    "description": "Basic user information validation",
                    "target_stage": "email_verification",
                    "parent_stage": "user_registration",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "email",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "password",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Fill in required user information",
                    "related_properties": ["email", "password"],
                }
            ],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": None},
            },
            "is_final": False,
        }

        # Act
        stage = Stage("registration_id", stage_config)

        # Assert
        assert stage.name == "user_registration"
        assert stage.description == "User registration stage"
        assert len(stage.gates) == 1
        assert stage.gates[0].name == "basic_info"
        assert stage.gates[0].target_stage == "email_verification"
        assert not stage.is_final

    def test_stage_creation_final_stage_without_gates(self):
        """Verify final stage can be created without gates."""
        # Arrange
        final_stage_config: StageDefinition = {
            "name": "completed",
            "description": "Final completion stage",
            "gates": [],
            "expected_actions": [],
            "fields": {},
            "is_final": True,
        }

        # Act
        stage = Stage("final_id", final_stage_config)

        # Assert
        assert stage.name == "completed"
        assert stage.is_final is True
        assert len(stage.gates) == 0

    def test_stage_creation_non_final_without_gates_is_allowed(self):
        """Verify non-final stage without gates is allowed (validation is at process level)."""
        # Arrange
        config: StageDefinition = {
            "name": "intermediate_stage",
            "description": "Intermediate stage without gates",
            "gates": [],
            "expected_actions": [],
            "fields": {},
            "is_final": False,
        }

        # Act
        stage = Stage("intermediate_id", config)

        # Assert
        assert stage.name == "intermediate_stage"
        assert stage.is_final is False
        assert len(stage.gates) == 0

    def test_stage_possible_transitions_property(self):
        """Verify possible_transitions returns all target stages from gates."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "multi_gate_stage",
            "description": "Stage with multiple gates",
            "gates": [
                {
                    "name": "gate1",
                    "description": "First gate",
                    "target_stage": "stage_a",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        }
                    ],
                },
                {
                    "name": "gate2",
                    "description": "Second gate",
                    "target_stage": "stage_b",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field2",
                            "expected_value": None,
                        }
                    ],
                },
                {
                    "name": "gate3",
                    "description": "Third gate",
                    "target_stage": "stage_c",  # Unique target
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field3",
                            "expected_value": None,
                        }
                    ],
                },
            ],
            "expected_actions": [],
            "fields": {"field1": None, "field2": None, "field3": None},
            "is_final": False,
        }

        stage = Stage("multi_id", stage_config)

        # Act
        transitions = stage.posible_transitions

        # Assert
        assert set(transitions) == {
            "stage_a",
            "stage_b",
            "stage_c",
        }  # All unique transitions

    def test_stage_evaluate_with_valid_schema_and_passing_gate(self):
        """Verify stage evaluation succeeds when schema is valid and gate passes."""
        # Arrange
        element_data = {
            "email": "user@example.com",
            "password": "securepass123",
            "age": 25,
        }
        element = DictElement(element_data)

        stage_config: StageDefinition = {
            "name": "validation_stage",
            "description": "User validation",
            "gates": [
                {
                    "name": "user_validation",
                    "description": "Validate user data",
                    "target_stage": "next_stage",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "email",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "password",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.GREATER_THAN,
                            "property_path": "age",
                            "expected_value": 18,
                        },
                    ],
                }
            ],
            "expected_actions": [],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": None},
                "age": {"type": "integer", "default": None},
            },
            "is_final": False,
        }

        stage = Stage("validation_id", stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.READY
        # Verify transition action is generated
        assert len(result.actions) == 1
        assert result.actions[0]["action_type"] == ActionType.TRANSITION
        assert result.actions[0]["source"] == ActionSource.COMPUTED
        assert "user_validation" in result.results
        assert result.results["user_validation"].success

    def test_stage_evaluate_with_invalid_schema(self):
        """Verify stage evaluation returns INVALID_SCHEMA when required properties missing."""
        # Arrange
        element_data = {
            "email": "user@example.com"
            # Missing password and age
        }
        element = DictElement(element_data)

        stage_config: StageDefinition = {
            "name": "validation_stage",
            "description": "User validation",
            "gates": [
                {
                    "name": "user_validation",
                    "description": "Validate user data",
                    "target_stage": "next_stage",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "email",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "password",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": "default_pass"},
                "age": {"type": "integer", "default": 18},
            },
            "is_final": False,
        }

        stage = Stage("validation_id", stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.INCOMPLETE
        # INCOMPLETE status generates PROVIDE_DATA actions for missing properties
        assert len(result.actions) >= 1
        assert all(
            action["action_type"] == ActionType.PROVIDE_DATA
            for action in result.actions
        )
        assert all(
            action["source"] == ActionSource.COMPUTED
            for action in result.actions
        )
        # Validation messages should indicate missing properties
        assert len(result.validation_messages) > 0
        assert result.results == {}  # No gates evaluated when schema invalid

    def test_stage_evaluate_with_valid_schema_but_failing_gates(self):
        """Verify stage evaluation returns ACTION_REQUIRED when gates fail."""
        # Arrange
        element_data = {
            "email": "invalid-email-format",  # Will fail regex
            "password": "securepass123",
            "age": 25,
        }
        element = DictElement(element_data)

        stage_config: StageDefinition = {
            "name": "validation_stage",
            "description": "User validation",
            "gates": [
                {
                    "name": "email_validation",
                    "description": "Validate email format",
                    "target_stage": "next_stage",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.REGEX,
                            "property_path": "email",
                            "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
                        }
                    ],
                }
            ],
            "expected_actions": [
                {"description": "Fix email format", "related_properties": ["email"]}
            ],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": None},
                "age": {"type": "integer", "default": None},
            },
            "is_final": False,
        }

        stage = Stage("validation_id", stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        assert result.status == StageStatus.BLOCKED
        # Stage has expected_actions, so "configured first" priority applies
        assert len(result.actions) >= 1
        # All actions should come from configured source (expected_actions in YAML)
        assert any(
            action["description"] == "Fix email format"
            for action in result.actions
        )
        assert all(
            action["source"] == ActionSource.CONFIGURED
            for action in result.actions
        )
        assert "email_validation" in result.results
        assert not result.results["email_validation"].success

    def test_stage_schema_validation_with_nested_properties(self):
        """Verify stage validates nested property schemas correctly."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "nested_validation",
            "description": "Nested property validation",
            "gates": [
                {
                    "name": "nested_gate",
                    "description": "Validate nested properties",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "user.profile.name",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [],
            "fields": {
                "user": {"profile": {"name": {"type": "string", "default": None}}}
            },
            "is_final": False,
        }

        # Act & Assert - Should not raise exception during stage creation
        stage = Stage("nested_id", stage_config)
        assert stage.name == "nested_validation"

    def test_stage_action_validation_fails_with_unevaluated_target_properties(self):
        """Verify stage creation fails when target_properties aren't evaluated by gates."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_action_stage",
            "description": "Stage with invalid actions",
            "gates": [
                {
                    "name": "gate1",
                    "description": "Gate that doesn't evaluate all action properties",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Action that references unevaluated target property",
                    "target_properties": [
                        "field1",
                        "field2",
                    ],  # field2 not evaluated by any gate
                }
            ],
            "fields": {
                "field1": {"type": "string", "default": None},
                "field2": {"type": "string", "default": None},
            },
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="Action target_property 'field2' is not evaluated by any gate"
        ):
            Stage("invalid_id", invalid_config)

    def test_stage_action_related_properties_emits_warning_for_unknown_fields(self):
        """Verify related_properties with unknown fields only emits warning, not error."""
        import warnings

        # Arrange
        config: StageDefinition = {
            "name": "action_with_related_props",
            "description": "Stage with related_properties referencing unknown field",
            "gates": [
                {
                    "name": "gate1",
                    "description": "Gate",
                    "target_stage": "next",
                    "parent_stage": "current",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Action with related property not in fields",
                    "related_properties": [
                        "unknown_field",  # Not in fields and not evaluated
                    ],
                }
            ],
            "fields": {
                "field1": {"type": "string", "default": None},
            },
            "is_final": False,
        }

        # Act & Assert - should emit warning but not raise error
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            stage = Stage("valid_id", config)

            # Should have created stage successfully
            assert stage.name == "action_with_related_props"

            # Should have emitted a warning about unknown related_property
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "unknown_field" in str(w[0].message)
            assert "not defined in fields" in str(w[0].message)

    def test_stage_serialization_to_dict(self):
        """Verify stage can be serialized back to dictionary format."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "serialization_test",
            "description": "Test stage serialization",
            "gates": [
                {
                    "name": "test_gate",
                    "description": "Test gate for serialization",
                    "target_stage": "next_stage",
                    "parent_stage": "current_stage",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [
                {"description": "Test action", "target_properties": ["field"]}
            ],
            "fields": {"field": {"type": "string", "default": None}},
            "is_final": False,
        }

        stage = Stage("serialization_id", stage_config)

        # Act
        serialized = stage.to_dict()

        # Assert
        assert serialized["name"] == "serialization_test"
        assert serialized["description"] == "Test stage serialization"
        assert len(serialized["gates"]) == 1
        assert serialized["gates"][0]["name"] == "test_gate"
        assert len(serialized["expected_actions"]) == 1
        assert serialized["expected_actions"][0]["description"] == "Test action"
        assert serialized["is_final"] is False


class TestStageIntegration:
    """Integration tests for Stage with complex scenarios."""

    def test_multi_gate_stage_evaluation_workflow(self):
        """Test stage with multiple gates representing different validation paths."""
        # Arrange
        user_data = {
            "email": "user@example.com",
            "password": "securepass123",
            "profile": {"name": "John Doe", "age": 25, "verified": False},
            "preferences": {"newsletter": True, "notifications": True},
        }
        element = DictElement(user_data)

        stage_config: StageDefinition = {
            "name": "user_onboarding",
            "description": "Complete user onboarding validation",
            "gates": [
                {
                    "name": "basic_requirements",
                    "description": "Basic user requirements",
                    "target_stage": "profile_setup",
                    "parent_stage": "registration",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "email",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "password",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.REGEX,
                            "property_path": "email",
                            "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
                        },
                    ],
                },
                {
                    "name": "profile_complete",
                    "description": "Complete profile information",
                    "target_stage": "verification",
                    "parent_stage": "registration",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "profile.name",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.GREATER_THAN,
                            "property_path": "profile.age",
                            "expected_value": 18,
                        },
                        {
                            "type": LockType.EQUALS,
                            "property_path": "profile.verified",
                            "expected_value": True,
                        },  # Will fail
                    ],
                },
            ],
            "expected_actions": [
                {
                    "description": "Complete profile verification",
                    "related_properties": ["profile.verified"],
                }
            ],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": None},
                "profile": {
                    "name": {"type": "string", "default": None},
                    "age": {"type": "integer", "default": None},
                    "verified": {"type": "boolean", "default": False},
                },
            },
            "is_final": False,
        }

        stage = Stage("onboarding_id", stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        # First gate should pass, triggering READY status with TRANSITION action
        assert result.status == StageStatus.READY
        assert len(result.actions) == 1
        assert result.actions[0]["action_type"] == ActionType.TRANSITION
        assert result.actions[0]["source"] == ActionSource.COMPUTED
        # Verify gates were evaluated
        assert "basic_requirements" in result.results
        assert result.results["basic_requirements"].success

    def test_complex_nested_validation_scenario(self):
        """Test stage evaluation with complex nested data structures."""
        # Arrange
        organization_data = {
            "organization": {
                "info": {
                    "name": "Tech Corp",
                    "type": "technology",
                    "employee_count": 150,
                },
                "departments": [
                    {
                        "name": "Engineering",
                        "head": {
                            "name": "Alice Johnson",
                            "email": "alice@techcorp.com",
                            "verified": True,
                        },
                        "team_size": 50,
                    },
                    {
                        "name": "Marketing",
                        "head": {
                            "name": "Bob Smith",
                            "email": "bob@techcorp.com",
                            "verified": False,  # Will cause failure
                        },
                        "team_size": 20,
                    },
                ],
                "policies": {"remote_work": True, "performance_reviews": True},
            }
        }
        element = DictElement(organization_data)

        stage_config: StageDefinition = {
            "name": "organization_validation",
            "description": "Organization structure validation",
            "gates": [
                {
                    "name": "basic_info",
                    "description": "Basic organization information",
                    "target_stage": "department_review",
                    "parent_stage": "setup",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "organization.info.name",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.GREATER_THAN,
                            "property_path": "organization.info.employee_count",
                            "expected_value": 10,
                        },
                    ],
                },
                {
                    "name": "department_heads_verified",
                    "description": "All department heads must be verified",
                    "target_stage": "policy_review",
                    "parent_stage": "setup",
                    "locks": [
                        {
                            "type": LockType.EQUALS,
                            "property_path": "organization.departments[0].head.verified",
                            "expected_value": True,
                        },
                        {
                            "type": LockType.EQUALS,
                            "property_path": "organization.departments[1].head.verified",
                            "expected_value": True,
                        },  # Will fail
                    ],
                },
            ],
            "expected_actions": [
                {
                    "description": "Verify all department heads",
                    "related_properties": [
                        "organization.departments[0].head.verified",
                        "organization.departments[1].head.verified",
                    ],
                }
            ],
            "fields": None,
            "is_final": False,
        }

        stage = Stage("org_validation_id", stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        # First gate passes, so should be READY status with TRANSITION action
        assert result.status == StageStatus.READY
        assert len(result.actions) == 1
        assert result.actions[0]["action_type"] == ActionType.TRANSITION
        assert result.actions[0]["source"] == ActionSource.COMPUTED
        # Verify at least one gate passed
        assert "basic_info" in result.results
        assert result.results["basic_info"].success

    def test_final_stage_evaluation(self):
        """Test evaluation of a final stage without gates."""
        # Arrange
        final_data = {
            "completion": {"status": "completed", "timestamp": "2024-01-20T10:00:00Z"}
        }
        element = DictElement(final_data)

        final_stage_config: StageDefinition = {
            "name": "completion",
            "description": "Final completion stage",
            "gates": [],
            "expected_actions": [],
            "fields": {
                "completion": {
                    "status": {"type": "string", "default": None},
                    "timestamp": {"type": "string", "default": None},
                }
            },
            "is_final": True,
        }

        stage = Stage("completion_id", final_stage_config)

        # Act
        result = stage.evaluate(element)

        # Assert
        # Final stages with valid schema should show BLOCKED status with no actions
        assert result.status == StageStatus.BLOCKED
        assert len(result.actions) == 0  # No actions for final stage (no configured, no gates to compute from)
        assert result.results == {}  # No gates to evaluate


class TestStageSchema:
    """Test Stage schema extraction functionality."""

    def test_get_schema_returns_expected_properties(self):
        """Verify get_schema returns the stage's expected properties."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "user_registration",
            "description": "User registration stage",
            "gates": [],
            "expected_actions": [],
            "fields": {
                "email": {"type": "string", "default": None},
                "password": {"type": "string", "default": None},
                "user.profile.name": {"type": "string", "default": "Anonymous"},
            },
            "is_final": False,
        }

        stage = Stage("registration_id", stage_config)

        # Act
        schema = stage.get_schema()

        # Assert
        assert schema is not None
        assert "email" in schema
        assert "password" in schema
        assert "user" in schema  # Nested structure
        assert schema["email"]["type"] == "string"
        assert schema["password"]["type"] == "string"
        # Access nested property through properties dict
        assert schema["user"]["properties"]["profile"]["properties"]["name"]["default"] == "Anonymous"

    def test_get_schema_returns_empty_for_none_properties(self):
        """Verify get_schema returns empty dict when no expected properties defined."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "simple_stage",
            "description": "Stage without properties",
            "gates": [],
            "expected_actions": [],
            "fields": None,
            "is_final": True,
        }

        stage = Stage("simple_id", stage_config)

        # Act
        schema = stage.get_schema()

        # Assert
        assert schema == {}

    def test_get_schema_returns_empty_dict_for_empty_properties_dict(self):
        """Verify get_schema returns empty dict when properties dict is empty."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "empty_props_stage",
            "description": "Stage with empty properties dict",
            "gates": [],
            "expected_actions": [],
            "fields": {},
            "is_final": False,
        }

        stage = Stage("empty_id", stage_config)

        # Act
        schema = stage.get_schema()

        # Assert
        assert schema == {}

    def test_get_schema_with_complex_nested_properties(self):
        """Verify get_schema handles complex nested property structures."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "complex_stage",
            "description": "Stage with complex nested properties",
            "gates": [],
            "expected_actions": [],
            "fields": {
                "user": {
                    "personal": {
                        "name": {"type": "string", "default": None},
                        "age": {"type": "integer", "default": 18},
                    },
                    "contact": {
                        "email": {"type": "string", "default": None},
                        "phone": {"type": "string", "default": None},
                    },
                },
                "preferences": {
                    "notifications": {"type": "boolean", "default": True},
                    "theme": {"type": "string", "default": "light"},
                },
            },
            "is_final": False,
        }

        stage = Stage("complex_id", stage_config)

        # Act
        schema = stage.get_schema()

        # Assert
        assert schema is not None
        assert "user" in schema
        assert "preferences" in schema
        # Access nested properties through properties dict
        user_props = schema["user"]["properties"]
        assert user_props["personal"]["properties"]["name"]["type"] == "string"
        assert user_props["personal"]["properties"]["age"]["default"] == 18
        assert schema["preferences"]["properties"]["theme"]["default"] == "light"

    def test_get_schema_is_non_mutating(self):
        """Verify get_schema does not modify the stage's internal state."""
        # Arrange
        original_properties = {
            "field1": {"type": "string", "default": "value1"},
            "field2": {"type": "integer", "default": 42},
        }

        stage_config: StageDefinition = {
            "name": "immutable_stage",
            "description": "Stage for testing immutability",
            "gates": [],
            "expected_actions": [],
            "fields": original_properties,
            "is_final": False,
        }

        stage = Stage("immutable_id", stage_config)

        # Act
        schema1 = stage.get_schema()
        schema2 = stage.get_schema()

        # Modify the returned schema
        if schema1:
            schema1["new_field"] = {"type": "string", "default": "added"}

        # Assert
        # The original stage properties should remain unchanged
        original_schema = stage.get_schema()
        assert "new_field" not in original_schema
        assert schema2 == original_schema
        assert schema1 != schema2  # schema1 was modified but shouldn't affect stage

    def test_get_schema_with_property_definitions_none_values(self):
        """Verify get_schema handles property definitions with None values."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "nullable_stage",
            "description": "Stage with None property definitions",
            "gates": [],
            "expected_actions": [],
            "fields": {
                "optional_field": None,
                "required_field": {"type": "string", "default": None},
            },
            "is_final": False,
        }

        stage = Stage("nullable_id", stage_config)

        # Act
        schema = stage.get_schema()

        # Assert
        assert schema is not None
        assert "optional_field" in schema
        assert "required_field" in schema
        # None values are treated as string type (default)
        assert schema["optional_field"]["type"] == "string"
        assert schema["required_field"]["type"] == "string"

    def test_get_schema_performance_with_large_properties(self):
        """Verify get_schema performs well with a large number of properties."""
        import time

        # Arrange - Create a stage with many properties
        large_properties = {}
        for i in range(1000):
            large_properties[f"field_{i}"] = {"type": "string", "default": f"value_{i}"}

        stage_config: StageDefinition = {
            "name": "large_stage",
            "description": "Stage with many properties",
            "gates": [],
            "expected_actions": [],
            "fields": large_properties,
            "is_final": False,
        }

        stage = Stage("large_id", stage_config)

        # Act
        start_time = time.time()
        schema = stage.get_schema()
        end_time = time.time()

        # Assert
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert execution_time < 100  # Should complete in less than 100ms
        assert schema is not None
        assert len(schema) == 1000
        assert "field_500" in schema
        assert schema["field_500"]["default"] == "value_500"
