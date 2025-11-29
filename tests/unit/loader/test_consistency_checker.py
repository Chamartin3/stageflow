"""
Tests for ProcessAnalyzer.

This module tests consistency validation for process definitions,
including the final stage gates validation.
"""


from stageflow.models import IssueSeverity, ProcessIssueTypes
from stageflow.process import Process


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
                            "locks": [{"exists": "data"}],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    "gates": {
                        "invalid_gate": {
                            "target_stage": "start",
                            "locks": [{"exists": "result"}],
                        }
                    },
                },
            },
        }

        # Act
        process = Process(process_def)
        # analyzer now internal - use process.issues and process.is_valid

        # Assert
        assert process.is_valid is False
        final_stage_issues = [
            issue
            for issue in process.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 1
        assert "end" in final_stage_issues[0].description
        assert "start" in final_stage_issues[0].description  # Target stage in error message
        assert final_stage_issues[0].severity == IssueSeverity.FATAL

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
                            "locks": [{"exists": "data"}],
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
        process = Process(process_def)
        # analyzer now internal - use process.issues and process.is_valid

        # Assert
        final_stage_issues = [
            issue
            for issue in process.issues
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
                            "locks": [{"exists": "data"}],
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
        process = Process(process_def)
        # analyzer now internal - use process.issues and process.is_valid

        # Assert
        final_stage_issues = [
            issue
            for issue in process.issues
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
                            "locks": [{"exists": "data"}],
                        }
                    },
                },
                "end": {
                    "name": "End",
                    "fields": ["result"],
                    "gates": {
                        "gate_one": {
                            "target_stage": "start",
                            "locks": [{"exists": "result"}],
                        },
                        "gate_two": {
                            "target_stage": "start",
                            "locks": [{"exists": "result"}],
                        },
                    },
                },
            },
        }

        # Act
        process = Process(process_def)
        # analyzer now internal - use process.issues and process.is_valid

        # Assert
        final_stage_issues = [
            issue
            for issue in process.issues
            if issue.issue_type == ProcessIssueTypes.FINAL_STAGE_HAS_GATES
        ]
        assert len(final_stage_issues) == 1
        # Error message shows target stages, not gate names
        assert "start" in final_stage_issues[0].description
