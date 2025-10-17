"""ProcessEditor for safe in-memory process mutations with backup/rollback mechanism."""

import copy
from typing import Any

from ..process import ConsistencyIssue, Process, ProcessDefinition
from ..stage import StageDefinition


class ProcessEditorError(Exception):
    """Base exception for ProcessEditor operations."""
    pass


class ValidationFailedError(ProcessEditorError):
    """Raised when a process modification fails validation."""

    def __init__(self, message: str, issues: list[ConsistencyIssue]):
        super().__init__(message)
        self.issues = issues


class ProcessEditor:
    """
    Safe in-memory process editor with backup/rollback mechanism.

    Provides safe editing capabilities for Process objects by maintaining
    backups and automatically rolling back changes that would result in
    invalid process configurations.

    Key features:
    - Backup/rollback mechanism for safe editing
    - Dirty flag tracking for change detection
    - Automatic rollback on validation failures
    - Integration with existing Process consistency validation
    - In-memory only operations until explicit sync
    """

    def __init__(self, process: Process):
        """
        Initialize ProcessEditor with a Process object.

        Args:
            process: The Process instance to edit

        Raises:
            ProcessEditorError: If the initial process has consistency issues
        """
        # Allow editing processes with consistency issues (for fixing them)
        # The editor is designed to enable fixing inconsistent processes
        # Validation occurs during save operations instead

        self._process = process
        self._backup: ProcessDefinition | None = None
        self._dirty = False
        self._create_backup()

    def _create_backup(self) -> None:
        """Create a deep copy backup of the current process configuration."""
        self._backup = copy.deepcopy(self._process.to_dict())
        self._dirty = False

    def _restore_backup(self) -> None:
        """Restore process from backup configuration."""
        if self._backup is None:
            raise ProcessEditorError("No backup available for restore operation")

        # Reconstruct process from backup
        self._process = Process(self._backup)
        self._dirty = False

    def _validate_and_commit(self) -> None:
        """
        Validate current process state and commit changes.

        Raises:
            ValidationFailedError: If validation fails, automatic rollback occurs
        """
        # Update consistency checker
        self._process.checker = self._process._get_consistency_checker()

        if not self._process.checker.valid:
            issues = self._process.consistensy_issues
            # Automatic rollback on validation failure
            self._restore_backup()
            raise ValidationFailedError(
                f"Process validation failed, changes rolled back. Issues: "
                f"{[issue.description for issue in issues]}",
                issues
            )

        # If validation passes, update dirty flag
        self._dirty = True

    @property
    def process(self) -> Process:
        """Get the current process being edited."""
        return self._process

    @property
    def is_dirty(self) -> bool:
        """Check if the process has unsaved changes."""
        return self._dirty

    def mark_clean(self) -> None:
        """Mark the editor as clean (no unsaved changes)."""
        self._dirty = False

    @property
    def consistency_issues(self) -> list[ConsistencyIssue]:
        """Get current consistency issues in the process."""
        return self._process.consistensy_issues

    def add_stage(self, stage_id: str, config: StageDefinition) -> None:
        """
        Add a new stage to the process with validation.

        Args:
            stage_id: Unique identifier for the new stage
            config: Stage configuration dictionary

        Raises:
            ProcessEditorError: If stage_id already exists
            ValidationFailedError: If adding stage creates consistency issues
        """
        if self._process.get_stage(stage_id) is not None:
            raise ProcessEditorError(f"Stage '{stage_id}' already exists in process")

        try:
            self._process.add_stage(stage_id, config)
            self._validate_and_commit()
        except Exception as e:
            if isinstance(e, ValidationFailedError):
                raise
            # Rollback on any other error
            self._restore_backup()
            raise ProcessEditorError(f"Failed to add stage '{stage_id}': {str(e)}") from e

    def remove_stage(self, stage_id: str) -> None:
        """
        Remove a stage from the process with validation.

        Args:
            stage_id: Identifier of the stage to remove

        Raises:
            ProcessEditorError: If stage doesn't exist or is initial/final stage
            ValidationFailedError: If removing stage creates consistency issues
        """
        stage = self._process.get_stage(stage_id)
        if stage is None:
            raise ProcessEditorError(f"Stage '{stage_id}' not found in process")

        if stage_id == self._process.initial_stage._id:
            raise ProcessEditorError("Cannot remove initial stage from process")

        if stage_id == self._process.final_stage._id:
            raise ProcessEditorError("Cannot remove final stage from process")

        try:
            self._process.remove_stage(stage_id)
            self._validate_and_commit()
        except Exception as e:
            if isinstance(e, ValidationFailedError):
                raise
            # Rollback on any other error
            self._restore_backup()
            raise ProcessEditorError(f"Failed to remove stage '{stage_id}': {str(e)}") from e

    def update_stage(self, stage_id: str, config: StageDefinition) -> None:
        """
        Update an existing stage configuration.

        Args:
            stage_id: Identifier of the stage to update
            config: New stage configuration

        Raises:
            ProcessEditorError: If stage doesn't exist
            ValidationFailedError: If update creates consistency issues
        """
        if self._process.get_stage(stage_id) is None:
            raise ProcessEditorError(f"Stage '{stage_id}' not found in process")

        try:
            # Remove and re-add with new configuration
            # First check if it's initial or final stage
            is_initial = stage_id == self._process.initial_stage._id
            is_final = stage_id == self._process.final_stage._id

            if is_initial or is_final:
                # For initial/final stages, we need to be more careful
                # Store the old stage data before removal
                old_stage = self._process.get_stage(stage_id)
                if old_stage is None:
                    raise ProcessEditorError(f"Stage '{stage_id}' not found")

                # Update the stage in place by reconstructing the entire process
                current_config = self._process.to_dict()
                current_config["stages"][stage_id] = config

                # Reconstruct process with updated configuration
                self._process = Process(current_config)
                self._validate_and_commit()
            else:
                # For non-initial/final stages, use remove and add
                self._process.remove_stage(stage_id)
                self._process.add_stage(stage_id, config)
                self._validate_and_commit()

        except Exception as e:
            if isinstance(e, ValidationFailedError):
                raise
            # Rollback on any other error
            self._restore_backup()
            raise ProcessEditorError(f"Failed to update stage '{stage_id}': {str(e)}") from e

    def add_transition(self, from_stage: str, to_stage: str) -> None:
        """
        Add a transition between two stages.

        Args:
            from_stage: Source stage identifier
            to_stage: Target stage identifier

        Raises:
            ProcessEditorError: If either stage doesn't exist
            ValidationFailedError: If transition creates consistency issues
        """
        if self._process.get_stage(from_stage) is None:
            raise ProcessEditorError(f"Source stage '{from_stage}' not found in process")

        if self._process.get_stage(to_stage) is None:
            raise ProcessEditorError(f"Target stage '{to_stage}' not found in process")

        try:
            self._process.add_transition(from_stage, to_stage)
            self._validate_and_commit()
        except Exception as e:
            if isinstance(e, ValidationFailedError):
                raise
            # Rollback on any other error
            self._restore_backup()
            raise ProcessEditorError(f"Failed to add transition '{from_stage}' -> '{to_stage}': {str(e)}") from e

    def rollback(self) -> None:
        """
        Manually rollback all changes to the last backup.

        This restores the process to its state when the editor was created
        or when sync() was last called.
        """
        self._restore_backup()

    def sync(self) -> None:
        """
        Synchronize changes by creating a new backup.

        This makes the current state the new baseline and clears the dirty flag.
        Call this after you're satisfied with the current changes and want to
        make them the new "clean" state.

        Raises:
            ValidationFailedError: If current state has consistency issues
        """
        if not self._process.checker.valid:
            issues = self._process.consistensy_issues
            raise ValidationFailedError(
                f"Cannot sync process with consistency issues: "
                f"{[issue.description for issue in issues]}",
                issues
            )

        self._create_backup()

    def validate(self) -> tuple[bool, list[ConsistencyIssue]]:
        """
        Validate current process state without making changes.

        Returns:
            Tuple of (is_valid, list of consistency issues)
        """
        # Update consistency checker to get latest state
        self._process.checker = self._process._get_consistency_checker()
        return self._process.checker.valid, self._process.consistensy_issues

    def get_process_definition(self) -> ProcessDefinition:
        """
        Get the current process configuration as a dictionary.

        Returns:
            ProcessDefinition dictionary representing current state
        """
        return self._process.to_dict()

    def __enter__(self) -> "ProcessEditor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - rollback on exceptions."""
        if exc_type is not None:
            # Rollback on any exception
            self.rollback()
