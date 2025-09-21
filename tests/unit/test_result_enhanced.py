"""Enhanced unit tests for StatusResult and related classes."""

import json
from datetime import datetime

import pytest

from stageflow.process.result import (
    Action,
    ActionType,
    DiagnosticInfo,
    ErrorInfo,
    EvaluationState,
    Priority,
    Severity,
    StatusResult,
    WarningInfo,
)


class TestEnhancedEvaluationState:
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


class TestAction:
    """Test Action class functionality."""

    def test_action_creation(self):
        """Test Action creation with all parameters."""
        action = Action(
            type=ActionType.COMPLETE_FIELD,
            description="Complete the email field",
            priority=Priority.HIGH,
            conditions=["email_field_empty"],
            metadata={"field": "email", "required": True}
        )

        assert action.type == ActionType.COMPLETE_FIELD
        assert action.description == "Complete the email field"
        assert action.priority == Priority.HIGH
        assert action.conditions == ["email_field_empty"]
        assert action.metadata == {"field": "email", "required": True}

    def test_action_minimal_creation(self):
        """Test Action creation with minimal parameters."""
        action = Action(
            type=ActionType.VALIDATE_DATA,
            description="Validate user data"
        )

        assert action.type == ActionType.VALIDATE_DATA
        assert action.description == "Validate user data"
        assert action.priority == Priority.NORMAL
        assert action.conditions == []
        assert action.metadata == {}

    def test_action_to_dict(self):
        """Test Action serialization to dictionary."""
        action = Action(
            type=ActionType.TRANSITION_STAGE,
            description="Move to next stage",
            priority=Priority.CRITICAL,
            conditions=["requirements_met"],
            metadata={"target_stage": "verification"}
        )

        result = action.to_dict()
        expected = {
            "type": "transition_stage",
            "description": "Move to next stage",
            "priority": "critical",
            "conditions": ["requirements_met"],
            "metadata": {"target_stage": "verification"}
        }

        assert result == expected


class TestDiagnosticInfo:
    """Test DiagnosticInfo class functionality."""

    def test_diagnostic_creation(self):
        """Test DiagnosticInfo creation."""
        diagnostic = DiagnosticInfo(
            category="validation",
            message="Field validation passed",
            details={"field": "email", "pattern": "email_regex"},
            severity=Severity.INFO
        )

        assert diagnostic.category == "validation"
        assert diagnostic.message == "Field validation passed"
        assert diagnostic.details == {"field": "email", "pattern": "email_regex"}
        assert diagnostic.severity == Severity.INFO
        assert isinstance(diagnostic.timestamp, datetime)

    def test_diagnostic_minimal_creation(self):
        """Test DiagnosticInfo creation with minimal parameters."""
        diagnostic = DiagnosticInfo(
            category="process",
            message="Stage transition detected"
        )

        assert diagnostic.category == "process"
        assert diagnostic.message == "Stage transition detected"
        assert diagnostic.details == {}
        assert diagnostic.severity == Severity.INFO
        assert isinstance(diagnostic.timestamp, datetime)

    def test_diagnostic_to_dict(self):
        """Test DiagnosticInfo serialization to dictionary."""
        diagnostic = DiagnosticInfo(
            category="performance",
            message="Operation completed in 150ms",
            details={"duration_ms": 150, "operation": "validation"},
            severity=Severity.DEBUG
        )

        result = diagnostic.to_dict()
        assert result["category"] == "performance"
        assert result["message"] == "Operation completed in 150ms"
        assert result["details"] == {"duration_ms": 150, "operation": "validation"}
        assert result["severity"] == "debug"
        assert "timestamp" in result


class TestErrorInfo:
    """Test ErrorInfo class functionality."""

    def test_error_creation(self):
        """Test ErrorInfo creation."""
        error = ErrorInfo(
            code="VALIDATION_FAILED",
            message="Email format is invalid",
            category="validation",
            details={"field": "email", "value": "invalid-email"},
            severity=Severity.ERROR
        )

        assert error.code == "VALIDATION_FAILED"
        assert error.message == "Email format is invalid"
        assert error.category == "validation"
        assert error.details == {"field": "email", "value": "invalid-email"}
        assert error.severity == Severity.ERROR
        assert isinstance(error.timestamp, datetime)

    def test_error_minimal_creation(self):
        """Test ErrorInfo creation with minimal parameters."""
        error = ErrorInfo(
            code="GENERAL_ERROR",
            message="An error occurred"
        )

        assert error.code == "GENERAL_ERROR"
        assert error.message == "An error occurred"
        assert error.category == "general"
        assert error.details == {}
        assert error.severity == Severity.ERROR
        assert isinstance(error.timestamp, datetime)

    def test_error_to_dict(self):
        """Test ErrorInfo serialization to dictionary."""
        error = ErrorInfo(
            code="DEPENDENCY_MISSING",
            message="Required dependency not found",
            category="system",
            details={"dependency": "external_service"},
            severity=Severity.CRITICAL
        )

        result = error.to_dict()
        assert result["code"] == "DEPENDENCY_MISSING"
        assert result["message"] == "Required dependency not found"
        assert result["category"] == "system"
        assert result["details"] == {"dependency": "external_service"}
        assert result["severity"] == "critical"
        assert "timestamp" in result


class TestWarningInfo:
    """Test WarningInfo class functionality."""

    def test_warning_creation(self):
        """Test WarningInfo creation."""
        warning = WarningInfo(
            code="DEPRECATED_FIELD",
            message="Field will be deprecated in next version",
            category="compatibility",
            details={"field": "old_email", "replacement": "email"}
        )

        assert warning.code == "DEPRECATED_FIELD"
        assert warning.message == "Field will be deprecated in next version"
        assert warning.category == "compatibility"
        assert warning.details == {"field": "old_email", "replacement": "email"}
        assert isinstance(warning.timestamp, datetime)

    def test_warning_to_dict(self):
        """Test WarningInfo serialization to dictionary."""
        warning = WarningInfo(
            code="PERFORMANCE_WARNING",
            message="Operation took longer than expected",
            category="performance",
            details={"expected_ms": 100, "actual_ms": 250}
        )

        result = warning.to_dict()
        assert result["code"] == "PERFORMANCE_WARNING"
        assert result["message"] == "Operation took longer than expected"
        assert result["category"] == "performance"
        assert result["details"] == {"expected_ms": 100, "actual_ms": 250}
        assert "timestamp" in result


class TestEnhancedStatusResult:
    """Test enhanced StatusResult functionality."""

    def test_status_result_basic_creation(self):
        """Test basic StatusResult creation with enhanced fields."""
        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            current_stage="profile_setup",
            proposed_stage="profile_setup",
            actions=["Complete email field"],
            metadata={"progress": 0.75}
        )

        assert result.element_id == "user_123"
        assert result.state == EvaluationState.FULFILLING
        assert result.current_stage == "profile_setup"
        assert result.proposed_stage == "profile_setup"
        assert result.actions == ["Complete email field"]
        assert result.metadata == {"progress": 0.75}
        assert result.errors == []
        assert result.warnings == []
        assert result.diagnostics == []
        assert isinstance(result.timestamp, datetime)

    def test_status_result_with_action_objects(self):
        """Test StatusResult with Action objects."""
        action = Action(
            type=ActionType.COMPLETE_FIELD,
            description="Complete the email field",
            priority=Priority.HIGH
        )

        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            actions=[action]
        )

        assert len(result.actions) == 1
        assert result.actions[0] == action

    def test_status_result_with_enhanced_diagnostics(self):
        """Test StatusResult with enhanced diagnostic information."""
        diagnostic = DiagnosticInfo(
            category="validation",
            message="Email format validated successfully"
        )

        error = ErrorInfo(
            code="REQUIRED_FIELD_MISSING",
            message="Name field is required"
        )

        warning = WarningInfo(
            code="PERFORMANCE_WARNING",
            message="Validation took longer than expected"
        )

        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            diagnostics=[diagnostic],
            errors=[error],
            warnings=[warning]
        )

        assert len(result.diagnostics) == 1
        assert result.diagnostics[0] == diagnostic
        assert len(result.errors) == 1
        assert result.errors[0] == error
        assert len(result.warnings) == 1
        assert result.warnings[0] == warning

    def test_status_result_class_methods(self):
        """Test StatusResult class method constructors."""
        # Test scoping
        result = StatusResult.scoping(
            element_id="user_123",
            actions=["Determine initial stage"],
            metadata={"process_id": "abc123"}
        )
        assert result.state == EvaluationState.SCOPING
        assert result.element_id == "user_123"

        # Test fulfilling
        result = StatusResult.fulfilling(
            element_id="user_123",
            current_stage="profile_setup",
            actions=["Complete email verification"]
        )
        assert result.state == EvaluationState.FULFILLING
        assert result.current_stage == "profile_setup"

        # Test qualifying
        result = StatusResult.qualifying(
            element_id="user_123",
            current_stage="profile_setup"
        )
        assert result.state == EvaluationState.QUALIFYING

        # Test awaiting
        result = StatusResult.awaiting(
            element_id="user_123",
            current_stage="email_verification",
            actions=["Wait for email confirmation"]
        )
        assert result.state == EvaluationState.AWAITING

        # Test advancing
        result = StatusResult.advancing(
            element_id="user_123",
            current_stage="profile_setup",
            proposed_stage="email_verification"
        )
        assert result.state == EvaluationState.ADVANCING

        # Test regressing
        result = StatusResult.regressing(
            element_id="user_123",
            current_stage="email_verification",
            proposed_stage="profile_setup",
            actions=["Fix validation errors"]
        )
        assert result.state == EvaluationState.REGRESSING

        # Test completed
        result = StatusResult.completed(
            element_id="user_123",
            metadata={"completion_time": "2023-01-01T12:00:00Z"}
        )
        assert result.state == EvaluationState.COMPLETED

    def test_status_result_add_methods(self):
        """Test StatusResult add methods for immutable updates."""
        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING
        )

        # Add action
        action = Action(ActionType.COMPLETE_FIELD, "Complete email")
        result_with_action = result.add_action(action)
        assert len(result_with_action.actions) == 1
        assert result_with_action.actions[0] == action
        assert len(result.actions) == 0  # Original unchanged

        # Add diagnostic
        diagnostic = DiagnosticInfo("validation", "Field validated")
        result_with_diagnostic = result.add_diagnostic(diagnostic)
        assert len(result_with_diagnostic.diagnostics) == 1
        assert result_with_diagnostic.diagnostics[0] == diagnostic

        # Add error
        error = ErrorInfo("ERR001", "Field error")
        result_with_error = result.add_error(error)
        assert len(result_with_error.errors) == 1
        assert result_with_error.errors[0] == error

        # Add warning
        warning = WarningInfo("WARN001", "Field warning")
        result_with_warning = result.add_warning(warning)
        assert len(result_with_warning.warnings) == 1
        assert result_with_warning.warnings[0] == warning

    def test_status_result_boolean_methods(self):
        """Test StatusResult boolean check methods."""
        # Test has_errors
        result_no_errors = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING
        )
        assert not result_no_errors.has_errors()

        result_with_errors = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            errors=["Error occurred"]
        )
        assert result_with_errors.has_errors()

        # Test has_warnings
        result_no_warnings = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING
        )
        assert not result_no_warnings.has_warnings()

        result_with_warnings = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            warnings=["Warning occurred"]
        )
        assert result_with_warnings.has_warnings()

        # Test is_successful
        assert result_no_errors.is_successful()
        assert not result_with_errors.is_successful()

        # Test is_terminal
        completed_result = StatusResult.completed(element_id="user_123")
        assert completed_result.is_terminal()
        assert result_with_errors.is_terminal()
        assert not result_no_errors.is_terminal()

    def test_status_result_serialization(self):
        """Test StatusResult serialization functionality."""
        action = Action(
            type=ActionType.COMPLETE_FIELD,
            description="Complete email field"
        )

        diagnostic = DiagnosticInfo(
            category="validation",
            message="Email format validated"
        )

        error = ErrorInfo(
            code="ERR001",
            message="Required field missing"
        )

        warning = WarningInfo(
            code="WARN001",
            message="Performance warning"
        )

        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            current_stage="profile_setup",
            actions=[action, "String action"],
            diagnostics=[diagnostic],
            errors=[error, "String error"],
            warnings=[warning, "String warning"],
            metadata={"progress": 0.75},
            processing_time_ms=150.5,
            performance_metrics={"cpu_usage": 25.0}
        )

        # Test to_dict
        result_dict = result.to_dict()
        assert result_dict["element_id"] == "user_123"
        assert result_dict["state"] == "fulfilling"
        assert result_dict["current_stage"] == "profile_setup"
        assert len(result_dict["actions"]) == 2
        assert isinstance(result_dict["actions"][0], dict)  # Action object serialized
        assert result_dict["actions"][1] == "String action"
        assert len(result_dict["diagnostics"]) == 1
        assert isinstance(result_dict["diagnostics"][0], dict)
        assert len(result_dict["errors"]) == 2
        assert len(result_dict["warnings"]) == 2
        assert result_dict["metadata"] == {"progress": 0.75}
        assert result_dict["processing_time_ms"] == 150.5
        assert result_dict["performance_metrics"] == {"cpu_usage": 25.0}

        # Test to_json
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["element_id"] == "user_123"
        assert parsed["state"] == "fulfilling"

    def test_status_result_summary_enhanced(self):
        """Test enhanced summary functionality."""
        # Test summary with Action objects
        action = Action(
            type=ActionType.COMPLETE_FIELD,
            description="Complete the email field"
        )

        result = StatusResult.fulfilling(
            element_id="user_123",
            current_stage="profile_setup",
            actions=[action, "Additional action"]
        )

        summary = result.summary()
        assert "Fulfilling" in summary
        assert "profile_setup" in summary
        assert "Complete the email field" in summary
        assert "Additional action" in summary

        # Test summary with ErrorInfo objects
        error = ErrorInfo(
            code="VALIDATION_ERROR",
            message="Email format is invalid"
        )

        result_with_error = StatusResult.fulfilling(
            element_id="user_123",
            current_stage="profile_setup",
            actions=[action],
            errors=[error, "String error"]
        )

        error_summary = result_with_error.summary()
        assert "Error in fulfilling" in error_summary
        assert "VALIDATION_ERROR: Email format is invalid" in error_summary
        assert "String error" in error_summary

    def test_status_result_performance_metrics(self):
        """Test performance metrics functionality."""
        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            processing_time_ms=250.75,
            performance_metrics={
                "cpu_usage_percent": 15.5,
                "memory_usage_mb": 128.0,
                "network_calls": 3,
                "cache_hits": 5,
                "cache_misses": 1
            }
        )

        assert result.processing_time_ms == 250.75
        assert result.performance_metrics["cpu_usage_percent"] == 15.5
        assert result.performance_metrics["memory_usage_mb"] == 128.0
        assert result.performance_metrics["network_calls"] == 3

        # Test serialization includes performance metrics
        result_dict = result.to_dict()
        assert result_dict["processing_time_ms"] == 250.75
        assert result_dict["performance_metrics"]["cpu_usage_percent"] == 15.5

    def test_status_result_validation(self):
        """Test StatusResult validation and error handling."""
        # Test that element_id is required
        with pytest.raises(ValueError, match="element_id is required"):
            StatusResult(
                element_id="",
                state=EvaluationState.FULFILLING
            )

        # Test immutability
        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING
        )

        with pytest.raises(AttributeError):
            result.state = EvaluationState.COMPLETED

    def test_status_result_mixed_types(self):
        """Test StatusResult with mixed string and object types."""
        action_obj = Action(ActionType.VALIDATE_DATA, "Validate email")
        error_obj = ErrorInfo("ERR001", "Validation failed")
        warning_obj = WarningInfo("WARN001", "Performance warning")

        result = StatusResult(
            element_id="user_123",
            state=EvaluationState.FULFILLING,
            actions=[action_obj, "String action"],
            errors=[error_obj, "String error"],
            warnings=[warning_obj, "String warning"]
        )

        # Test serialization handles mixed types
        result_dict = result.to_dict()
        assert len(result_dict["actions"]) == 2
        assert isinstance(result_dict["actions"][0], dict)
        assert result_dict["actions"][1] == "String action"

        assert len(result_dict["errors"]) == 2
        assert isinstance(result_dict["errors"][0], dict)
        assert result_dict["errors"][1] == "String error"

        # Test summary handles mixed types (when there are errors, summary shows errors)
        summary = result.summary()
        assert "Error in fulfilling" in summary
        assert "ERR001: Validation failed" in summary
        assert "String error" in summary


if __name__ == "__main__":
    pytest.main([__file__])
