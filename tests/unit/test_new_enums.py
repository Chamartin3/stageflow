"""Tests for enums and types added in v2.0."""

import pytest

from stageflow.models import (
    Action,
    ActionSource,
    ActionType,
    RegressionDetails,
    RegressionPolicy,
)
from stageflow.stage import StageStatus


class TestRegressionPolicyEnum:
    """Tests for RegressionPolicy enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert RegressionPolicy.IGNORE == "ignore"
        assert RegressionPolicy.WARN == "warn"
        assert RegressionPolicy.BLOCK == "block"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        assert RegressionPolicy("ignore") == RegressionPolicy.IGNORE
        assert RegressionPolicy("warn") == RegressionPolicy.WARN
        assert RegressionPolicy("block") == RegressionPolicy.BLOCK

    def test_enum_invalid_value(self):
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            RegressionPolicy("invalid")

    def test_enum_membership(self):
        """Test membership checks."""
        values = [p.value for p in RegressionPolicy]
        assert "ignore" in values
        assert "warn" in values
        assert "block" in values
        assert len(values) == 3


class TestActionSourceEnum:
    """Tests for ActionSource enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert ActionSource.CONFIGURED == "configured"
        assert ActionSource.COMPUTED == "computed"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        assert ActionSource("configured") == ActionSource.CONFIGURED
        assert ActionSource("computed") == ActionSource.COMPUTED

    def test_enum_invalid_value(self):
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ActionSource("invalid")


class TestActionTypeEnum:
    """Tests for ActionType enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert ActionType.PROVIDE_DATA == "provide_data"
        assert ActionType.RESOLVE_VALIDATION == "resolve_validation"
        assert ActionType.EXECUTE_ACTION == "execute_action"
        assert ActionType.TRANSITION == "transition"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        assert ActionType("provide_data") == ActionType.PROVIDE_DATA
        assert ActionType("resolve_validation") == ActionType.RESOLVE_VALIDATION
        assert ActionType("execute_action") == ActionType.EXECUTE_ACTION
        assert ActionType("transition") == ActionType.TRANSITION

    def test_enum_invalid_value(self):
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ActionType("invalid")


class TestStageStatusAliases:
    """Tests for StageStatus aliases during migration."""

    def test_new_status_names(self):
        """Test new status names exist."""
        assert StageStatus.INCOMPLETE
        assert StageStatus.BLOCKED
        assert StageStatus.READY

    def test_string_values(self):
        """Test string values are correct."""
        assert StageStatus.INCOMPLETE.value == "incomplete"
        assert StageStatus.BLOCKED.value == "blocked"
        assert StageStatus.READY.value == "ready"


class TestRegressionDetailsType:
    """Tests for RegressionDetails TypedDict."""

    def test_minimal_instance(self):
        """Test creating minimal valid instance."""
        details: RegressionDetails = {
            "detected": False,
            "policy": "warn",
            "failed_stages": [],
            "failed_statuses": {}
        }

        assert details["detected"] is False
        assert details["policy"] == "warn"
        assert details["failed_stages"] == []
        assert details["failed_statuses"] == {}

    def test_full_instance(self):
        """Test creating instance with all optional fields."""
        details: RegressionDetails = {
            "detected": True,
            "policy": "block",
            "failed_stages": ["stage1", "stage2"],
            "failed_statuses": {
                "stage1": "incomplete",
                "stage2": "blocked"
            },
            "missing_properties": {
                "stage1": ["email", "password"]
            },
            "failed_gates": {
                "stage2": ["verify_email"]
            }
        }

        assert details["detected"] is True
        assert len(details["failed_stages"]) == 2
        assert "missing_properties" in details
        assert "failed_gates" in details


class TestActionTypedDict:
    """Tests for Action TypedDict structure."""

    def test_action_with_required_fields(self):
        """Test Action with all required fields."""
        action: Action = {
            "action_type": ActionType.PROVIDE_DATA,
            "source": ActionSource.COMPUTED,
            "description": "Provide required property 'email'",
            "related_properties": [],
            "target_properties": ["email"],
        }

        assert action["action_type"] == ActionType.PROVIDE_DATA
        assert action["source"] == ActionSource.COMPUTED
        assert action["description"] == "Provide required property 'email'"
        assert action["target_properties"] == ["email"]

    def test_action_with_optional_fields(self):
        """Test Action with optional fields."""
        action: Action = {
            "action_type": ActionType.TRANSITION,
            "source": ActionSource.COMPUTED,
            "description": "Ready to transition to 'next'",
            "related_properties": ["email", "name"],
            "target_properties": [],
            "target_stage": "next",
            "gate_name": "complete_gate",
        }

        assert action["target_stage"] == "next"
        assert action["gate_name"] == "complete_gate"

    def test_execute_action_type(self):
        """Test EXECUTE_ACTION for configured actions."""
        action: Action = {
            "action_type": ActionType.EXECUTE_ACTION,
            "source": ActionSource.CONFIGURED,
            "description": "Contact support for verification",
            "related_properties": ["support_ticket"],
            "target_properties": ["verified"],
            "name": "contact_support",
            "instructions": ["Call the support hotline", "Provide your ticket number"],
        }

        assert action["action_type"] == ActionType.EXECUTE_ACTION
        assert action["source"] == ActionSource.CONFIGURED
        assert action["name"] == "contact_support"
        assert len(action["instructions"]) == 2

    def test_resolve_validation_type(self):
        """Test RESOLVE_VALIDATION for computed actions from failed gates."""
        action: Action = {
            "action_type": ActionType.RESOLVE_VALIDATION,
            "source": ActionSource.COMPUTED,
            "description": "Email must be verified",
            "related_properties": [],
            "target_properties": ["verified"],
            "gate_name": "verify_email",
        }

        assert action["action_type"] == ActionType.RESOLVE_VALIDATION
        assert action["source"] == ActionSource.COMPUTED
        assert action["gate_name"] == "verify_email"
