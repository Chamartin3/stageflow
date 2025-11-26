"""Tests for ProcessEditor functionality."""

import pytest

from stageflow.manager import ProcessEditor, ProcessEditorError, ValidationFailedError
from stageflow.process import Process


@pytest.fixture
def simple_process():
    """Create a simple two-stage process for testing."""
    return Process(
        {
            "name": "test_process",
            "description": "Test process for editor",
            "stages": {
                "start": {
                    "name": "Start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "test_field"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": {"test_field": {"type": "str"}},
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "description": "Final stage",
                    "gates": [],
                    "expected_actions": [],
                    "fields": {},
                    "is_final": True,
                },
            },
            "initial_stage": "start",
            "final_stage": "end",
        }
    )


@pytest.fixture
def three_stage_process():
    """Create a three-stage process for testing."""
    return Process(
        {
            "name": "test_process",
            "description": "Test process for editor",
            "stages": {
                "start": {
                    "name": "Start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "to_middle",
                            "target_stage": "middle",
                            "locks": [{"exists": "field1"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": {"field1": {"type": "str"}},
                    "is_final": False,
                },
                "middle": {
                    "name": "Middle",
                    "description": "Middle stage",
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "field2"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": {"field2": {"type": "str"}},
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "description": "Final stage",
                    "gates": [],
                    "expected_actions": [],
                    "fields": {},
                    "is_final": True,
                },
            },
            "initial_stage": "start",
            "final_stage": "end",
        }
    )


class TestProcessEditorInitialization:
    """Test ProcessEditor initialization."""

    def test_editor_initialization_with_valid_process(self, simple_process):
        """Test initializing editor with a valid process."""
        editor = ProcessEditor(simple_process)

        assert editor.process.name == "test_process"
        assert not editor.is_dirty
        assert len(editor.consistency_issues) == 0

    def test_editor_initialization_with_inconsistent_process(self):
        """Test that editor allows initialization with inconsistent process for fixing."""
        # Create a process with invalid transitions
        invalid_config = {
            "name": "invalid_process",
            "description": "Invalid process",
            "stages": {
                "start": {
                    "name": "Start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "to_nonexistent",
                            "target_stage": "nonexistent",
                            "locks": [{"exists": "field"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": {},
                    "is_final": False,
                },
                "end": {
                    "name": "End",
                    "description": "Final stage",
                    "gates": [],
                    "expected_actions": [],
                    "fields": {},
                    "is_final": True,
                },
            },
            "initial_stage": "start",
            "final_stage": "end",
        }

        invalid_process = Process(invalid_config)

        # Act & Assert - Editor should allow editing inconsistent processes
        # to enable fixing them
        editor = ProcessEditor(invalid_process)

        # Verify consistency issues are detected
        issues = editor.consistency_issues
        assert len(issues) > 0
        # The specific issue detected is that Start cannot reach End stage
        assert any("cannot reach final stage" in issue.description for issue in issues)


class TestProcessEditorAddStage:
    """Test adding stages to a process."""

    def test_add_stage_creates_branch(self, simple_process):
        """Test adding a stage that creates an alternative path."""
        editor = ProcessEditor(simple_process)

        # Add alternative stage that connects to end
        alt_config = {
            "name": "Alternative",
            "description": "Alternative path",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "alt_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"alt_field": {"type": "str"}},
            "is_final": False,
        }

        editor.add_stage("alternative", alt_config)

        # Update start to have two paths
        start_config = {
            "name": "Start",
            "description": "Starting stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "test_field"}],
                },
                {
                    "name": "to_alternative",
                    "target_stage": "alternative",
                    "locks": [{"exists": "alt_trigger"}],
                },
            ],
            "expected_actions": [],
            "fields": {
                "test_field": {"type": "str"},
                "alt_trigger": {"type": "str"},
            },
            "is_final": False,
        }

        editor.update_stage("start", start_config)

        assert editor.is_dirty
        assert editor.process.get_stage("alternative") is not None
        assert len(editor.consistency_issues) == 0

    def test_add_duplicate_stage_raises_error(self, simple_process):
        """Test that adding a duplicate stage raises an error."""
        editor = ProcessEditor(simple_process)

        duplicate_config = {
            "name": "Start",
            "description": "Duplicate stage",
            "gates": [],
            "expected_actions": [],
            "fields": {},
            "is_final": False,
        }

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.add_stage("start", duplicate_config)

        assert "already exists" in str(exc_info.value)


class TestProcessEditorRemoveStage:
    """Test removing stages from a process."""

    def test_remove_stage_with_alternative_path(self, three_stage_process):
        """Test removing a stage when there's an alternative path."""
        editor = ProcessEditor(three_stage_process)

        # First add alternative path from start to end
        alt_config = {
            "name": "Alternative",
            "description": "Alternative path",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "alt_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"alt_field": {"type": "str"}},
            "is_final": False,
        }
        editor.add_stage("alternative", alt_config)

        # Update start to have path to alternative
        start_config = {
            "name": "Start",
            "description": "Starting stage",
            "gates": [
                {
                    "name": "to_middle",
                    "target_stage": "middle",
                    "locks": [{"exists": "field1"}],
                },
                {
                    "name": "to_alternative",
                    "target_stage": "alternative",
                    "locks": [{"exists": "alt_trigger"}],
                },
            ],
            "expected_actions": [],
            "fields": {
                "field1": {"type": "str"},
                "alt_trigger": {"type": "str"},
            },
            "is_final": False,
        }
        editor.update_stage("start", start_config)

        # Now remove middle stage
        editor.remove_stage("middle")

        assert editor.is_dirty
        assert editor.process.get_stage("middle") is None
        assert len(editor.consistency_issues) == 0

    def test_remove_initial_stage_raises_error(self, simple_process):
        """Test that removing initial stage raises an error."""
        editor = ProcessEditor(simple_process)

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.remove_stage("start")

        assert "Cannot remove initial stage" in str(exc_info.value)

    def test_remove_final_stage_raises_error(self, simple_process):
        """Test that removing final stage raises an error."""
        editor = ProcessEditor(simple_process)

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.remove_stage("end")

        assert "Cannot remove final stage" in str(exc_info.value)

    def test_remove_nonexistent_stage_raises_error(self, simple_process):
        """Test that removing non-existent stage raises an error."""
        editor = ProcessEditor(simple_process)

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.remove_stage("nonexistent")

        assert "not found" in str(exc_info.value)


class TestProcessEditorUpdateStage:
    """Test updating stages in a process."""

    def test_update_stage_properties(self, simple_process):
        """Test updating a stage's properties."""
        editor = ProcessEditor(simple_process)

        updated_config = {
            "name": "Updated Start",
            "description": "Updated starting stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "updated_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"updated_field": {"type": "str"}},
            "is_final": False,
        }

        editor.update_stage("start", updated_config)

        assert editor.is_dirty
        updated_stage = editor.process.get_stage("start")
        assert updated_stage.name == "Updated Start"
        assert len(editor.consistency_issues) == 0

    def test_update_nonexistent_stage_raises_error(self, simple_process):
        """Test that updating non-existent stage raises an error."""
        editor = ProcessEditor(simple_process)

        config = {
            "name": "Nonexistent",
            "description": "Nonexistent stage",
            "gates": [],
            "expected_actions": [],
            "fields": {},
            "is_final": False,
        }

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.update_stage("nonexistent", config)

        assert "not found" in str(exc_info.value)


class TestProcessEditorRollback:
    """Test rollback functionality."""

    def test_rollback_restores_original_state(self, simple_process):
        """Test that rollback restores the original process state."""
        editor = ProcessEditor(simple_process)
        original_stage_count = len(editor.process.stages)

        # Make changes - add alternative branch
        alt_config = {
            "name": "Temporary",
            "description": "Temporary stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "temp_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"temp_field": {"type": "str"}},
            "is_final": False,
        }

        editor.add_stage("temporary", alt_config)

        # Update start to add branch to temporary
        start_config = {
            "name": "Start",
            "description": "Starting stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "test_field"}],
                },
                {
                    "name": "to_temporary",
                    "target_stage": "temporary",
                    "locks": [{"exists": "temp_trigger"}],
                },
            ],
            "expected_actions": [],
            "fields": {
                "test_field": {"type": "str"},
                "temp_trigger": {"type": "str"},
            },
            "is_final": False,
        }
        editor.update_stage("start", start_config)

        assert editor.is_dirty
        assert editor.process.get_stage("temporary") is not None

        # Rollback
        editor.rollback()

        assert not editor.is_dirty
        assert editor.process.get_stage("temporary") is None
        assert len(editor.process.stages) == original_stage_count


class TestProcessEditorSync:
    """Test sync functionality."""

    def test_sync_creates_new_backup(self, simple_process):
        """Test that sync creates a new backup point."""
        editor = ProcessEditor(simple_process)

        # Make changes - add alternative branch
        alt_config = {
            "name": "Synced",
            "description": "Synced stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "synced_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"synced_field": {"type": "str"}},
            "is_final": False,
        }

        editor.add_stage("synced", alt_config)

        # Update start to add branch
        start_config = {
            "name": "Start",
            "description": "Starting stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "test_field"}],
                },
                {
                    "name": "to_synced",
                    "target_stage": "synced",
                    "locks": [{"exists": "sync_trigger"}],
                },
            ],
            "expected_actions": [],
            "fields": {
                "test_field": {"type": "str"},
                "sync_trigger": {"type": "str"},
            },
            "is_final": False,
        }
        editor.update_stage("start", start_config)

        assert editor.is_dirty

        # Sync changes
        editor.sync()
        assert not editor.is_dirty
        assert editor.process.get_stage("synced") is not None

        # Make another change and rollback - should keep synced stage
        temp_config = {
            "name": "Temporary",
            "description": "Temporary stage",
            "gates": [
                {
                    "name": "to_end",
                    "target_stage": "end",
                    "locks": [{"exists": "temp_field"}],
                }
            ],
            "expected_actions": [],
            "fields": {"temp_field": {"type": "str"}},
            "is_final": False,
        }

        editor.add_stage("temporary", temp_config)
        editor.rollback()

        assert editor.process.get_stage("synced") is not None
        assert editor.process.get_stage("temporary") is None


class TestProcessEditorValidation:
    """Test validation functionality."""

    def test_validation_failure_triggers_rollback(self, simple_process):
        """Test that validation failure triggers automatic rollback."""
        editor = ProcessEditor(simple_process)

        # Try to add stage with invalid transition
        invalid_config = {
            "name": "Invalid",
            "description": "Invalid stage",
            "gates": [
                {
                    "name": "invalid_gate",
                    "target_stage": "nonexistent",
                    "locks": [{"exists": "field"}],
                }
            ],
            "expected_actions": [],
            "fields": {},
            "is_final": False,
        }

        with pytest.raises(ValidationFailedError) as exc_info:
            editor.add_stage("invalid", invalid_config)

        assert not editor.is_dirty
        assert editor.process.get_stage("invalid") is None
        assert len(exc_info.value.issues) > 0

    def test_validate_method_returns_status(self, simple_process):
        """Test that validate method returns validation status."""
        editor = ProcessEditor(simple_process)

        is_valid, issues = editor.validate()
        assert is_valid
        assert len(issues) == 0


class TestProcessEditorContextManager:
    """Test context manager functionality."""

    def test_context_manager_rollback_on_exception(self, simple_process):
        """Test that context manager rolls back on exceptions."""
        original_stage_count = len(simple_process.stages)

        editor_after_exception = None
        with pytest.raises(ValueError):
            with ProcessEditor(simple_process) as editor:
                # Make changes - add alternative branch
                alt_config = {
                    "name": "Context",
                    "description": "Context stage",
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "context_field"}],
                        }
                    ],
                    "expected_actions": [],
                    "fields": {"context_field": {"type": "str"}},
                    "is_final": False,
                }

                editor.add_stage("context", alt_config)

                # Update start to add branch
                start_config = {
                    "name": "Start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "test_field"}],
                        },
                        {
                            "name": "to_context",
                            "target_stage": "context",
                            "locks": [{"exists": "context_trigger"}],
                        },
                    ],
                    "expected_actions": [],
                    "fields": {
                        "test_field": {"type": "str"},
                        "context_trigger": {"type": "str"},
                    },
                    "is_final": False,
                }
                editor.update_stage("start", start_config)

                # Store reference to check after exception
                editor_after_exception = editor

                # Simulate error
                raise ValueError("Simulated error")

        # Check rollback occurred on the editor's process
        assert not editor_after_exception.is_dirty
        assert editor_after_exception.process.get_stage("context") is None
        assert len(editor_after_exception.process.stages) == original_stage_count


class TestProcessEditorAddTransition:
    """Test adding transitions."""

    def test_add_transition_between_existing_stages(self, simple_process):
        """Test adding a transition between existing stages."""
        editor = ProcessEditor(simple_process)

        editor.add_transition("start", "end")

        assert editor.is_dirty
        assert len(editor.consistency_issues) == 0

    def test_add_transition_with_nonexistent_source_raises_error(self, simple_process):
        """Test that adding transition with non-existent source raises error."""
        editor = ProcessEditor(simple_process)

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.add_transition("nonexistent", "end")

        assert "Source stage" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_add_transition_with_nonexistent_target_raises_error(self, simple_process):
        """Test that adding transition with non-existent target raises error."""
        editor = ProcessEditor(simple_process)

        with pytest.raises(ProcessEditorError) as exc_info:
            editor.add_transition("start", "nonexistent")

        assert "Target stage" in str(exc_info.value)
        assert "not found" in str(exc_info.value)


class TestProcessEditorUtilityMethods:
    """Test utility methods."""

    def test_get_process_definition(self, simple_process):
        """Test getting process definition as dictionary."""
        editor = ProcessEditor(simple_process)

        definition = editor.get_process_definition()

        assert isinstance(definition, dict)
        assert definition["name"] == "test_process"
        assert "stages" in definition
        assert "initial_stage" in definition
        assert "final_stage" in definition

    def test_consistency_issues_property(self, simple_process):
        """Test consistency issues property."""
        editor = ProcessEditor(simple_process)

        issues = editor.consistency_issues
        assert isinstance(issues, list)
        assert len(issues) == 0
