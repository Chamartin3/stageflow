"""Tests for regression checking functionality."""

import pytest
from stageflow.elements import create_element
from stageflow.models import RegressionPolicy
from stageflow.process import Process
from stageflow.stage import StageStatus


def test_check_regression_no_previous_stages():
    """Test regression check with no previous stages."""
    process = Process({
        "name": "test",
        "description": "Test process",
        "initial_stage": "stage1",
        "final_stage": "stage1",
        "stages": {
            "stage1": {
                "name": "Stage 1",
                "description": "First stage",
                "gates": [],
                "expected_actions": [],
                "expected_properties": {},
                "is_final": True
            }
        }
    })

    stage = process.get_stage("stage1")
    assert stage is not None
    details = process._check_regression(
        create_element({}), stage, RegressionPolicy.WARN
    )

    assert not details["detected"]
    assert details["policy"] == "warn"


def test_check_regression_previous_stage_failed():
    """Test regression detected when previous stage fails."""
    process = Process({
        "name": "test",
        "initial_stage": "stage1",
        "final_stage": "stage2",
        "stages": {
            "stage1": {
                "name": "Stage 1",
                "description": "First stage",
                "gates": [{
                    "name": "to_stage2",
                    "target_stage": "stage2",
                    "locks": [{"exists": "email"}]
                }],
                "expected_actions": [],
                "expected_properties": {},
                "is_final": False
            },
            "stage2": {
                "name": "Stage 2",
                "description": "Second stage",
                "gates": [],
                "expected_actions": [],
                "expected_properties": {},
                "is_final": True
            }
        }
    })

    # Element at stage2 but missing email (regression)
    element = create_element({})
    stage2 = process.get_stage("stage2")
    details = process._check_regression(
        element, stage2, RegressionPolicy.WARN
    )

    assert details["detected"]
    assert "stage1" in details["failed_stages"]
    assert details["failed_statuses"]["stage1"] == "incomplete"