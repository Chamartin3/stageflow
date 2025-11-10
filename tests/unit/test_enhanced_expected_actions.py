"""Unit tests for enhanced expected_actions structure (Proposal 8)."""

import warnings

import pytest

from stageflow.elements import DictElement
from stageflow.lock import LockType
from stageflow.stage import Stage, StageDefinition


class TestActionDefinitionBasic:
    """Test basic ActionDefinition with required description field only."""

    def test_action_with_description_only(self):
        """Verify action can be created with only description field."""
        # Arrange & Act
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {"description": "Complete the task"}  # Only description field
            ],
            "expected_properties": {},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        assert stage.stage_actions[0]["description"] == "Complete the task"

    def test_action_with_description_and_related_properties(self):
        """Verify backward compatibility with description and related_properties."""
        # Arrange & Act
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
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "description": "Update field",
                    "related_properties": ["field1"],
                }
            ],
            "expected_properties": {"field1": None},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        assert stage.stage_actions[0]["description"] == "Update field"
        assert stage.stage_actions[0]["related_properties"] == ["field1"]

    def test_action_missing_description_raises_error(self):
        """Verify error is raised when description is missing."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {"name": "test_action"}  # Missing required description
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="missing required 'description' field"):
            Stage("invalid_id", invalid_config)

    def test_action_with_empty_description_raises_error(self):
        """Verify error is raised when description is empty string."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {"description": ""}  # Empty description
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="missing required 'description' field"):
            Stage("invalid_id", invalid_config)


class TestActionDefinitionWithName:
    """Test ActionDefinition with optional name field."""

    def test_action_with_name_and_description(self):
        """Verify action can include optional name field."""
        # Arrange & Act
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {
                    "name": "create_document",
                    "description": "Create the initial document structure",
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        assert stage.stage_actions[0]["name"] == "create_document"
        assert (
            stage.stage_actions[0]["description"]
            == "Create the initial document structure"
        )

    def test_action_with_invalid_name_type_raises_error(self):
        """Verify error is raised when name is not a string."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {
                    "name": 123,  # Invalid: not a string
                    "description": "Test action",
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="invalid 'name' field"):
            Stage("invalid_id", invalid_config)

    def test_action_with_empty_name_raises_error(self):
        """Verify error is raised when name is empty string."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {
                    "name": "",  # Invalid: empty string
                    "description": "Test action",
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="invalid 'name' field"):
            Stage("invalid_id", invalid_config)

    def test_duplicate_action_names_emit_warning(self):
        """Verify warning is emitted for duplicate action names."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {"name": "test_action", "description": "First action"},
                {
                    "name": "test_action",
                    "description": "Second action",
                },  # Duplicate name
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            stage = Stage("test_id", stage_config)

            # Should emit a warning about duplicate names
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "Duplicate action name" in str(w[0].message)
            assert "test_action" in str(w[0].message)

        # Stage should still be created successfully
        assert len(stage.stage_actions) == 2


class TestActionDefinitionWithInstructions:
    """Test ActionDefinition with optional instructions field."""

    def test_action_with_instructions(self):
        """Verify action can include optional instructions field."""
        # Arrange & Act
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {
                    "name": "document_bug",
                    "description": "Document the bug with complete information",
                    "instructions": [
                        "Set severity level (critical, high, medium, low)",
                        "Provide clear description of the bug",
                        "Add steps to reproduce",
                    ],
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        action = stage.stage_actions[0]
        assert action["name"] == "document_bug"
        assert action["description"] == "Document the bug with complete information"
        assert len(action["instructions"]) == 3
        assert (
            action["instructions"][0]
            == "Set severity level (critical, high, medium, low)"
        )

    def test_action_with_invalid_instructions_type_raises_error(self):
        """Verify error is raised when instructions is not a list."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {
                    "description": "Test action",
                    "instructions": "Not a list",  # Invalid: must be list
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="invalid 'instructions' field: must be a list"
        ):
            Stage("invalid_id", invalid_config)

    def test_action_with_non_string_instruction_items_raises_error(self):
        """Verify error is raised when instruction items are not strings."""
        # Arrange
        invalid_config: StageDefinition = {
            "name": "invalid_stage",
            "description": "Invalid stage",
            "gates": [],
            "expected_actions": [
                {
                    "description": "Test action",
                    "instructions": [
                        "Valid instruction",
                        123,  # Invalid: not a string
                    ],
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="invalid 'instructions' field: all items must be strings"
        ):
            Stage("invalid_id", invalid_config)

    def test_action_with_too_many_instructions_emits_warning(self):
        """Verify warning is emitted when instructions exceed recommended limit."""
        # Arrange
        many_instructions = [f"Instruction {i}" for i in range(15)]  # More than 10

        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {
                    "description": "Action with many instructions",
                    "instructions": many_instructions,
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        # Act & Assert
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            stage = Stage("test_id", stage_config)

            # Should emit a warning about too many instructions
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "15 instructions" in str(w[0].message)
            assert "concise" in str(w[0].message)

        # Stage should still be created successfully
        assert len(stage.stage_actions[0]["instructions"]) == 15


class TestActionDefinitionCompleteStructure:
    """Test ActionDefinition with all fields (name, description, instructions, related_properties)."""

    def test_action_with_all_fields(self):
        """Verify action can include all optional and required fields."""
        # Arrange & Act
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
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field2",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [
                {
                    "name": "complete_form",
                    "description": "Complete the registration form",
                    "instructions": [
                        "Fill in your email address",
                        "Choose a strong password",
                        "Verify your phone number",
                    ],
                    "related_properties": ["field1", "field2"],
                }
            ],
            "expected_properties": {"field1": None, "field2": None},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        action = stage.stage_actions[0]
        assert action["name"] == "complete_form"
        assert action["description"] == "Complete the registration form"
        assert len(action["instructions"]) == 3
        assert action["related_properties"] == ["field1", "field2"]

    def test_mixed_action_formats(self):
        """Verify stage can have mix of old format and new format actions."""
        # Arrange & Act
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
                            "type": LockType.EXISTS,
                            "property_path": "field1",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field2",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [
                # Old format (backward compatible)
                {
                    "description": "Simple action",
                    "related_properties": ["field1"],
                },
                # New format with all fields
                {
                    "name": "enhanced_action",
                    "description": "Enhanced action with instructions",
                    "instructions": ["Step 1", "Step 2"],
                    "related_properties": ["field2"],
                },
            ],
            "expected_properties": {"field1": None, "field2": None},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Assert
        assert len(stage.stage_actions) == 2

        # First action (old format)
        action1 = stage.stage_actions[0]
        assert action1["description"] == "Simple action"
        assert "name" not in action1
        assert "instructions" not in action1

        # Second action (new format)
        action2 = stage.stage_actions[1]
        assert action2["name"] == "enhanced_action"
        assert action2["description"] == "Enhanced action with instructions"
        assert len(action2["instructions"]) == 2


class TestActionDefinitionSerialization:
    """Test that enhanced actions are properly serialized."""

    def test_stage_serialization_preserves_enhanced_actions(self):
        """Verify stage.to_dict() preserves enhanced action structure."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "test_stage",
            "description": "Test stage",
            "gates": [],
            "expected_actions": [
                {
                    "name": "test_action",
                    "description": "Test action description",
                    "instructions": ["Instruction 1", "Instruction 2"],
                }
            ],
            "expected_properties": {},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Act
        serialized = stage.to_dict()

        # Assert
        assert len(serialized["expected_actions"]) == 1
        action = serialized["expected_actions"][0]
        assert action["name"] == "test_action"
        assert action["description"] == "Test action description"
        assert len(action["instructions"]) == 2
        assert action["instructions"][0] == "Instruction 1"


class TestActionDefinitionIntegration:
    """Integration tests for enhanced actions in stage evaluation."""

    def test_stage_evaluation_includes_enhanced_actions(self):
        """Verify stage evaluation results include enhanced action information."""
        # Arrange
        element_data = {"field1": "value1"}
        element = DictElement(element_data)

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
                        # This will fail
                        {
                            "type": LockType.EXISTS,
                            "property_path": "field2",
                            "expected_value": None,
                        }
                    ],
                }
            ],
            "expected_actions": [
                {
                    "name": "add_field",
                    "description": "Add missing field",
                    "instructions": [
                        "Navigate to the field editor",
                        "Add field2 with appropriate value",
                    ],
                    "related_properties": ["field2"],
                }
            ],
            "expected_properties": {"field1": None, "field2": None},
            "is_final": False,
        }

        stage = Stage("test_id", stage_config)

        # Act
        _result = stage.evaluate(element)

        # Assert
        # The stage_actions should be available in the stage object
        assert len(stage.stage_actions) == 1
        assert stage.stage_actions[0]["name"] == "add_field"
        assert len(stage.stage_actions[0]["instructions"]) == 2


class TestRealWorldScenarios:
    """Test real-world scenarios with enhanced expected_actions."""

    def test_bug_tracking_workflow_actions(self):
        """Test enhanced actions in a bug tracking workflow."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "Bug Investigation",
            "description": "Investigate and document the bug",
            "gates": [
                {
                    "name": "documentation_complete",
                    "description": "Bug documentation is complete",
                    "target_stage": "fix_in_progress",
                    "parent_stage": "investigation",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "severity",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "description",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "steps_to_reproduce",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [
                {
                    "name": "document_bug",
                    "description": "Document the bug with complete information",
                    "instructions": [
                        "Set severity level (critical, high, medium, low)",
                        "Provide clear description of the bug",
                        "Add steps to reproduce",
                        "Document expected vs actual behavior",
                        "Attach relevant screenshots or logs",
                    ],
                    "related_properties": [
                        "severity",
                        "description",
                        "steps_to_reproduce",
                    ],
                }
            ],
            "expected_properties": {
                "severity": None,
                "description": None,
                "steps_to_reproduce": None,
            },
            "is_final": False,
        }

        stage = Stage("bug_investigation", stage_config)

        # Assert
        assert len(stage.stage_actions) == 1
        action = stage.stage_actions[0]
        assert action["name"] == "document_bug"
        assert len(action["instructions"]) == 5
        assert len(action["related_properties"]) == 3

    def test_feature_development_workflow_actions(self):
        """Test enhanced actions in a feature development workflow."""
        # Arrange
        stage_config: StageDefinition = {
            "name": "Feature Review",
            "description": "Review feature before deployment",
            "gates": [
                {
                    "name": "review_complete",
                    "description": "Feature review is complete",
                    "target_stage": "ready_for_deployment",
                    "parent_stage": "review",
                    "locks": [
                        {
                            "type": LockType.EXISTS,
                            "property_path": "testing_results",
                            "expected_value": None,
                        },
                        {
                            "type": LockType.EXISTS,
                            "property_path": "code_review_approved",
                            "expected_value": None,
                        },
                    ],
                }
            ],
            "expected_actions": [
                {
                    "name": "conduct_testing",
                    "description": "Complete testing for the feature",
                    "instructions": [
                        "Write unit tests for core functionality",
                        "Perform integration testing",
                        "Verify edge cases are handled",
                    ],
                    "related_properties": ["testing_results"],
                },
                {
                    "name": "request_code_review",
                    "description": "Get code review approval",
                    "instructions": [
                        "Create pull request with detailed description",
                        "Address reviewer feedback",
                        "Ensure all checks pass",
                    ],
                    "related_properties": ["code_review_approved"],
                },
            ],
            "expected_properties": {
                "testing_results": None,
                "code_review_approved": None,
            },
            "is_final": False,
        }

        stage = Stage("feature_review", stage_config)

        # Assert
        assert len(stage.stage_actions) == 2
        assert stage.stage_actions[0]["name"] == "conduct_testing"
        assert stage.stage_actions[1]["name"] == "request_code_review"
        assert len(stage.stage_actions[0]["instructions"]) == 3
        assert len(stage.stage_actions[1]["instructions"]) == 3
