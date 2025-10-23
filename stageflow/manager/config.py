# stageflow/manager/config.py
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypedDict

from stageflow.manager.constants import (
    BACKUP_SUBDIR_NAME,
    DEFAULT_AUTO_FIX_PERMISSIONS,
    DEFAULT_BACKUP_ENABLED,
    DEFAULT_CREATE_DIR,
    # Directory constants
    DEFAULT_DIR_PERMISSIONS,
    DEFAULT_FORMAT,
    DEFAULT_MAX_BACKUPS,
    # Default values
    DEFAULT_PROCESSES_DIR,
    DEFAULT_STRICT_VALIDATION,
    # Environment variable names
    ENV_VAR_PREFIX,
    FILE_EXT_JSON,
    FILE_EXT_YAML,
    # File format constants
    SUPPORTED_EXTENSIONS,
    get_auto_fix_permissions,
    get_backup_dir,
    get_backup_enabled,
    get_create_dir,
    get_default_format,
    get_max_backups,
    # Helper functions
    get_processes_dir,
    get_strict_validation,
)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass

class ProcessFileFormat(StrEnum):
    """Supported process file formats"""
    YAML = "yaml"
    JSON = "json"
    AUTO = "auto"  # Detect from file extension

class ManagerConfigDict(TypedDict, total=False):
    """TypedDict for manager configuration dictionary"""
    processes_dir: str
    default_format: str
    create_dir_if_missing: bool
    backup_enabled: bool
    backup_dir: str | None
    max_backups: int
    strict_validation: bool
    auto_fix_permissions: bool

@dataclass(frozen=True)
class ManagerConfig:
    """Configuration for StageFlow process manager"""

    # Core settings
    processes_dir: Path
    default_format: ProcessFileFormat = ProcessFileFormat.YAML
    create_dir_if_missing: bool = True

    # File handling
    backup_enabled: bool = False
    backup_dir: Path | None = None
    max_backups: int = 5

    # Validation settings
    strict_validation: bool = True
    auto_fix_permissions: bool = True

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
        self._setup_directories()

    @classmethod
    def from_env(cls,
                 env_prefix: str = ENV_VAR_PREFIX,
                 fallback_dir: str = DEFAULT_PROCESSES_DIR) -> 'ManagerConfig':
        """Create configuration from environment variables using constants module"""

        # Get processes directory
        processes_dir_str = get_processes_dir() if env_prefix == ENV_VAR_PREFIX else fallback_dir
        processes_dir = Path(processes_dir_str).expanduser().resolve()

        # Get default format
        format_str = get_default_format()
        try:
            default_format = ProcessFileFormat(format_str)
        except ValueError:
            default_format = ProcessFileFormat.YAML

        # Get boolean settings using helper functions
        create_dir = get_create_dir()
        backup_enabled = get_backup_enabled()
        strict_validation = get_strict_validation()
        auto_fix_permissions = get_auto_fix_permissions()

        # Get backup settings
        backup_dir = None
        backup_dir_str = get_backup_dir()
        if backup_dir_str:
            backup_dir = Path(backup_dir_str).expanduser().resolve()

        max_backups = get_max_backups()

        return cls(
            processes_dir=processes_dir,
            default_format=default_format,
            create_dir_if_missing=create_dir,
            backup_enabled=backup_enabled,
            backup_dir=backup_dir,
            max_backups=max_backups,
            strict_validation=strict_validation,
            auto_fix_permissions=auto_fix_permissions
        )

    @classmethod
    def from_dict(cls, config_dict: ManagerConfigDict) -> 'ManagerConfig':
        """Create configuration from typed dictionary using constants module"""
        # Get processes directory with type safety
        processes_dir_str = config_dict.get('processes_dir', DEFAULT_PROCESSES_DIR)
        processes_dir = Path(processes_dir_str).expanduser().resolve()

        # Handle format with validation
        format_str = config_dict.get('default_format', DEFAULT_FORMAT)
        try:
            default_format = ProcessFileFormat(format_str.lower())
        except ValueError as e:
            raise ConfigValidationError(f"Invalid default_format: {format_str}") from e

        # Handle backup_dir with type safety
        backup_dir = None
        backup_dir_val = config_dict.get('backup_dir')
        if backup_dir_val:
            backup_dir = Path(backup_dir_val).expanduser().resolve()

        # Validate max_backups
        max_backups = config_dict.get('max_backups', DEFAULT_MAX_BACKUPS)
        if max_backups < 0:
            raise ConfigValidationError("max_backups must be non-negative")

        return cls(
            processes_dir=processes_dir,
            default_format=default_format,
            create_dir_if_missing=config_dict.get('create_dir_if_missing', DEFAULT_CREATE_DIR),
            backup_enabled=config_dict.get('backup_enabled', DEFAULT_BACKUP_ENABLED),
            backup_dir=backup_dir,
            max_backups=max_backups,
            strict_validation=config_dict.get('strict_validation', DEFAULT_STRICT_VALIDATION),
            auto_fix_permissions=config_dict.get('auto_fix_permissions', DEFAULT_AUTO_FIX_PERMISSIONS)
        )

    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Validate processes directory
        if not self.processes_dir:
            raise ConfigValidationError("processes_dir cannot be empty")

        # Validate backup settings
        if self.backup_enabled and not self.backup_dir:
            # Default backup dir to processes_dir/.backups
            object.__setattr__(self, 'backup_dir', self.processes_dir / BACKUP_SUBDIR_NAME)

        if self.max_backups < 0:
            raise ConfigValidationError("max_backups must be non-negative")

        # Validate format
        if not isinstance(self.default_format, ProcessFileFormat):
            raise ConfigValidationError(f"Invalid default_format: {self.default_format}")

    def _setup_directories(self) -> None:
        """Create directories if they don't exist"""
        if self.create_dir_if_missing:
            try:
                self.processes_dir.mkdir(parents=True, exist_ok=True)

                # Fix permissions if needed
                if self.auto_fix_permissions and not os.access(self.processes_dir, os.R_OK | os.W_OK):
                    try:
                        os.chmod(self.processes_dir, DEFAULT_DIR_PERMISSIONS)
                    except PermissionError:
                        pass  # Ignore permission errors

                # Create backup directory if backup is enabled
                if self.backup_enabled and self.backup_dir:
                    self.backup_dir.mkdir(parents=True, exist_ok=True)

            except OSError as e:
                raise ConfigValidationError(f"Failed to create processes directory: {e}") from e

    def get_process_file_path(self, process_name: str, format_override: ProcessFileFormat | None = None) -> Path:
        """Get full path for a process file"""
        file_format = format_override or self.default_format

        if file_format == ProcessFileFormat.AUTO:
            # Try to find existing file with any extension
            for ext in SUPPORTED_EXTENSIONS:
                file_path = self.processes_dir / f"{process_name}.{ext}"
                if file_path.exists():
                    return file_path
            # If not found, default to YAML
            file_format = ProcessFileFormat.YAML

        extension = FILE_EXT_YAML if file_format == ProcessFileFormat.YAML else FILE_EXT_JSON
        return self.processes_dir / f"{process_name}.{extension}"

    def get_backup_path(self, process_name: str, timestamp: str) -> Path:
        """Get backup file path for a process"""
        if not self.backup_enabled or not self.backup_dir:
            raise ConfigValidationError("Backup not enabled")

        return self.backup_dir / f"{process_name}_{timestamp}.{FILE_EXT_YAML}"

    def is_valid_processes_dir(self) -> bool:
        """Check if processes directory is valid and accessible"""
        try:
            return (self.processes_dir.exists() and
                   self.processes_dir.is_dir() and
                   os.access(self.processes_dir, os.R_OK | os.W_OK))
        except OSError:
            return False

    def to_dict(self) -> ManagerConfigDict:
        """Convert configuration to typed dictionary"""
        return ManagerConfigDict(
            processes_dir=str(self.processes_dir),
            default_format=self.default_format.value,
            create_dir_if_missing=self.create_dir_if_missing,
            backup_enabled=self.backup_enabled,
            backup_dir=str(self.backup_dir) if self.backup_dir else None,
            max_backups=self.max_backups,
            strict_validation=self.strict_validation,
            auto_fix_permissions=self.auto_fix_permissions
        )

    def __str__(self) -> str:
        return f"ManagerConfig(processes_dir='{self.processes_dir}', format={self.default_format.value})"

    def __repr__(self) -> str:
        return (f"ManagerConfig(processes_dir={self.processes_dir!r}, "
                f"default_format={self.default_format!r}, "
                f"backup_enabled={self.backup_enabled})")


# Environment variable reference:
# STAGEFLOW_PROCESSES_DIR - Directory containing process files (default: ./processes)
# STAGEFLOW_DEFAULT_FORMAT - Default file format: yaml|json|auto (default: yaml)
# STAGEFLOW_CREATE_DIR - Create directory if missing: true|false (default: true)
# STAGEFLOW_BACKUP_ENABLED - Enable file backups: true|false (default: false)
# STAGEFLOW_BACKUP_DIR - Backup directory path (default: processes_dir/.backups)
# STAGEFLOW_MAX_BACKUPS - Maximum backup files to keep (default: 5)
# STAGEFLOW_STRICT_VALIDATION - Enable strict validation: true|false (default: true)
# STAGEFLOW_AUTO_FIX_PERMISSIONS - Auto-fix directory permissions: true|false (default: true)

