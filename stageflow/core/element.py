"""Element interface and implementations for StageFlow."""

from abc import ABC, abstractmethod
from typing import Any


class Element(ABC):
    """
    Abstract base class for data elements in StageFlow.

    Elements provide a consistent interface for accessing data properties
    during validation. The framework never modifies the element data,
    ensuring non-mutating evaluation.
    """

    @abstractmethod
    def get_property(self, path: str) -> Any:
        """
        Get a property value using dot/bracket notation.

        Args:
            path: Property path (e.g., "user.profile.name" or "items[0].price")

        Returns:
            The property value, or None if not found
        """
        pass

    @abstractmethod
    def has_property(self, path: str) -> bool:
        """
        Check if a property exists.

        Args:
            path: Property path to check

        Returns:
            True if property exists, False otherwise
        """
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """
        Convert element to dictionary representation.

        Returns:
            Dictionary representation of the element data
        """
        pass


class DictElement(Element):
    """
    Dictionary-based element implementation.

    Wraps a dictionary and provides property access via dot notation.
    """

    def __init__(self, data: dict[str, Any]):
        """
        Initialize with dictionary data.

        Args:
            data: Dictionary containing element data
        """
        self._data = data

    def get_property(self, path: str) -> Any:
        """Get property value using dot/bracket notation."""
        return self._resolve_path(self._data, path)

    def has_property(self, path: str) -> bool:
        """Check if property exists."""
        try:
            self._resolve_path(self._data, path)
            return True
        except (KeyError, IndexError, TypeError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self._data.copy()

    def _resolve_path(self, data: Any, path: str) -> Any:
        """
        Resolve property path in data structure.

        Args:
            data: Data to search in
            path: Property path (dot.notation or bracket[notation])

        Returns:
            Resolved value

        Raises:
            KeyError: If property path doesn't exist
            TypeError: If path cannot be resolved
        """
        if not path:
            return data

        # Split on dots, handling bracket notation
        parts = []
        current = ""
        bracket_depth = 0

        for char in path:
            if char == "[":
                bracket_depth += 1
                current += char
            elif char == "]":
                bracket_depth -= 1
                current += char
            elif char == "." and bracket_depth == 0:
                if current:
                    parts.append(current)
                current = ""
            else:
                current += char

        if current:
            parts.append(current)

        result = data
        for part in parts:
            if part.endswith("]") and "[" in part:
                # Handle bracket notation like "items[0]" or "data[key]"
                key, bracket = part.split("[", 1)
                index = bracket[:-1]  # Remove closing ]

                if key:
                    result = result[key]

                # Try numeric index first, then string key
                try:
                    result = result[int(index)]
                except (ValueError, TypeError):
                    result = result[index]
            else:
                result = result[part]

        return result


# Factory function for creating elements
def create_element(data: dict[str, Any] | Element) -> Element:
    """
    Create an Element instance from various data sources.

    Args:
        data: Dictionary or existing Element instance

    Returns:
        Element instance
    """
    if isinstance(data, Element):
        return data
    elif isinstance(data, dict):
        return DictElement(data)
    else:
        raise TypeError(f"Cannot create Element from type {type(data)}")
