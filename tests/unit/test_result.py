"""Unit tests for StatusResult and EvaluationState."""


import pytest

from stageflow.process.result import EvaluationState, StatusResult


class TestEvaluationState:
    """Test EvaluationState enumeration."""

    def test_evaluation_state_values(self):
        """Test that all evaluation states are defined with correct values."""
        assert EvaluationState.SCOPING.value == "scoping"
        assert EvaluationState.FULFILLING.value == "fulfilling"
        assert EvaluationState.QUALIFYING.value == "qualifying"
        assert EvaluationState.AWAITING.value == "awaiting"
        assert EvaluationState.ADVANCING.value == "advancing"
        assert EvaluationState.REGRESSING.value == "regressing"
        assert EvaluationState.COMPLETED.value == "completed"

    def test_evaluation_state_count(self):
        """Test expected number of evaluation states (7-state flow)."""
        states = list(EvaluationState)
        assert len(states) == 7

    def test_evaluation_state_string_representation(self):
        """Test string representation of evaluation states."""
        assert str(EvaluationState.SCOPING) == "ValidationState.SCOPING"
        assert EvaluationState.SCOPING.name == "SCOPING"

    def test_evaluation_state_comparison(self):
        """Test evaluation state comparison and equality."""
        assert EvaluationState.SCOPING == EvaluationState.SCOPING
        assert EvaluationState.SCOPING != EvaluationState.FULFILLING

    def test_evaluation_state_iteration(self):
        """Test that we can iterate over all evaluation states."""
        all_states = list(EvaluationState)
        expected_values = {
            "scoping", "fulfilling", "qualifying", "awaiting",
            "advancing", "regressing", "completed"
        }
        actual_values = {state.value for state in all_states}
        assert actual_values == expected_values


class TestStatusResultCreation:
    """Test StatusResult creation and initialization."""

    def test_status_result_basic_creation(self):
        """Test basic StatusResult creation."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=["Complete profile"],
            metadata={"user_id": "123"},
            errors=[]
        )

        assert result.state == EvaluationState.FULFILLING
        assert result.current_stage == "stage1"
        assert result.proposed_stage == "stage1"
        assert result.actions == ["Complete profile"]
        assert result.metadata == {"user_id": "123"}
        assert result.errors == []

    def test_status_result_minimal_creation(self):
        """Test StatusResult creation with minimal required fields."""
        result = StatusResult(
            state=EvaluationState.SCOPING,
            current_stage=None,
            proposed_stage=None,
            actions=[],
            metadata={},
            errors=[]
        )

        assert result.state == EvaluationState.SCOPING
        assert result.current_stage is None
        assert result.proposed_stage is None
        assert result.actions == []
        assert result.metadata == {}
        assert result.errors == []

    def test_status_result_immutability(self):
        """Test that StatusResult is immutable (frozen dataclass)."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=["Complete profile"],
            metadata={"user_id": "123"},
            errors=[]
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            result.state = EvaluationState.COMPLETED

        with pytest.raises(AttributeError):
            result.current_stage = "stage2"

    def test_status_result_post_init_validation(self):
        """Test StatusResult post-initialization validation."""
        # These should not raise exceptions due to current implementation
        # which allows flexibility in the post_init validation

        # Completed state with current_stage
        result = StatusResult(
            state=EvaluationState.COMPLETED,
            current_stage="stage1",  # This is allowed
            proposed_stage=None,
            actions=["Process completed"],
            metadata={},
            errors=[]
        )
        assert result.state == EvaluationState.COMPLETED

        # Scoping state without current_stage
        result = StatusResult(
            state=EvaluationState.SCOPING,
            current_stage=None,  # This is allowed
            proposed_stage=None,
            actions=[],
            metadata={},
            errors=[]
        )
        assert result.state == EvaluationState.SCOPING


class TestStatusResultClassMethods:
    """Test StatusResult class method constructors."""

    def test_scoping_class_method(self):
        """Test StatusResult.scoping() class method."""
        result = StatusResult.scoping()

        assert result.state == EvaluationState.SCOPING
        assert result.current_stage is None
        assert result.proposed_stage is None
        assert result.actions == []
        assert result.metadata == {}
        assert result.errors == []

    def test_scoping_with_parameters(self):
        """Test StatusResult.scoping() with parameters."""
        actions = ["Determine initial stage"]
        metadata = {"process_id": "abc123"}
        errors = ["Missing required data"]

        result = StatusResult.scoping(
            actions=actions,
            metadata=metadata,
            errors=errors
        )

        assert result.state == EvaluationState.SCOPING
        assert result.actions == actions
        assert result.metadata == metadata
        assert result.errors == errors

    def test_fulfilling_class_method(self):
        """Test StatusResult.fulfilling() class method."""
        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete email verification"]
        )

        assert result.state == EvaluationState.FULFILLING
        assert result.current_stage == "profile_setup"
        assert result.proposed_stage == "profile_setup"
        assert result.actions == ["Complete email verification"]
        assert result.metadata == {}
        assert result.errors == []

    def test_fulfilling_with_optional_parameters(self):
        """Test StatusResult.fulfilling() with optional parameters."""
        metadata = {"progress": 0.75}
        errors = ["Validation warning"]

        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete email verification"],
            metadata=metadata,
            errors=errors
        )

        assert result.metadata == metadata
        assert result.errors == errors

    def test_qualifying_class_method(self):
        """Test StatusResult.qualifying() class method."""
        result = StatusResult.qualifying(current_stage="profile_setup")

        assert result.state == EvaluationState.QUALIFYING
        assert result.current_stage == "profile_setup"
        assert result.proposed_stage == "profile_setup"
        assert result.actions == []  # No default actions generated
        assert result.metadata == {}
        assert result.errors == []

    def test_qualifying_with_optional_parameters(self):
        """Test StatusResult.qualifying() with optional parameters."""
        metadata = {"score": 95}
        errors = []

        result = StatusResult.qualifying(
            current_stage="profile_setup",
            metadata=metadata,
            errors=errors
        )

        assert result.metadata == metadata
        assert result.errors == errors

    def test_awaiting_class_method(self):
        """Test StatusResult.awaiting() class method."""
        actions = ["Wait for email verification", "Check external system"]

        result = StatusResult.awaiting(
            current_stage="email_verification",
            actions=actions
        )

        assert result.state == EvaluationState.AWAITING
        assert result.current_stage == "email_verification"
        assert result.proposed_stage == "email_verification"
        assert result.actions == actions
        assert result.metadata == {}
        assert result.errors == []

    def test_awaiting_with_optional_parameters(self):
        """Test StatusResult.awaiting() with optional parameters."""
        metadata = {"wait_time": 300}
        errors = ["Timeout warning"]

        result = StatusResult.awaiting(
            current_stage="email_verification",
            actions=["Wait for email verification"],
            metadata=metadata,
            errors=errors
        )

        assert result.metadata == metadata
        assert result.errors == errors

    def test_advancing_class_method(self):
        """Test StatusResult.advancing() class method."""
        result = StatusResult.advancing(
            current_stage="profile_setup",
            proposed_stage="email_verification"
        )

        assert result.state == EvaluationState.ADVANCING
        assert result.current_stage == "profile_setup"
        assert result.proposed_stage == "email_verification"
        assert result.actions == []  # No default actions generated
        assert result.metadata == {}
        assert result.errors == []

    def test_advancing_with_optional_parameters(self):
        """Test StatusResult.advancing() with optional parameters."""
        metadata = {"transition_time": "2023-01-01T12:00:00Z"}
        errors = []

        result = StatusResult.advancing(
            current_stage="profile_setup",
            proposed_stage="email_verification",
            metadata=metadata,
            errors=errors
        )

        assert result.metadata == metadata
        assert result.errors == errors

    def test_regressing_class_method(self):
        """Test StatusResult.regressing() class method."""
        actions = ["Fix validation errors", "Update profile data"]

        result = StatusResult.regressing(
            current_stage="email_verification",
            proposed_stage="profile_setup",
            actions=actions
        )

        assert result.state == EvaluationState.REGRESSING
        assert result.current_stage == "email_verification"
        assert result.proposed_stage == "profile_setup"
        assert result.actions == actions
        assert result.metadata == {}
        assert result.errors == []

    def test_regressing_with_optional_parameters(self):
        """Test StatusResult.regressing() with optional parameters."""
        metadata = {"regression_reason": "Invalid email format"}
        errors = ["Email validation failed"]

        result = StatusResult.regressing(
            current_stage="email_verification",
            proposed_stage="profile_setup",
            actions=["Fix validation errors"],
            metadata=metadata,
            errors=errors
        )

        assert result.metadata == metadata
        assert result.errors == errors

    def test_completed_class_method(self):
        """Test StatusResult.completed() class method."""
        result = StatusResult.completed()

        assert result.state == EvaluationState.COMPLETED
        assert result.current_stage is None
        assert result.proposed_stage is None
        assert result.actions == []  # No default actions generated
        assert result.metadata == {}
        assert result.errors == []

    def test_completed_with_optional_parameters(self):
        """Test StatusResult.completed() with optional parameters."""
        metadata = {"completion_time": "2023-01-01T12:00:00Z", "final_score": 100}
        errors = []

        result = StatusResult.completed(metadata=metadata, errors=errors)

        assert result.metadata == metadata
        assert result.errors == errors


class TestStatusResultInstanceMethods:
    """Test StatusResult instance methods."""

    def test_has_errors_true(self):
        """Test has_errors() method when errors exist."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=[],
            metadata={},
            errors=["Validation error", "Missing data"]
        )

        assert result.has_errors() is True

    def test_has_errors_false(self):
        """Test has_errors() method when no errors exist."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=[],
            metadata={},
            errors=[]
        )

        assert result.has_errors() is False

    def test_is_terminal_completed(self):
        """Test is_terminal() method for completed state."""
        result = StatusResult.completed()
        assert result.is_terminal() is True

    def test_is_terminal_with_errors(self):
        """Test is_terminal() method when errors exist."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=[],
            metadata={},
            errors=["Fatal error"]
        )

        assert result.is_terminal() is True

    def test_is_terminal_false(self):
        """Test is_terminal() method for non-terminal states."""
        non_terminal_states = [
            EvaluationState.SCOPING,
            EvaluationState.FULFILLING,
            EvaluationState.QUALIFYING,
            EvaluationState.AWAITING,
            EvaluationState.ADVANCING,
            EvaluationState.REGRESSING
        ]

        for state in non_terminal_states:
            result = StatusResult(
                state=state,
                current_stage="stage1",
                proposed_stage="stage1",
                actions=[],
                metadata={},
                errors=[]
            )
            assert result.is_terminal() is False

    def test_summary_no_errors_with_stage(self):
        """Test summary() method with no errors and stage information."""
        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete email field", "Add phone number"]
        )

        summary = result.summary()
        assert "Fulfilling" in summary
        assert "profile_setup" in summary
        assert "Complete email field" in summary
        assert "Add phone number" in summary

    def test_summary_no_errors_no_stage(self):
        """Test summary() method with no errors and no stage."""
        result = StatusResult.scoping(actions=["Determine initial stage"])

        summary = result.summary()
        assert "Scoping" in summary
        assert "Determine initial stage" in summary

    def test_summary_with_errors(self):
        """Test summary() method with errors."""
        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete email field"],
            errors=["Invalid email format", "Missing phone number"]
        )

        summary = result.summary()
        assert "Error in fulfilling" in summary
        assert "Invalid email format" in summary
        assert "Missing phone number" in summary

    def test_summary_no_actions(self):
        """Test summary() method with no actions."""
        result = StatusResult(
            state=EvaluationState.QUALIFYING,
            current_stage="profile_setup",
            proposed_stage="profile_setup",
            actions=[],
            metadata={},
            errors=[]
        )

        summary = result.summary()
        assert "Qualifying" in summary
        assert "profile_setup" in summary

    def test_summary_multiple_scenarios(self):
        """Test summary() method for various state scenarios."""
        # Scoping with no stage
        result = StatusResult.scoping()
        summary = result.summary()
        assert "Scoping" in summary

        # Completed state - no longer includes default action text
        result = StatusResult.completed()
        summary = result.summary()
        assert "Completed" in summary
        # No default actions are generated, so no action text in summary

        # Advancing state
        result = StatusResult.advancing(
            current_stage="stage1",
            proposed_stage="stage2"
        )
        summary = result.summary()
        assert "Advancing" in summary
        assert "stage1" in summary
        # Note: stage2 won't be in summary since it's proposed_stage, not in actions


class TestStatusResultEdgeCases:
    """Test StatusResult edge cases and error conditions."""

    def test_status_result_with_none_values(self):
        """Test StatusResult handling of None values."""
        result = StatusResult(
            state=EvaluationState.SCOPING,
            current_stage=None,
            proposed_stage=None,
            actions=[],
            metadata={},
            errors=[]
        )

        assert result.current_stage is None
        assert result.proposed_stage is None

    def test_status_result_with_empty_collections(self):
        """Test StatusResult with empty lists and dictionaries."""
        result = StatusResult(
            state=EvaluationState.FULFILLING,
            current_stage="stage1",
            proposed_stage="stage1",
            actions=[],
            metadata={},
            errors=[]
        )

        assert result.actions == []
        assert result.metadata == {}
        assert result.errors == []
        assert result.has_errors() is False

    def test_status_result_with_complex_metadata(self):
        """Test StatusResult with complex metadata structures."""
        complex_metadata = {
            "user": {
                "id": "123",
                "profile": {
                    "name": "John Doe",
                    "settings": ["email", "sms"]
                }
            },
            "process": {
                "version": "1.0",
                "started_at": "2023-01-01T12:00:00Z"
            },
            "metrics": {
                "completion_percentage": 75.5,
                "estimated_time_remaining": 300
            }
        }

        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete verification"],
            metadata=complex_metadata
        )

        assert result.metadata == complex_metadata
        assert result.metadata["user"]["id"] == "123"
        assert result.metadata["metrics"]["completion_percentage"] == 75.5

    def test_status_result_with_unicode_strings(self):
        """Test StatusResult with unicode strings."""
        result = StatusResult.fulfilling(
            current_stage="étape_profil",  # French
            actions=["完成验证", "проверить данные"],  # Chinese, Russian
            metadata={"用户": "João", "город": "São Paulo"},
            errors=["エラー発生"]  # Japanese
        )

        assert result.current_stage == "étape_profil"
        assert "完成验证" in result.actions
        assert "проверить данные" in result.actions
        assert result.metadata["用户"] == "João"
        assert result.metadata["город"] == "São Paulo"
        assert "エラー発生" in result.errors

    def test_status_result_large_collections(self):
        """Test StatusResult with large collections."""
        large_actions = [f"Action {i}" for i in range(100)]
        large_errors = [f"Error {i}" for i in range(50)]
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(200)}

        result = StatusResult.fulfilling(
            current_stage="large_stage",
            actions=large_actions,
            metadata=large_metadata,
            errors=large_errors
        )

        assert len(result.actions) == 100
        assert len(result.errors) == 50
        assert len(result.metadata) == 200
        assert result.has_errors() is True

    def test_status_result_string_representations(self):
        """Test string representations of StatusResult."""
        result = StatusResult.fulfilling(
            current_stage="profile_setup",
            actions=["Complete email verification"]
        )

        # Test that string representation doesn't throw errors
        str_repr = str(result)
        assert "StatusResult" in str_repr
        assert "FULFILLING" in str_repr

        repr_str = repr(result)
        assert "StatusResult" in repr_str

    def test_status_result_equality(self):
        """Test StatusResult equality comparison."""
        # Use explicit element_id and timestamp for consistent comparison
        from datetime import datetime
        fixed_timestamp = datetime(2023, 1, 1, 12, 0, 0)

        result1 = StatusResult.fulfilling(
            element_id="test_element",
            current_stage="stage1",
            actions=["action1"],
            timestamp=fixed_timestamp
        )

        result2 = StatusResult.fulfilling(
            element_id="test_element",
            current_stage="stage1",
            actions=["action1"],
            timestamp=fixed_timestamp
        )

        result3 = StatusResult.fulfilling(
            element_id="test_element",
            current_stage="stage2",
            actions=["action1"],
            timestamp=fixed_timestamp
        )

        # Same data should be equal
        assert result1 == result2

        # Different data should not be equal
        assert result1 != result3

    def test_status_result_hash(self):
        """Test StatusResult hash functionality - note that it's not hashable due to mutable fields."""
        # Use explicit element_id and timestamp for consistent comparison
        from datetime import datetime
        fixed_timestamp = datetime(2023, 1, 1, 12, 0, 0)

        result1 = StatusResult.fulfilling(
            element_id="test_element",
            current_stage="stage1",
            actions=["action1"],
            timestamp=fixed_timestamp
        )

        result2 = StatusResult.fulfilling(
            element_id="test_element",
            current_stage="stage1",
            actions=["action1"],
            timestamp=fixed_timestamp
        )

        # StatusResult is not hashable due to list/dict fields, so test that it raises TypeError
        with pytest.raises(TypeError):
            hash(result1)

        # But equality should still work
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__])
