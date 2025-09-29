"""Common interfaces and abstract base classes for StageFlow.

This module defines the core interfaces and protocols that establish
contracts between different components of the StageFlow framework.
"""

from abc import ABC, abstractmethod
from typing import Any

from .types import ElementData, EvaluationContext, PropertyPath, ValidationResult


class ElementInterface(ABC):
    """Abstract interface for data elements in StageFlow."""

    @abstractmethod
    def get_property(self, path: PropertyPath) -> Any:
        """Get property value using dot/bracket notation."""
        pass

    @abstractmethod
    def has_property(self, path: PropertyPath) -> bool:
        """Check if property exists."""
        pass

    @abstractmethod
    def to_dict(self) -> ElementData:
        """Convert element to dictionary representation."""
        pass


class ValidatorInterface(ABC):
    """Abstract interface for validators."""

    @abstractmethod
    def validate(self, value: Any, expected_value: Any, context: EvaluationContext | None = None) -> ValidationResult:
        """Validate a value against expected criteria."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get validator name."""
        pass


class LockInterface(ABC):
    """Abstract interface for validation locks."""

    @abstractmethod
    def evaluate(self, element: ElementInterface) -> "LockResult":
        """Evaluate lock against element."""
        pass

    @property
    @abstractmethod
    def property_path(self) -> PropertyPath:
        """Get property path this lock validates."""
        pass

    @property
    @abstractmethod
    def name(self) -> str | None:
        """Get lock name."""
        pass


class GateInterface(ABC):
    """Abstract interface for validation gates."""

    @abstractmethod
    def evaluate(self, element: ElementInterface) -> "GateResult":
        """Evaluate gate against element."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get gate name."""
        pass

    @abstractmethod
    def get_property_paths(self) -> list[PropertyPath]:
        """Get all property paths used by this gate."""
        pass


class StageInterface(ABC):
    """Abstract interface for validation stages."""

    @abstractmethod
    def evaluate(self, element: ElementInterface) -> "StageResult":
        """Evaluate stage against element."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get stage name."""
        pass

    @abstractmethod
    def get_required_properties(self) -> set[PropertyPath]:
        """Get properties required by this stage."""
        pass


class ProcessInterface(ABC):
    """Abstract interface for validation processes."""

    @abstractmethod
    def evaluate(self, element: ElementInterface, current_stage_name: str | None = None) -> "StatusResult":
        """Evaluate element against process."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get process name."""
        pass

    @abstractmethod
    def get_stage(self, stage_name: str) -> StageInterface | None:
        """Get stage by name."""
        pass


class RegistryInterface(ABC):
    """Abstract interface for component registries."""

    @abstractmethod
    def register_validator(self, name: str, validator: ValidatorInterface) -> None:
        """Register a validator."""
        pass

    @abstractmethod
    def get_validator(self, name: str) -> ValidatorInterface:
        """Get a validator by name."""
        pass

    @abstractmethod
    def register_pattern(self, name: str, pattern: dict[str, Any]) -> None:
        """Register a reusable pattern."""
        pass


class LoaderInterface(ABC):
    """Abstract interface for configuration loaders."""

    @abstractmethod
    def load(self, source: str | dict[str, Any]) -> dict[str, Any]:
        """Load configuration from source."""
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration structure."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Get supported file formats."""
        pass


class ExtensionInterface(ABC):
    """Abstract interface for framework extensions."""

    @abstractmethod
    def initialize(self, registry: RegistryInterface) -> None:
        """Initialize extension with registry."""
        pass

    @abstractmethod
    def register_components(self, registry: RegistryInterface) -> None:
        """Register extension components."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get extension name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Get extension version."""
        pass


# Result interfaces
class ResultInterface(ABC):
    """Abstract interface for evaluation results."""

    @property
    @abstractmethod
    def success(self) -> bool:
        """Whether the evaluation was successful."""
        pass

    @property
    @abstractmethod
    def errors(self) -> list[str]:
        """List of error messages."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Additional result metadata."""
        pass


class LockResultInterface(ResultInterface):
    """Interface for lock evaluation results."""

    @property
    @abstractmethod
    def passed(self) -> bool:
        """Whether the lock passed."""
        pass

    @property
    @abstractmethod
    def property_value(self) -> Any:
        """The value that was validated."""
        pass


class GateResultInterface(ResultInterface):
    """Interface for gate evaluation results."""

    @property
    @abstractmethod
    def passed(self) -> bool:
        """Whether the gate passed."""
        pass

    @property
    @abstractmethod
    def lock_results(self) -> dict[str, LockResultInterface]:
        """Results from individual locks."""
        pass

    @property
    @abstractmethod
    def actions(self) -> list[str]:
        """Recommended actions based on evaluation."""
        pass


class StageResultInterface(ResultInterface):
    """Interface for stage evaluation results."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of the evaluated stage."""
        pass

    @property
    @abstractmethod
    def overall_passed(self) -> bool:
        """Whether the stage passed overall."""
        pass

    @property
    @abstractmethod
    def gate_results(self) -> dict[str, GateResultInterface]:
        """Results from individual gates."""
        pass


# Factory interfaces
class ComponentFactory(ABC):
    """Abstract factory for creating components."""

    @abstractmethod
    def create_element(self, data: ElementData, **kwargs) -> ElementInterface:
        """Create element from data."""
        pass

    @abstractmethod
    def create_lock(self, config: dict[str, Any]) -> LockInterface:
        """Create lock from configuration."""
        pass

    @abstractmethod
    def create_gate(self, config: dict[str, Any]) -> GateInterface:
        """Create gate from configuration."""
        pass

    @abstractmethod
    def create_stage(self, config: dict[str, Any]) -> StageInterface:
        """Create stage from configuration."""
        pass
