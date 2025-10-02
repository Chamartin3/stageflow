"""
Tests for simple example processes.

This module validates that all simple example processes work correctly
and produce expected evaluation results.
"""

from pathlib import Path

import pytest

from stageflow import Element, load_process
from stageflow.process.result import EvaluationState


class TestUserRegistrationExample:
    """Test the user registration simple example."""

    @pytest.fixture
    def process(self):
        """Load the user registration process."""
        examples_dir = Path(__file__).parent.parent.parent / "stageflow" / "examples"
        process_file = examples_dir / "simple" / "processes" / "user_registration.yaml"
        return load_process(process_file)

    def test_new_user_awaits_email_verification(self, process):
        """Test that new users are awaiting email verification."""
        user_data = {
            "email": "john@example.com",
            "password": "SecurePass123!",
            "meta": {"created_at": "2024-01-15T10:00:00Z"}
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "email_signup"
        assert result.state == EvaluationState.AWAITING
        assert not result.can_advance
        assert len(result.actions) > 0
        assert any("verification" in action.description.lower() for action in result.actions)

    def test_email_verified_user_can_setup_profile(self, process):
        """Test that users with verified email can set up profile."""
        user_data = {
            "email": "jane@example.com",
            "password": "StrongPass456!",
            "first_name": "Jane",
            "meta": {
                "email_verified_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-15T10:00:00Z"
            }
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "profile_setup"
        assert result.state == EvaluationState.FULFILLING
        assert not result.can_advance  # Missing last_name and terms

    def test_profile_complete_awaits_terms(self, process):
        """Test that users with complete profile await terms acceptance."""
        user_data = {
            "email": "bob@example.com",
            "password": "MyPassword789!",
            "first_name": "Bob",
            "last_name": "Wilson",
            "profile": {
                "required_fields": ["first_name", "last_name"]
            },
            "meta": {
                "email_verified_at": "2024-01-15T10:30:00Z",
                "terms_accepted": False,
                "created_at": "2024-01-15T10:00:00Z"
            }
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "profile_setup"
        assert result.state == EvaluationState.AWAITING

    def test_complete_registration_is_active(self, process):
        """Test that fully completed registration reaches active status."""
        user_data = {
            "email": "alice@example.com",
            "password": "GoodPass321!",
            "first_name": "Alice",
            "last_name": "Brown",
            "status": "active",
            "profile": {
                "required_fields": ["first_name", "last_name"]
            },
            "meta": {
                "email_verified_at": "2024-01-15T10:30:00Z",
                "terms_accepted": True,
                "created_at": "2024-01-15T10:00:00Z"
            }
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "active_user"
        assert result.state == EvaluationState.COMPLETED
        assert not result.can_advance  # Final stage
        assert len(result.actions) == 0

    def test_invalid_email_format_scoping(self, process):
        """Test that invalid email format puts user in scoping state."""
        user_data = {
            "email": "not-a-valid-email",
            "password": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User"
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "email_signup"
        assert result.state == EvaluationState.SCOPING
        assert len(result.errors) > 0

    def test_missing_required_fields_scoping(self, process):
        """Test that missing required fields puts user in scoping state."""
        user_data = {
            # Missing email and password
            "first_name": "Incomplete",
            "last_name": "User"
        }
        element = Element(user_data)
        result = process.evaluate(element)

        assert result.current_stage == "email_signup"
        assert result.state == EvaluationState.SCOPING
        assert len(result.errors) > 0


class TestTaskWorkflowExample:
    """Test the task workflow simple example."""

    @pytest.fixture
    def process(self):
        """Load the task workflow process."""
        examples_dir = Path(__file__).parent.parent.parent / "stageflow" / "examples"
        process_file = examples_dir / "simple" / "processes" / "task_workflow.yaml"
        return load_process(process_file)

    def test_new_task_awaits_assignment(self, process):
        """Test that new tasks await assignment."""
        task_data = {
            "title": "Design user dashboard",
            "description": "Create wireframes and mockups for the main user dashboard",
            "priority": "medium",
            "due_date": "2024-02-20",
            "labels": ["frontend", "design"],
            "meta": {"created_at": "2024-01-15T14:00:00Z"}
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_created"
        assert result.state == EvaluationState.AWAITING
        assert not result.can_advance

    def test_assigned_task_awaits_start(self, process):
        """Test that assigned tasks await work start."""
        task_data = {
            "title": "Write API documentation",
            "description": "Document all REST API endpoints with examples",
            "priority": "low",
            "due_date": "2024-02-25",
            "assignee": {
                "user_id": "tech_writer_001",
                "name": "Sarah Writer",
                "email": "sarah.writer@company.com"
            },
            "meta": {
                "created_at": "2024-01-15T11:00:00Z",
                "assigned_at": "2024-01-15T11:30:00Z"
            }
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_assigned"
        assert result.state == EvaluationState.AWAITING

    def test_work_in_progress_fulfilling(self, process):
        """Test that tasks in progress are in fulfilling state."""
        task_data = {
            "title": "Optimize database queries",
            "description": "Review and optimize slow-running database queries",
            "priority": "high",
            "assignee": {
                "user_id": "dba_001",
                "name": "Mike Database",
                "email": "mike.db@company.com"
            },
            "progress_notes": "Identified 5 slow queries, optimized 2 so far",
            "completion_percentage": 40,
            "meta": {
                "created_at": "2024-01-14T08:00:00Z",
                "assigned_at": "2024-01-14T08:15:00Z",
                "started_at": "2024-01-14T09:00:00Z"
            }
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_in_progress"
        assert result.state == EvaluationState.FULFILLING

    def test_completed_task_final_state(self, process):
        """Test that completed tasks reach final state."""
        task_data = {
            "title": "Implement user authentication",
            "description": "Add login/logout functionality to the application",
            "priority": "high",
            "due_date": "2024-02-15",
            "labels": ["backend", "security"],
            "assignee": {
                "user_id": "dev_001",
                "name": "John Developer",
                "email": "john.dev@company.com"
            },
            "status": "completed",
            "progress_notes": "Implemented OAuth2 integration with JWT tokens",
            "completion_percentage": 100,
            "meta": {
                "created_at": "2024-01-15T09:00:00Z",
                "assigned_at": "2024-01-15T09:30:00Z",
                "started_at": "2024-01-16T10:00:00Z",
                "completed_at": "2024-01-18T16:30:00Z"
            }
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_completed"
        assert result.state == EvaluationState.COMPLETED
        assert not result.can_advance

    def test_invalid_priority_scoping(self, process):
        """Test that invalid priority puts task in scoping state."""
        task_data = {
            "title": "Test task",
            "description": "This is a test task",
            "priority": "super_urgent",  # Invalid priority
            "meta": {"created_at": "2024-01-15T10:00:00Z"}
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_created"
        assert result.state == EvaluationState.SCOPING

    def test_missing_title_and_description_scoping(self, process):
        """Test that missing required fields puts task in scoping state."""
        task_data = {
            # Missing title and description
            "priority": "medium",
            "meta": {"created_at": "2024-01-15T10:00:00Z"}
        }
        element = Element(task_data)
        result = process.evaluate(element)

        assert result.current_stage == "task_created"
        assert result.state == EvaluationState.SCOPING
