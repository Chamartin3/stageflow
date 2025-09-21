"""Registry for custom validators and gates in StageFlow.

This module provides comprehensive registry functionality for managing custom
validators, gate builders, and validation patterns that extend the core
StageFlow validation framework.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from stageflow.core.element import Element
from stageflow.gates.config import LockConfig, GateConfig, ValidatorConfig
from stageflow.gates.lock import Lock, LockType
from stageflow.gates.gate import Gate


@dataclass
class ValidatorEntry:
    """Entry in the custom validator registry."""

    name: str
    validator: Callable[[Any, Any], bool]
    description: str = ""
    expected_params: dict[str, str] = field(default_factory=dict)
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    is_async: bool = False
    thread_safe: bool = True
    examples: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: ValidatorConfig, validator: Callable[[Any, Any], bool]) -> "ValidatorEntry":
        """Create ValidatorEntry from ValidatorConfig."""
        return cls(
            name=config["name"],
            validator=validator,
            description=config["description"],
            expected_params=config.get("expected_params", {}),
            version=config.get("version", "1.0.0"),
            author=config.get("author", ""),
            tags=config.get("tags", []),
            is_async=config.get("is_async", False),
            thread_safe=config.get("thread_safe", True),
            examples=config.get("examples", [])
        )


@dataclass
class GateBuilderEntry:
    """Entry for custom gate builders in the registry."""

    name: str
    builder: Callable[..., Gate]
    description: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)


class GatesRegistry:
    """
    Central registry for custom validators, gate builders, and patterns.

    Provides a unified interface for registering and managing extensions
    to the StageFlow gates and validation system.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._validators: dict[str, ValidatorEntry] = {}
        self._gate_builders: dict[str, GateBuilderEntry] = {}
        self._lock_patterns: dict[str, LockConfig] = {}
        self._gate_patterns: dict[str, GateConfig] = {}

    # Validator management
    def register_validator(
        self,
        name: str,
        validator: Callable[[Any, Any], bool],
        description: str = "",
        expected_params: Optional[dict[str, str]] = None,
        **metadata
    ) -> None:
        """
        Register a custom validator function.

        Args:
            name: Unique name for the validator
            validator: Function that takes (value, expected_value) and returns bool
            description: Human-readable description
            expected_params: Dictionary describing expected parameters
            **metadata: Additional metadata (version, author, tags, etc.)
        """
        if name in self._validators:
            raise ValueError(f"Validator '{name}' is already registered")

        entry = ValidatorEntry(
            name=name,
            validator=validator,
            description=description,
            expected_params=expected_params or {},
            version=metadata.get("version", "1.0.0"),
            author=metadata.get("author", ""),
            tags=metadata.get("tags", []),
            is_async=metadata.get("is_async", False),
            thread_safe=metadata.get("thread_safe", True),
            examples=metadata.get("examples", [])
        )

        self._validators[name] = entry

    def register_validator_from_config(
        self,
        config: ValidatorConfig,
        validator: Callable[[Any, Any], bool]
    ) -> None:
        """Register validator from ValidatorConfig interface."""
        if config["name"] in self._validators:
            raise ValueError(f"Validator '{config['name']}' is already registered")

        entry = ValidatorEntry.from_config(config, validator)
        self._validators[config["name"]] = entry

    def unregister_validator(self, name: str) -> None:
        """
        Unregister a custom validator.

        Args:
            name: Name of validator to remove

        Raises:
            KeyError: If validator doesn't exist
        """
        if name not in self._validators:
            raise KeyError(f"Validator '{name}' is not registered")

        del self._validators[name]

    def get_validator(self, name: str) -> ValidatorEntry:
        """
        Get a registered validator.

        Args:
            name: Name of validator to retrieve

        Returns:
            ValidatorEntry instance

        Raises:
            KeyError: If validator doesn't exist
        """
        if name not in self._validators:
            raise KeyError(f"Validator '{name}' is not registered")

        return self._validators[name]

    def get_validator_function(self, name: str) -> Callable[[Any, Any], bool]:
        """Get just the validator function by name."""
        return self.get_validator(name).validator

    def validate(self, name: str, value: Any, expected_value: Any) -> bool:
        """
        Execute a custom validator.

        Args:
            name: Name of validator to execute
            value: Value to validate
            expected_value: Expected value or parameters

        Returns:
            True if validation passes, False otherwise

        Raises:
            KeyError: If validator doesn't exist
        """
        validator_entry = self.get_validator(name)
        try:
            return validator_entry.validator(value, expected_value)
        except Exception:
            # Custom validators should handle their own exceptions
            # Return False for any validation errors
            return False

    def list_validators(self) -> dict[str, str]:
        """
        List all registered validators.

        Returns:
            Dictionary mapping validator names to descriptions
        """
        return {name: entry.description for name, entry in self._validators.items()}

    def search_validators(self, tags: Optional[list[str]] = None, author: Optional[str] = None) -> list[str]:
        """
        Search validators by tags or author.

        Args:
            tags: List of tags to search for
            author: Author to search for

        Returns:
            List of matching validator names
        """
        matches = []
        for name, entry in self._validators.items():
            if tags and not any(tag in entry.tags for tag in tags):
                continue
            if author and entry.author != author:
                continue
            matches.append(name)
        return matches

    # Gate builder management
    def register_gate_builder(
        self,
        name: str,
        builder: Callable[..., Gate],
        description: str = "",
        parameters: Optional[dict[str, str]] = None,
        examples: Optional[list[dict[str, Any]]] = None
    ) -> None:
        """
        Register a custom gate builder function.

        Args:
            name: Unique name for the gate builder
            builder: Function that creates Gate instances
            description: Human-readable description
            parameters: Dictionary describing expected parameters
            examples: List of example configurations
        """
        if name in self._gate_builders:
            raise ValueError(f"Gate builder '{name}' is already registered")

        entry = GateBuilderEntry(
            name=name,
            builder=builder,
            description=description,
            parameters=parameters or {},
            examples=examples or []
        )

        self._gate_builders[name] = entry

    def get_gate_builder(self, name: str) -> GateBuilderEntry:
        """Get a registered gate builder."""
        if name not in self._gate_builders:
            raise KeyError(f"Gate builder '{name}' is not registered")
        return self._gate_builders[name]

    def build_gate(self, name: str, *args, **kwargs) -> Gate:
        """Execute a gate builder function."""
        builder_entry = self.get_gate_builder(name)
        return builder_entry.builder(*args, **kwargs)

    def list_gate_builders(self) -> dict[str, str]:
        """List all registered gate builders."""
        return {name: entry.description for name, entry in self._gate_builders.items()}

    # Pattern management
    def register_lock_pattern(self, name: str, config: LockConfig) -> None:
        """Register a reusable lock configuration pattern."""
        if name in self._lock_patterns:
            raise ValueError(f"Lock pattern '{name}' is already registered")
        self._lock_patterns[name] = config

    def register_gate_pattern(self, name: str, config: GateConfig) -> None:
        """Register a reusable gate configuration pattern."""
        if name in self._gate_patterns:
            raise ValueError(f"Gate pattern '{name}' is already registered")
        self._gate_patterns[name] = config

    def get_lock_pattern(self, name: str) -> LockConfig:
        """Get a registered lock pattern."""
        if name not in self._lock_patterns:
            raise KeyError(f"Lock pattern '{name}' is not registered")
        return self._lock_patterns[name]

    def get_gate_pattern(self, name: str) -> GateConfig:
        """Get a registered gate pattern."""
        if name not in self._gate_patterns:
            raise KeyError(f"Gate pattern '{name}' is not registered")
        return self._gate_patterns[name]

    def create_lock_from_pattern(self, pattern_name: str, property_path: str, **overrides) -> Lock:
        """Create a Lock instance from a registered pattern."""
        pattern = self.get_lock_pattern(pattern_name)

        # Apply overrides to pattern
        config = pattern.copy()
        config.update(overrides)
        config["property_path"] = property_path

        # Convert string lock_type to enum
        lock_type = LockType(config["lock_type"])

        return Lock(
            lock_type=lock_type,
            property_path=config["property_path"],
            expected_value=config.get("expected_value"),
            validator_name=config.get("validator_name"),
            metadata=config.get("metadata", {})
        )

    # Registry management
    def clear_all(self) -> None:
        """Clear all registered items."""
        self._validators.clear()
        self._gate_builders.clear()
        self._lock_patterns.clear()
        self._gate_patterns.clear()

    def export_registry(self) -> dict[str, Any]:
        """Export registry contents for serialization."""
        return {
            "validators": {name: {
                "name": entry.name,
                "description": entry.description,
                "expected_params": entry.expected_params,
                "version": entry.version,
                "author": entry.author,
                "tags": entry.tags,
                "is_async": entry.is_async,
                "thread_safe": entry.thread_safe,
                "examples": entry.examples
            } for name, entry in self._validators.items()},
            "gate_builders": {name: {
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.parameters,
                "examples": entry.examples
            } for name, entry in self._gate_builders.items()},
            "lock_patterns": self._lock_patterns,
            "gate_patterns": self._gate_patterns
        }

    def get_stats(self) -> dict[str, int]:
        """Get registry statistics."""
        return {
            "validators": len(self._validators),
            "gate_builders": len(self._gate_builders),
            "lock_patterns": len(self._lock_patterns),
            "gate_patterns": len(self._gate_patterns)
        }


# Global registry instance
_global_registry = GatesRegistry()


def get_global_registry() -> GatesRegistry:
    """Get the global gates registry instance."""
    return _global_registry


# Convenience functions for global registry
def register_validator(
    name: str,
    validator: Callable[[Any, Any], bool],
    description: str = "",
    expected_params: Optional[dict[str, str]] = None,
    **metadata
) -> None:
    """Register a validator in the global registry."""
    _global_registry.register_validator(name, validator, description, expected_params, **metadata)


def get_validator(name: str) -> Callable[[Any, Any], bool]:
    """Get a validator function from the global registry."""
    return _global_registry.get_validator_function(name)


def register_gate_builder(
    name: str,
    builder: Callable[..., Gate],
    description: str = "",
    parameters: Optional[dict[str, str]] = None,
    examples: Optional[list[dict[str, Any]]] = None
) -> None:
    """Register a gate builder in the global registry."""
    _global_registry.register_gate_builder(name, builder, description, parameters, examples)


def register_lock_pattern(name: str, config: LockConfig) -> None:
    """Register a lock pattern in the global registry."""
    _global_registry.register_lock_pattern(name, config)


def register_gate_pattern(name: str, config: GateConfig) -> None:
    """Register a gate pattern in the global registry."""
    _global_registry.register_gate_pattern(name, config)


# Example validators for common patterns
def _validate_email_format(value: Any, expected_value: Any) -> bool:
    """Validate basic email format."""
    if not isinstance(value, str):
        return False
    return "@" in value and "." in value.split("@")[-1]


def _validate_phone_format(value: Any, expected_value: Any) -> bool:
    """Validate phone number format."""
    import re
    if not isinstance(value, str):
        return False
    # Simple phone validation - can be customized
    pattern = r"^\+?[\d\s\-\(\)]+$"
    return bool(re.match(pattern, value))


def _validate_date_iso(value: Any, expected_value: Any) -> bool:
    """Validate ISO date format."""
    if not isinstance(value, str):
        return False
    try:
        from datetime import datetime
        datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


# Register common validators
register_validator(
    "email_format",
    _validate_email_format,
    "Validate basic email format",
    {"value": "email string to validate", "expected_value": "unused"}
)

register_validator(
    "phone_format",
    _validate_phone_format,
    "Validate phone number format",
    {"value": "phone string to validate", "expected_value": "unused"}
)

register_validator(
    "iso_date",
    _validate_date_iso,
    "Validate ISO date format",
    {"value": "date string to validate", "expected_value": "unused"}
)


# Common lock patterns
register_lock_pattern("email_required", {
    "property_path": "",  # Will be set when creating lock
    "lock_type": "custom",
    "validator_name": "email_format",
    "description": "Required email field validation"
})

register_lock_pattern("phone_optional", {
    "property_path": "",  # Will be set when creating lock
    "lock_type": "custom",
    "validator_name": "phone_format",
    "allow_missing": True,
    "description": "Optional phone field validation"
})

register_lock_pattern("non_empty_string", {
    "property_path": "",  # Will be set when creating lock
    "lock_type": "not_empty",
    "description": "Non-empty string validation"
})