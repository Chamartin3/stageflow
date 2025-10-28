"""
Process Registry Module

Handles process discovery, loading, and file operations for StageFlow processes.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stageflow.process import Process, ProcessDefinition
from stageflow.schema import LoadError, load_process

from .config import ManagerConfig, ProcessFileFormat


class ProcessRegistryError(Exception):
    """Exception raised for process registry operations."""

    pass


class ProcessRegistry:
    """
    Registry for managing multiple StageFlow processes.

    Provides file-based process discovery, loading, and saving functionality
    using the existing StageFlow loader infrastructure.
    """

    def __init__(self, config: ManagerConfig):
        """
        Initialize the process registry.

        Args:
            config: Manager configuration containing directory and format settings
        """
        self.config = config
        self._yaml = YAML(typ="safe", pure=True)
        self._yaml.preserve_quotes = True
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def list_processes(self) -> list[str]:
        """
        List all available process names in the registry.

        Returns:
            List of process names (without file extensions)

        Raises:
            ProcessRegistryError: If processes directory is not accessible
        """
        if not self.config.is_valid_processes_dir():
            raise ProcessRegistryError(
                f"Processes directory not accessible: {self.config.processes_dir}"
            )

        process_names = set()

        try:
            for file_path in self.config.processes_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in [
                    ".yaml",
                    ".yml",
                    ".json",
                ]:
                    process_names.add(file_path.stem)
        except OSError as e:
            raise ProcessRegistryError(f"Failed to list processes: {e}") from e

        return sorted(process_names)

    def process_exists(self, process_name: str) -> bool:
        """
        Check if a process exists in the registry.

        Args:
            process_name: Name of the process to check

        Returns:
            True if process exists, False otherwise
        """
        if not process_name or not process_name.strip():
            return False

        try:
            # Try to find the process with any supported extension
            for ext in ["yaml", "yml", "json"]:
                file_path = self.config.processes_dir / f"{process_name}.{ext}"
                if file_path.exists() and file_path.is_file():
                    return True
            return False
        except OSError:
            return False

    def get_process_file_path(self, process_name: str) -> Path | None:
        """
        Get the file path for an existing process.

        Args:
            process_name: Name of the process

        Returns:
            Path to the process file if it exists, None otherwise
        """
        if not self.process_exists(process_name):
            return None

        # Try to find existing file with any extension
        for ext in ["yaml", "yml", "json"]:
            file_path = self.config.processes_dir / f"{process_name}.{ext}"
            if file_path.exists():
                return file_path

        return None

    def load_process(self, process_name: str) -> Process:
        """
        Load a process from the registry.

        Args:
            process_name: Name of the process to load

        Returns:
            Process object

        Raises:
            ProcessRegistryError: If process doesn't exist or loading fails
        """
        file_path = self.get_process_file_path(process_name)
        if not file_path:
            available = ", ".join(self.list_processes()) or "none"
            raise ProcessRegistryError(
                f"Process '{process_name}' not found. Available processes: {available}"
            )

        try:
            return load_process(file_path)
        except LoadError as e:
            raise ProcessRegistryError(
                f"Failed to load process '{process_name}': {e}"
            ) from e

    def load_process_data(self, process_name: str) -> ProcessDefinition:
        """
        Load raw process data without creating a Process object.

        Args:
            process_name: Name of the process to load

        Returns:
            Raw process data dictionary

        Raises:
            ProcessRegistryError: If process doesn't exist or loading fails
        """
        file_path = self.get_process_file_path(process_name)
        if not file_path:
            available = ", ".join(self.list_processes()) or "none"
            raise ProcessRegistryError(
                f"Process '{process_name}' not found. Available processes: {available}"
            )

        try:
            # Load the process and extract its configuration
            process = load_process(file_path)
            # Ensure required stages exist
            if not process.initial_stage or not process.final_stage:
                raise ProcessRegistryError(
                    f"Process '{process_name}' missing required initial or final stage"
                )

            # For now, return a basic dict - this method may need to be updated
            # based on how ProcessDefinition is used
            return {
                "name": process.name,
                "description": process.description,
                "stages": {},  # This would need proper extraction
                "initial_stage": process.initial_stage._id,
                "final_stage": process.final_stage._id,
            }
        except LoadError as e:
            raise ProcessRegistryError(
                f"Failed to load process data '{process_name}': {e}"
            ) from e

    def save_process(
        self,
        process_name: str,
        process_data: Process | ProcessDefinition | dict,
        format_override: ProcessFileFormat | None = None,
        create_backup: bool | None = None,
    ) -> Path:
        """
        Save a process to the registry.

        Args:
            process_name: Name for the process file
            process_data: Process data (can be Process object, ProcessDefinition, or dict)
            format_override: Override default file format
            create_backup: Override backup setting from config

        Returns:
            Path to the saved file

        Raises:
            ProcessRegistryError: If saving fails
        """
        if not process_name or not process_name.strip():
            raise ProcessRegistryError("Process name cannot be empty")

        # Validate processes directory
        if not self.config.is_valid_processes_dir():
            raise ProcessRegistryError(
                f"Processes directory not accessible: {self.config.processes_dir}"
            )

        # Get target file path
        target_path = self.config.get_process_file_path(process_name, format_override)

        # Create backup if needed
        should_backup = (
            create_backup if create_backup is not None else self.config.backup_enabled
        )
        if should_backup and target_path.exists():
            self._create_backup(process_name)

        # Extract process data
        if isinstance(process_data, Process):
            # Extract from Process object
            data_dict = self._extract_process_data(process_data)
        elif isinstance(process_data, dict):
            # Use dict directly, ensure it has process wrapper
            if "process" in process_data:
                data_dict = process_data
            else:
                data_dict = {"process": process_data}
        else:
            # Assume it's ProcessDefinition (dict-like)
            data_dict = {"process": process_data}

        # Save the file
        try:
            self._write_process_file(target_path, data_dict)
            return target_path
        except Exception as e:
            raise ProcessRegistryError(
                f"Failed to save process '{process_name}': {e}"
            ) from e

    def delete_process(
        self, process_name: str, create_backup: bool | None = None
    ) -> bool:
        """
        Delete a process from the registry.

        Args:
            process_name: Name of the process to delete
            create_backup: Override backup setting from config

        Returns:
            True if process was deleted, False if it didn't exist

        Raises:
            ProcessRegistryError: If deletion fails
        """
        file_path = self.get_process_file_path(process_name)
        if not file_path:
            return False

        # Create backup if needed
        should_backup = (
            create_backup if create_backup is not None else self.config.backup_enabled
        )
        if should_backup:
            self._create_backup(process_name)

        try:
            file_path.unlink()
            return True
        except OSError as e:
            raise ProcessRegistryError(
                f"Failed to delete process '{process_name}': {e}"
            ) from e

    def get_process_info(self, process_name: str) -> dict[str, Any]:
        """
        Get metadata information about a process.

        Args:
            process_name: Name of the process

        Returns:
            Dictionary with process metadata

        Raises:
            ProcessRegistryError: If process doesn't exist
        """
        file_path = self.get_process_file_path(process_name)
        if not file_path:
            raise ProcessRegistryError(f"Process '{process_name}' not found")

        try:
            stat = file_path.stat()
            return {
                "name": process_name,
                "file_path": str(file_path),
                "format": "yaml"
                if file_path.suffix.lower() in [".yaml", ".yml"]
                else "json",
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except OSError as e:
            raise ProcessRegistryError(
                f"Failed to get process info for '{process_name}': {e}"
            ) from e

    def list_process_info(self) -> list[dict[str, Any]]:
        """
        Get metadata information for all processes in the registry.

        Returns:
            List of process metadata dictionaries

        Raises:
            ProcessRegistryError: If registry cannot be accessed
        """
        process_names = self.list_processes()
        info_list = []

        for name in process_names:
            try:
                info_list.append(self.get_process_info(name))
            except ProcessRegistryError:
                # Skip processes that can't be accessed
                continue

        return info_list

    def _create_backup(self, process_name: str) -> None:
        """Create a backup of an existing process."""
        if not self.config.backup_enabled or not self.config.backup_dir:
            return

        source_path = self.get_process_file_path(process_name)
        if not source_path or not source_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = self.config.get_backup_path(process_name, timestamp)

        try:
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(source_path, backup_path)

            # Clean up old backups
            self._cleanup_old_backups(process_name)

        except OSError as e:
            # Don't fail the main operation if backup fails
            print(f"Warning: Failed to create backup for '{process_name}': {e}")

    def _cleanup_old_backups(self, process_name: str) -> None:
        """Remove old backup files beyond the configured limit."""
        if not self.config.backup_dir or self.config.max_backups <= 0:
            return

        try:
            # Find all backup files for this process
            pattern = f"{process_name}_*.yaml"
            backup_files = list(self.config.backup_dir.glob(pattern))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Remove excess files
            for old_backup in backup_files[self.config.max_backups :]:
                old_backup.unlink()

        except OSError:
            # Ignore cleanup errors
            pass

    def _extract_process_data(self, process: Process) -> dict[str, Any]:
        """Extract data from a Process object for serialization."""
        try:
            # Create a process definition from the Process object's attributes
            # by reconstructing the original configuration structure

            stages_def = {}
            for stage in process.stages:
                stage_data = {
                    "name": stage.name,
                    "description": stage.description or "",
                    "gates": [],
                    "expected_actions": [
                        {
                            "description": action.description,
                            "related_properties": action.related_properties,
                        }
                        for action in stage.stage_actions
                    ]
                    if stage.stage_actions
                    else [],
                    "is_final": stage.is_final,
                }

                # Convert gates
                for gate in stage.gates:
                    gate_data = {
                        "name": gate.name,
                        "description": gate.description or "",
                        "target_stage": gate.target_stage,
                        "locks": [],
                    }

                    # Convert locks
                    for lock in gate.locks:
                        lock_data = {
                            "type": lock.lock_type.value,
                            "property_path": lock.property_path,
                        }
                        if (
                            hasattr(lock, "expected_value")
                            and lock.expected_value is not None
                        ):
                            lock_data["expected_value"] = lock.expected_value
                        gate_data["locks"].append(lock_data)

                    stage_data["gates"].append(gate_data)

                stages_def[stage._id] = stage_data

            process_def = {
                "name": process.name,
                "description": process.description or "",
                "stages": stages_def,
                "initial_stage": process.initial_stage._id,
                "final_stage": process.final_stage._id,
            }

            return {"process": process_def}

        except Exception as e:
            raise ProcessRegistryError(f"Failed to extract process data: {e}") from e

    def _write_process_file(self, file_path: Path, data: dict[str, Any]) -> None:
        """Write process data to file in the appropriate format."""
        file_format = (
            ProcessFileFormat.YAML
            if file_path.suffix.lower() in [".yaml", ".yml"]
            else ProcessFileFormat.JSON
        )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if file_format == ProcessFileFormat.YAML:
                    self._yaml.dump(data, f)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ProcessRegistryError(f"Failed to write file {file_path}: {e}") from e

    def validate_process_name(self, process_name: str) -> bool:
        """
        Validate a process name for file system compatibility.

        Args:
            process_name: Name to validate

        Returns:
            True if name is valid, False otherwise
        """
        if not process_name or not process_name.strip():
            return False

        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in process_name for char in invalid_chars):
            return False

        # Check for reserved names (Windows)
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if process_name.upper() in reserved_names:
            return False

        # Check length (common file system limit)
        if len(process_name) > 255:
            return False

        return True

    def __str__(self) -> str:
        """String representation of the registry."""
        process_count = (
            len(self.list_processes()) if self.config.is_valid_processes_dir() else 0
        )
        return f"ProcessRegistry(dir='{self.config.processes_dir}', processes={process_count})"

    def __repr__(self) -> str:
        """Detailed string representation of the registry."""
        return f"ProcessRegistry(config={self.config!r})"
