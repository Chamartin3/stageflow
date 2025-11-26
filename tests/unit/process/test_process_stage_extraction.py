"""Unit tests for automatic stage extraction from element properties."""

import pytest

from stageflow import DictElement
from stageflow.process import Process, ProcessDefinition


class TestStageExtractionPrecedence:
    """Test stage selection precedence order."""

    def test_explicit_override_takes_precedence(self):
        """Explicit stage parameter should override auto-extraction."""
        # Process with stage_prop configured
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process with stage_prop",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_middle",
                            "target_stage": "middle",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "middle": {
                    "name": "Middle",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "middle",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with status="middle"
        element = DictElement({"status": "middle", "data": "test"})

        # Call evaluate with explicit stage override "start"
        result = process.evaluate(element, "start")

        # Assert current_stage is "start" (not "middle" from element)
        assert result["stage"] == "start"

    def test_auto_extraction_when_no_override(self):
        """Auto-extraction should work when no explicit stage provided."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_middle",
                            "target_stage": "middle",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "middle": {
                    "name": "Middle",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "middle",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with status="middle"
        element = DictElement({"status": "middle", "data": "test"})

        # Call evaluate without explicit stage
        result = process.evaluate(element)

        # Assert current_stage is "middle" (from auto-extraction)
        assert result["stage"] == "middle"

    def test_initial_stage_fallback(self):
        """Should fall back to initial_stage when no extraction configured."""
        # Process without stage_prop
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with any data (status field should be ignored)
        element = DictElement({"status": "middle", "data": "test"})

        # Call evaluate without explicit stage
        result = process.evaluate(element)

        # Assert current_stage is initial_stage
        assert result["stage"] == "start"


class TestStageExtractionValidation:
    """Test validation and error handling."""

    def test_property_not_found_in_element(self):
        """Should raise error when configured property doesn't exist."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element without "status" property
        element = DictElement({"data": "test"})

        # Should raise ValueError with helpful message
        with pytest.raises(ValueError) as exc_info:
            process.evaluate(element)

        assert "Stage property 'status' not found in element" in str(exc_info.value)

    def test_property_value_not_string(self):
        """Should raise error when property value is not a string."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with status=123 (integer)
        element = DictElement({"status": 123})

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            process.evaluate(element)

        assert "must be a string" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_invalid_stage_name(self):
        """Should raise error when extracted stage doesn't exist."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with status="nonexistent_stage"
        element = DictElement({"status": "nonexistent_stage"})

        # Should raise ValueError with list of available stages
        with pytest.raises(ValueError) as exc_info:
            process.evaluate(element)

        error_msg = str(exc_info.value)
        assert "not a valid stage" in error_msg
        assert "Available stages:" in error_msg
        assert "start" in error_msg
        assert "end" in error_msg

    def test_nested_property_path(self):
        """Should support dot notation for nested properties."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "meta.current_stage",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_middle",
                            "target_stage": "middle",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "middle": {
                    "name": "Middle",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "middle",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with nested meta.current_stage="middle"
        element = DictElement(
            {
                "data": "test",
                "meta": {"current_stage": "middle", "timestamp": "2024-01-01"},
            }
        )

        # Call evaluate without explicit stage
        result = process.evaluate(element)

        # Assert current_stage is "middle" (from nested property)
        assert result["stage"] == "middle"

    def test_bracket_notation_property_path(self):
        """Should support bracket notation for property paths."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "workflow.stages[0].name",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_active",
                            "target_stage": "active",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "active": {
                    "name": "Active",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "active",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Element with bracket notation path
        element = DictElement(
            {"workflow": {"stages": [{"name": "active", "completed": True}]}}
        )

        # Call evaluate without explicit stage
        result = process.evaluate(element)

        # Assert current_stage is "active" (from bracket notation)
        assert result["stage"] == "active"


class TestStageExtractionSerialization:
    """Test serialization and deserialization."""

    def test_to_dict_includes_property(self):
        """Process.to_dict() should include stage_prop."""
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "stage_prop": "status",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Call to_dict()
        result = process.to_dict()

        # Assert "stage_prop" in result
        assert "stage_prop" in result
        assert result["stage_prop"] == "status"

    def test_to_dict_omits_when_none(self):
        """Process.to_dict() should omit property when not configured."""
        # Process without stage_prop
        process_config: ProcessDefinition = {
            "name": "test_process",
            "description": "Test process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": {},
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "parent_stage": "start",
                            "locks": [{"exists": "status"}],  # Minimal lock for testing
                        }
                    ],
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # Call to_dict()
        result = process.to_dict()

        # Assert "stage_prop" not in result
        assert "stage_prop" not in result


class TestStageExtractionIntegration:
    """Integration tests with real-world scenarios."""

    def test_user_workflow_with_status_field(self):
        """Test realistic user workflow with status field."""
        process_config: ProcessDefinition = {
            "name": "user_workflow",
            "description": "User registration workflow",
            "stage_prop": "status",
            "initial_stage": "registration",
            "final_stage": "active",
            "stages": {
                "registration": {
                    "name": "Registration",
                    "fields": {
                        "email": {"type": "str"},
                        "verification": {
                            "email_verified_at": {"type": "str"},
                        },
                    },
                    "gates": [
                        {
                            "name": "email_verified",
                            "target_stage": "profile_setup",
                            "parent_stage": "registration",
                            "locks": [{"exists": "verification.email_verified_at"}],
                        }
                    ],
                    "is_final": False,
                },
                "profile_setup": {
                    "name": "Profile Setup",
                    "fields": {
                        "email": {"type": "str"},
                        "profile": {
                            "first_name": {"type": "str"},
                            "last_name": {"type": "str"},
                        },
                    },
                    "gates": [
                        {
                            "name": "profile_complete",
                            "target_stage": "active",
                            "parent_stage": "profile_setup",
                            "locks": [
                                {"exists": "profile.first_name"},
                                {"exists": "profile.last_name"},
                            ],
                        }
                    ],
                    "is_final": False,
                },
                "active": {
                    "name": "Active",
                    "fields": {},
                    "gates": [],
                    "is_final": True,
                },
            },
        }

        process = Process(process_config)

        # User in profile_setup stage with incomplete profile
        user = DictElement(
            {
                "email": "user@example.com",
                "status": "profile_setup",
                "verification": {"email_verified_at": "2024-01-01T10:00:00Z"},
                "profile": {
                    "first_name": "John"
                    # Missing last_name
                },
            }
        )

        # Evaluate without explicit stage (should use auto-extraction)
        result = process.evaluate(user)

        # Should evaluate at profile_setup stage
        assert result["stage"] == "profile_setup"
        # Should be incomplete (missing last_name - data missing)
        assert result["stage_result"].status == "incomplete"
