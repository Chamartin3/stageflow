"""Constants and default values for StageFlow manager configuration.

This module centralizes all configuration constants and environment variable
settings used by the StageFlow process manager.
"""

import os
from typing import Final

# =============================================================================
# Environment Variable Names
# =============================================================================

ENV_VAR_PREFIX: Final[str] = "STAGEFLOW_"

# Core settings
ENV_PROCESSES_DIR: Final[str] = f"{ENV_VAR_PREFIX}PROCESSES_DIR"
ENV_DEFAULT_FORMAT: Final[str] = f"{ENV_VAR_PREFIX}DEFAULT_FORMAT"
ENV_CREATE_DIR: Final[str] = f"{ENV_VAR_PREFIX}CREATE_DIR"

# Backup settings
ENV_BACKUP_ENABLED: Final[str] = f"{ENV_VAR_PREFIX}BACKUP_ENABLED"
ENV_BACKUP_DIR: Final[str] = f"{ENV_VAR_PREFIX}BACKUP_DIR"
ENV_MAX_BACKUPS: Final[str] = f"{ENV_VAR_PREFIX}MAX_BACKUPS"

# Validation settings
ENV_STRICT_VALIDATION: Final[str] = f"{ENV_VAR_PREFIX}STRICT_VALIDATION"
ENV_AUTO_FIX_PERMISSIONS: Final[str] = f"{ENV_VAR_PREFIX}AUTO_FIX_PERMISSIONS"


# =============================================================================
# Default Configuration Values
# =============================================================================

DEFAULT_PROCESSES_DIR: Final[str] = "~/.stageflow/"
DEFAULT_FORMAT: Final[str] = "yaml"
DEFAULT_CREATE_DIR: Final[bool] = True
DEFAULT_BACKUP_ENABLED: Final[bool] = False
DEFAULT_MAX_BACKUPS: Final[int] = 5
DEFAULT_STRICT_VALIDATION: Final[bool] = True
DEFAULT_AUTO_FIX_PERMISSIONS: Final[bool] = True


# =============================================================================
# File Format Constants
# =============================================================================

FILE_EXT_YAML: Final[str] = "yaml"
FILE_EXT_YML: Final[str] = "yml"
FILE_EXT_JSON: Final[str] = "json"

# Supported file extensions for auto-detection
SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (
    FILE_EXT_YAML,
    FILE_EXT_YML,
    FILE_EXT_JSON,
)


# =============================================================================
# Directory and Permission Constants
# =============================================================================

DEFAULT_DIR_PERMISSIONS: Final[int] = 0o755
BACKUP_SUBDIR_NAME: Final[str] = ".backups"


# =============================================================================
# Boolean String Parsing
# =============================================================================

TRUTHY_VALUES: Final[tuple[str, ...]] = ("true", "1", "yes", "on")
FALSY_VALUES: Final[tuple[str, ...]] = ("false", "0", "no", "off")


# =============================================================================
# Helper Functions
# =============================================================================


def get_env_bool(env_var: str, default: bool) -> bool:
    """
    Get boolean value from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value from environment or default
    """
    value = os.getenv(env_var, str(default)).lower()
    return value in TRUTHY_VALUES


def get_env_int(env_var: str, default: int) -> int:
    """
    Get integer value from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set

    Returns:
        Integer value from environment or default
    """
    try:
        return int(os.getenv(env_var, str(default)))
    except ValueError:
        return default


def get_env_str(env_var: str, default: str) -> str:
    """
    Get string value from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set

    Returns:
        String value from environment or default
    """
    return os.getenv(env_var, default)


# =============================================================================
# Configuration Value Getters (reads from environment)
# =============================================================================


def get_processes_dir() -> str:
    """Get processes directory from environment or default."""
    return get_env_str(ENV_PROCESSES_DIR, DEFAULT_PROCESSES_DIR)


def get_default_format() -> str:
    """Get default file format from environment or default."""
    return get_env_str(ENV_DEFAULT_FORMAT, DEFAULT_FORMAT).lower()


def get_create_dir() -> bool:
    """Get create directory flag from environment or default."""
    return get_env_bool(ENV_CREATE_DIR, DEFAULT_CREATE_DIR)


def get_backup_enabled() -> bool:
    """Get backup enabled flag from environment or default."""
    return get_env_bool(ENV_BACKUP_ENABLED, DEFAULT_BACKUP_ENABLED)


def get_backup_dir() -> str | None:
    """Get backup directory from environment or None."""
    return os.getenv(ENV_BACKUP_DIR)


def get_max_backups() -> int:
    """Get maximum backups from environment or default."""
    return get_env_int(ENV_MAX_BACKUPS, DEFAULT_MAX_BACKUPS)


def get_strict_validation() -> bool:
    """Get strict validation flag from environment or default."""
    return get_env_bool(ENV_STRICT_VALIDATION, DEFAULT_STRICT_VALIDATION)


def get_auto_fix_permissions() -> bool:
    """Get auto-fix permissions flag from environment or default."""
    return get_env_bool(ENV_AUTO_FIX_PERMISSIONS, DEFAULT_AUTO_FIX_PERMISSIONS)


# =============================================================================
# Documentation
# =============================================================================

ENVIRONMENT_VARIABLE_DOCS = """
Environment Variables Reference:

Core Settings:
  STAGEFLOW_PROCESSES_DIR       - Directory containing process files
                                  Default: ~/.stageflow/
  STAGEFLOW_DEFAULT_FORMAT      - Default file format: yaml|json|auto
                                  Default: yaml
  STAGEFLOW_CREATE_DIR          - Create directory if missing: true|false
                                  Default: true

Backup Settings:
  STAGEFLOW_BACKUP_ENABLED      - Enable file backups: true|false
                                  Default: false
  STAGEFLOW_BACKUP_DIR          - Backup directory path
                                  Default: <processes_dir>/.backups
  STAGEFLOW_MAX_BACKUPS         - Maximum backup files to keep
                                  Default: 5

Validation Settings:
  STAGEFLOW_STRICT_VALIDATION   - Enable strict validation: true|false
                                  Default: true
  STAGEFLOW_AUTO_FIX_PERMISSIONS - Auto-fix directory permissions: true|false
                                  Default: true

Examples:
  export STAGEFLOW_PROCESSES_DIR="./processes"
  export STAGEFLOW_DEFAULT_FORMAT="yaml"
  export STAGEFLOW_BACKUP_ENABLED="true"
  export STAGEFLOW_MAX_BACKUPS="10"
"""
