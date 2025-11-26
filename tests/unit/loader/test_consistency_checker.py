"""
Tests for ProcessConsistencyChecker.

This module tests consistency validation for process definitions,
including the final stage gates validation.
"""


from stageflow.loader.consistency_checker import ProcessConsistencyChecker
from stageflow.models import ProcessIssueTypes


class TestFinalStageHasNoGates:
    """Test that final stages cannot have outgoing gates."""

    def test_final_stage_with_gates_raises_error(self):
        """Verify that a final stage with gates produces an error."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                    "gates": {
                        "to_end": {
                            "target_stage": "end",
                            "locks": [],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    "gates": {
                        "invalid_gate": {
                            "target_stage": "start",
                            "locks": [],
                        }
                    },
                },
            },
        }

        # Act
        checker = ProcessConsistencyChecker(process_def)

        # Assert
        assert checker.valid is False
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 1
        assert "end" in final_stage_issues[0].description
        assert "invalid_gate" in final_stage_issues[0].description
        assert final_stage_issues[0].severity == "error"

    def test_final_stage_without_gates_is_valid(self):
        """Verify that a final stage without gates passes validation."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                    "gates": {
                        "to_end": {
                            "target_stage": "end",
                            "locks": [],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    # No gates - this is correct for a final stage
                },
            },
        }

        # Act
        checker = ProcessConsistencyChecker(process_def)

        # Assert
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 0

    def test_final_stage_with_empty_gates_dict_is_valid(self):
        """Verify that a final stage with empty gates dict passes validation."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                    "gates": {
                        "to_end": {
                            "target_stage": "end",
                            "locks": [],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    "gates": {},  # Empty gates dict is fine
                },
            },
        }

        # Act
        checker = ProcessConsistencyChecker(process_def)

        # Assert
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 0

    def test_final_stage_with_multiple_gates_lists_all(self):
        """Verify that all gate names are listed when final stage has multiple gates."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                    "gates": {
                        "to_end": {
                            "target_stage": "end",
                            "locks": [],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    "gates": {
                        "gate_one": {
                            "target_stage": "start",
                            "locks": [],
                        },
                        "gate_two": {
                            "target_stage": "start",
                            "locks": [],
                        },
                    },
                },
            },
        }

        # Act
        checker = ProcessConsistencyChecker(process_def)

        # Assert
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 1
        assert "gate_one" in final_stage_issues[0].description
        assert "gate_two" in final_stage_issues[0].description

    def test_missing_final_stage_does_not_crash(self):
        """Verify checker handles missing final_stage gracefully."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            # No final_stage defined
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                },
            },
        }

        # Act - should not raise
        checker = ProcessConsistencyChecker(process_def)

        # Assert - no FINAL_STAGE_HAS_GATES issue (can't check without final_stage)
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 0

    def test_nonexistent_final_stage_does_not_crash(self):
        """Verify checker handles nonexistent final_stage gracefully."""
        # Arrange
        process_def = {
            "name": "test_process",
            "initial_stage": "start",
            "final_stage": "nonexistent",
            "stages": {
                "start": {
                    "name": "Start",
                    "fields": ["data"],
                },
            },
        }

        # Act - should not raise
        checker = ProcessConsistencyChecker(process_def)

        # Assert - no FINAL_STAGE_HAS_GATES issue (stage doesn't exist)
        final_stage_issues = [
            issue
            for issue in checker.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 0
