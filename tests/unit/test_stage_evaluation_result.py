"""Tests for StageEvaluationResult."""

from stageflow.models import ActionSource, ActionType
from stageflow.stage import StageEvaluationResult, StageStatus


def test_stage_evaluation_result_new_fields():
    """Test unified actions field works correctly."""
    result = StageEvaluationResult(
        status=StageStatus.INCOMPLETE,
        results={},
        actions=[
            {
                "action_type": ActionType.PROVIDE_DATA,
                "source": ActionSource.COMPUTED,
                "description": "Provide required property 'email'",
                "related_properties": [],
                "target_properties": ["email"],
            }
        ],
        validation_messages=["Missing property 'email'"]
    )

    assert result.status == StageStatus.INCOMPLETE
    assert result.results == {}
    assert len(result.actions) == 1
    assert result.actions[0]["action_type"] == ActionType.PROVIDE_DATA
    assert result.actions[0]["source"] == ActionSource.COMPUTED
    assert len(result.validation_messages) == 1


def test_new_api_fields():
    """Test new API fields work correctly."""
    from stageflow.gate import GateResult

    result = StageEvaluationResult(
        status=StageStatus.BLOCKED,
        results={"gate1": GateResult(success=False)},
        actions=[
            {
                "action_type": ActionType.RESOLVE_VALIDATION,
                "source": ActionSource.COMPUTED,
                "description": "Validation failed",
                "related_properties": [],
                "target_properties": ["field1"],
                "gate_name": "gate1",
            }
        ],
        validation_messages=["Validation failed"]
    )

    # Test new fields
    assert result.results == {"gate1": GateResult(success=False)}
    assert len(result.actions) == 1
    assert result.actions[0]["action_type"] == ActionType.RESOLVE_VALIDATION
    assert result.actions[0]["source"] == ActionSource.COMPUTED
    assert result.validation_messages == ["Validation failed"]


def test_configured_actions_have_priority():
    """Test that configured actions use EXECUTE_ACTION type."""
    result = StageEvaluationResult(
        status=StageStatus.BLOCKED,
        results={},
        actions=[
            {
                "action_type": ActionType.EXECUTE_ACTION,
                "source": ActionSource.CONFIGURED,
                "description": "Contact support",
                "related_properties": [],
                "target_properties": ["verified"],
            }
        ],
        validation_messages=[]
    )

    assert result.actions[0]["action_type"] == ActionType.EXECUTE_ACTION
    assert result.actions[0]["source"] == ActionSource.CONFIGURED


def test_transition_action():
    """Test TRANSITION action for READY status."""
    from stageflow.gate import GateResult

    result = StageEvaluationResult(
        status=StageStatus.READY,
        results={"complete_gate": GateResult(success=True)},
        actions=[
            {
                "action_type": ActionType.TRANSITION,
                "source": ActionSource.COMPUTED,
                "description": "Ready to transition to 'next'",
                "related_properties": ["email", "verified"],
                "target_properties": [],
                "target_stage": "next",
                "gate_name": "complete_gate",
            }
        ],
        validation_messages=["Ready to transition"]
    )

    assert result.status == StageStatus.READY
    assert len(result.actions) == 1
    assert result.actions[0]["action_type"] == ActionType.TRANSITION
    assert result.actions[0]["target_stage"] == "next"
    assert result.actions[0]["gate_name"] == "complete_gate"
