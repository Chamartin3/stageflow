"""Tests for StageEvaluationResult refactoring."""

from stageflow.stage import (
    StageEvaluationResult,
    StageStatus,
    GateResult,
    ActionSource
)


def test_stage_evaluation_result_new_fields():
    """Test new field names work correctly."""
    result = StageEvaluationResult(
        status=StageStatus.INCOMPLETE,
        results={},
        configured_actions=[],
        validation_messages=["Missing property 'email'"]
    )

    assert result.status == StageStatus.INCOMPLETE
    assert result.results == {}
    assert result.configured_actions == []
    assert len(result.validation_messages) == 1


def test_new_api_fields():
    """Test new API fields work correctly."""
    from stageflow.gate import GateResult

    result = StageEvaluationResult(
        status=StageStatus.BLOCKED,
        results={"gate1": GateResult(success=False)},
        configured_actions=[{"description": "Contact support"}],
        validation_messages=["Validation failed"]
    )

    # Test new fields
    assert result.results == {"gate1": GateResult(success=False)}
    assert len(result.configured_actions) == 1
    assert result.validation_messages == ["Validation failed"]