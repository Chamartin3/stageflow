"""Tests for new enums added in v2.0."""

import pytest

from stageflow.models import RegressionPolicy
from stageflow.stage import Action, ActionSource, ActionType, StageStatus


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
        assert ActionSource.GENERATED == "generated"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        assert ActionSource("configured") == ActionSource.CONFIGURED
        assert ActionSource("generated") == ActionSource.GENERATED

    def test_enum_invalid_value(self):
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ActionSource("invalid")


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
        from stageflow.models import RegressionDetails

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
        from stageflow.models import RegressionDetails

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


class TestActionDataclassUpdates:
    """Tests for Action dataclass new fields."""

    def test_action_with_defaults(self):
        """Test Action with default source and gate_name."""
        action = Action(
            description="Test action",
            related_properties=["email"],
            action_type=ActionType.UPDATE
        )

        assert action.source == ActionSource.CONFIGURED
        assert action.gate_name is None

    def test_action_with_explicit_source(self):
        """Test Action with explicit GENERATED source."""
        action = Action(
            description="Email must be verified",
            related_properties=["verified"],
            action_type=ActionType.EXCECUTE,
            source=ActionSource.GENERATED,
            gate_name="verify_email"
        )

        assert action.source == ActionSource.GENERATED
        assert action.gate_name == "verify_email"

    def test_action_immutability(self):
        """Test Action is still frozen/immutable."""
        action = Action(
            description="Test",
            related_properties=[],
            action_type=ActionType.UPDATE
        )

        with pytest.raises(AttributeError):
            action.description = "Modified"  # type: ignore
