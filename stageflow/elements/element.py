"""Element interface and implementations for StageFlow."""

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Optional, TypedDict


class ElementConfig(TypedDict):
    """TypedDict for element configuration with data and options."""

    data: dict[str, Any]


class ElementDataConfig(TypedDict, total=False):
    """TypedDict for element data configuration."""

    data: dict[str, Any]


@dataclass
class FunctionCall:
    """Represents a function call in a property path."""

    function_name: str
    argument_path: str

    @classmethod
    def parse(cls, path: str) -> Optional["FunctionCall"]:
        """
        Parse function call syntax: function_name(argument_path)

        Args:
            path: Property path that may contain function syntax

        Returns:
            FunctionCall if path is a function, None otherwise

        Examples:
            length(items) → FunctionCall("length", "items")
            count(array) → FunctionCall("count", "array")
            items.length → None (not function syntax)
            regular.path → None (not function syntax)
        """
        if not path or not path.endswith(")"):
            return None

        # Find opening parenthesis
        paren_pos = path.find("(")
        if paren_pos == -1:
            return None

        function_name = path[:paren_pos].strip()
        argument_path = path[paren_pos + 1 : -1].strip()

        # Only support length/count functions initially
        if function_name.lower() in ("length", "count"):
            return cls(function_name=function_name.lower(), argument_path=argument_path)

        return None


@dataclass
class FilterSegment:
    """
    Represents a filter expression in a property path.

    Syntax: [?property==value]

    Examples:
        [?id=='work_done'] → FilterSegment("id", "==", "work_done")
        [?status=='active'] → FilterSegment("status", "==", "active")
        [?count==5] → FilterSegment("count", "==", 5)
        [?flag==true] → FilterSegment("flag", "==", True)
    """

    property: str
    operator: Literal["=="]  # Only equality initially
    value: Any  # str, int, bool, None

    def matches(self, item: dict) -> bool:
        """
        Check if an item matches this filter criteria.

        Args:
            item: Dictionary to test against filter

        Returns:
            True if item matches filter, False otherwise

        Examples:
            >>> filter = FilterSegment("id", "==", "work_done")
            >>> filter.matches({"id": "work_done", "name": "Task"})
            True
            >>> filter.matches({"id": "other", "name": "Task"})
            False
        """
        if not isinstance(item, dict):
            return False

        item_value = item.get(self.property)

        # Type-aware comparison
        if self.operator == "==":
            return item_value == self.value

        return False  # Unsupported operator

    @classmethod
    def parse(cls, filter_expr: str) -> Optional["FilterSegment"]:
        """
        Parse filter expression from bracket content.

        Args:
            filter_expr: Content between [? and ], e.g., "id=='work_done'"

        Returns:
            FilterSegment if valid, None otherwise

        Examples:
            parse("id=='work_done'") → FilterSegment("id", "==", "work_done")
            parse("count==5") → FilterSegment("count", "==", 5)
            parse("active==true") → FilterSegment("active", "==", True)
            parse("value==null") → FilterSegment("value", "==", None)
            parse("invalid") → None
        """
        if not filter_expr or not filter_expr.startswith("?"):
            return None

        # Remove leading '?'
        expr = filter_expr[1:].strip()

        # Find == operator
        if "==" not in expr:
            return None

        parts = expr.split("==", 1)
        if len(parts) != 2:
            return None

        property_name = parts[0].strip()
        value_str = parts[1].strip()

        # Parse value (string, number, boolean, null)
        value = cls._parse_value(value_str)

        if property_name and value is not ...:  # Use ... as sentinel for parse error
            return cls(property=property_name, operator="==", value=value)

        return None

    @classmethod
    def _parse_value(cls, value_str: str) -> Any:
        """
        Parse value from string representation.

        Args:
            value_str: String representation of value

        Returns:
            Parsed value (str, int, bool, None) or ... for parse error

        Examples:
            "'string'" → "string"
            '"string"' → "string"
            "123" → 123
            "true" → True
            "false" → False
            "null" → None
        """
        value_str = value_str.strip()

        # String literals (single or double quotes)
        if (value_str.startswith("'") and value_str.endswith("'")) or (
            value_str.startswith('"') and value_str.endswith('"')
        ):
            return value_str[1:-1]  # Remove quotes

        # Boolean literals
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Null/None literal
        if value_str.lower() in ("null", "none"):
            return None

        # Numeric literals
        try:
            # Try integer first
            if "." not in value_str:
                return int(value_str)
            # Try float
            return float(value_str)
        except ValueError:
            pass

        # Parse error
        return ...  # Sentinel value


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

    Wraps a dictionary and provides property access via dot notation,
    bracket notation, and get_property method calls. The wrapped data
    remains completely immutable.
    """

    def __init__(self, data: dict[str, Any] | ElementConfig | ElementDataConfig):
        """
        Initialize with dictionary data or ElementConfig.

        Args:
            data: Dictionary, ElementConfig, or ElementDataConfig containing element data
        """
        if isinstance(data, dict):
            # Handle both direct dict and ElementConfig/ElementDataConfig
            if "data" in data and isinstance(data["data"], dict):
                # This is an ElementConfig or ElementDataConfig
                config = data
                self._data = deepcopy(config["data"])
                self._config = config
            else:
                # This is a plain dictionary
                self._data = deepcopy(data)
                self._config = None
        else:
            # Handle other types (for backward compatibility)
            self._data = deepcopy(data)
            self._config = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        import copy

        return copy.deepcopy(self._data)  # type: ignore

    def __getattr__(self, name: str) -> Any:
        """
        Enable dot notation access to properties.

        Args:
            name: Property name to access

        Returns:
            Property value, or DictElement for nested dictionaries

        Raises:
            AttributeError: If property doesn't exist
        """
        try:
            value = self.get_property(name)
            # Return DictElement for nested dictionaries to maintain interface
            if isinstance(value, dict):
                return DictElement(value)
            return value
        except (KeyError, IndexError, TypeError) as err:
            raise AttributeError(f"Element has no attribute '{name}'") from err

    def __getitem__(self, key: str) -> Any:
        """
        Enable bracket notation access to properties.

        Args:
            key: Property key to access

        Returns:
            Property value, or DictElement for nested dictionaries

        Raises:
            KeyError: If property doesn't exist
        """
        value = self.get_property(key)
        # Return DictElement for nested dictionaries to maintain interface
        if isinstance(value, dict):
            return DictElement(value)
        return value

    def __iter__(self):
        """Enable iteration over top-level property keys."""
        return iter(self._data)

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for checking property existence."""
        return self.has_property(key)

    def keys(self):
        """Return top-level property keys."""
        return self._data.keys()

    def values(self):
        """Return top-level property values."""
        for value in self._data.values():
            if isinstance(value, dict):
                yield DictElement(value)
            else:
                yield value

    def items(self):
        """Return top-level property key-value pairs."""
        for key, value in self._data.items():
            if isinstance(value, dict):
                yield key, DictElement(value)
            else:
                yield key, value

    def _resolve_path(self, data: Any, path: str) -> Any:
        """
        Resolve property path in data structure.

        Supports both dot notation and bracket notation:
        - Simple dot notation: "user.profile.name"
        - Simple bracket notation: "user['profile']['name']"
        - Mixed notation: "settings.themes[0]['colors'].primary"
        - Array access: "items[1].id"
        - Quoted keys: "data['key with spaces']"
        - Escaped characters: "data['key\\.with\\.dots']"

        Args:
            data: Data to search in
            path: Property path using dot/bracket notation

        Returns:
            Resolved value

        Raises:
            KeyError: If property path doesn't exist
            IndexError: If array index is out of bounds
            TypeError: If path cannot be resolved on the data type
            ValueError: If path syntax is invalid
        """
        if not path:
            return data

        try:
            parts = self._parse_path(path)
            result = data

            for i, part in enumerate(parts):
                try:
                    if isinstance(part, int):
                        # Array/list index access
                        result = result[part]
                    else:
                        # Object/dict key access
                        result = result[part]
                except (KeyError, IndexError, TypeError) as e:
                    # Provide context in error messages
                    partial_path = self._reconstruct_path(parts[: i + 1])
                    if isinstance(e, KeyError):
                        raise KeyError(
                            f"Property '{part}' not found at path '{partial_path}'"
                        ) from e
                    elif isinstance(e, IndexError):
                        raise IndexError(
                            f"Index {part} out of bounds at path '{partial_path}'"
                        ) from e
                    else:
                        raise TypeError(
                            f"Cannot access '{part}' on {type(result).__name__} at path '{partial_path}'"
                        ) from e

            return result

        except Exception as e:
            # Re-raise with path context if not already provided
            if "at path" not in str(e):
                raise type(e)(f"{str(e)} in path '{path}'") from e
            raise

    def _parse_path(self, path: str) -> list[str | int]:
        """
        Parse a property path into a list of keys/indices.

        Handles:
        - Dot notation: "user.profile.name" -> ["user", "profile", "name"]
        - Bracket notation: "user['profile']['name']" -> ["user", "profile", "name"]
        - Mixed notation: "settings.themes[0]['colors'].primary" -> ["settings", "themes", 0, "colors", "primary"]
        - Quoted keys: "data['key with spaces']" -> ["data", "key with spaces"]
        - Escaped quotes: "data['key\\'with\\'quotes']" -> ["data", "key'with'quotes"]

        Args:
            path: Raw path string

        Returns:
            List of string keys and integer indices

        Raises:
            ValueError: If path syntax is invalid
        """
        if not path:
            return []

        parts = []
        i = 0
        current_key = ""

        while i < len(path):
            char = path[i]

            if char == ".":
                # Dot separator - end current key
                if current_key:
                    parts.append(current_key)
                    current_key = ""
            elif char == "[":
                # Start of bracket notation
                if current_key:
                    parts.append(current_key)
                    current_key = ""

                # Parse bracket content
                bracket_content, bracket_end = self._parse_bracket(path, i)
                parts.append(bracket_content)
                i = bracket_end
            else:
                # Regular character - add to current key
                current_key += char

            i += 1

        # Add final key if present
        if current_key:
            parts.append(current_key)

        return parts

    def _parse_bracket(self, path: str, start_index: int) -> tuple[str | int, int]:
        """
        Parse bracket notation starting at the given index.

        Args:
            path: Full path string
            start_index: Index of opening bracket

        Returns:
            Tuple of (parsed_value, end_index)

        Raises:
            ValueError: If bracket syntax is invalid
        """
        if path[start_index] != "[":
            raise ValueError(f"Expected '[' at position {start_index}")

        i = start_index + 1
        content = ""
        in_quotes = False
        quote_char = None

        while i < len(path):
            char = path[i]

            if not in_quotes:
                if char in ("'", '"'):
                    # Start of quoted string
                    in_quotes = True
                    quote_char = char
                elif char == "]":
                    # End of bracket
                    break
                elif char.isspace():
                    # Skip whitespace outside quotes
                    pass
                else:
                    content += char
            else:
                if char == quote_char:
                    # Check for escaped quote
                    if i > 0 and path[i - 1] == "\\":
                        # Escaped quote - add to content
                        content = content[:-1] + char  # Remove backslash and add quote
                    else:
                        # End of quoted string
                        in_quotes = False
                        quote_char = None
                else:
                    content += char

            i += 1

        if i >= len(path):
            raise ValueError(f"Unclosed bracket starting at position {start_index}")

        if in_quotes:
            raise ValueError(
                f"Unclosed quote in bracket starting at position {start_index}"
            )

        # Try to parse as integer for array access
        try:
            return int(content), i
        except ValueError:
            # Return as string key
            return content, i

    def _reconstruct_path(self, parts: list[str | int]) -> str:
        """
        Reconstruct a path string from parsed parts for error messages.

        Args:
            parts: List of parsed path parts

        Returns:
            Reconstructed path string
        """
        if not parts:
            return ""

        result = str(parts[0])
        for part in parts[1:]:
            if isinstance(part, int):
                result += f"[{part}]"
            elif isinstance(part, str):
                # Use bracket notation for keys with special characters
                if "." in part or " " in part or "'" in part or '"' in part:
                    # Escape single quotes in the key
                    escaped_key = part.replace("'", "\\'")
                    result += f"['{escaped_key}']"
                else:
                    result += f".{part}"

        return result

    def _is_length_property(self, path: str) -> tuple[bool, str]:
        """
        Check if path ends with .length suffix.

        Args:
            path: Property path to check

        Returns:
            Tuple of (is_length_property, base_path)
            - is_length_property: True if path ends with .length
            - base_path: Path without .length suffix (if applicable)

        Examples:
            "items.length" → (True, "items")
            "user.posts.length" → (True, "user.posts")
            "length" → (False, "length")  # Not a property, just a field name
            "items" → (False, "items")
        """
        if path.endswith(".length"):
            base_path = path[:-7]  # Remove '.length'
            # Ensure base_path is not empty
            if base_path:
                return True, base_path
        return False, path

    def _get_length(self, path: str) -> int | None:
        """
        Get the length of a property value.

        Supports both function call syntax (length(path)) and property syntax (path.length).

        Args:
            path: Property path that may be a length operation

        Returns:
            Length of the property value, or None if the operation is invalid

        Raises:
            ValueError: If path syntax is invalid or property cannot be measured
        """
        # Check for function call syntax: length(argument_path)
        function_call = FunctionCall.parse(path)
        if function_call:
            if function_call.function_name in ("length", "count"):
                base_path = function_call.argument_path
                # Check for empty argument
                if not base_path.strip():
                    return None
            else:
                raise ValueError(
                    f"Unsupported function '{function_call.function_name}' in path '{path}'"
                )
        else:
            # Check for property syntax: base_path.length
            is_length_prop, base_path = self._is_length_property(path)
            if not is_length_prop:
                raise ValueError(f"Path '{path}' is not a valid length operation")

        # Resolve the base property
        try:
            value = self._resolve_path(self._data, base_path)
        except (KeyError, IndexError, TypeError):
            # Return None for invalid paths instead of raising
            return None

        # Get length based on value type
        try:
            if isinstance(value, (list, tuple)):
                return len(value)
            elif isinstance(value, str):
                return len(value)
            elif isinstance(value, dict):
                return len(value)
            elif isinstance(value, set):
                return len(value)
            elif hasattr(value, "__len__"):
                # Generic length for any object with __len__
                return len(value)
            else:
                # Return None for unsupported types instead of raising
                return None
        except Exception:
            # Return None for any length operation errors
            return None

    def get_property(self, path: str) -> Any:
        """
        Get a property value using dot/bracket notation.

        Supports length operations via function call syntax (length(path))
        or property syntax (path.length).

        Args:
            path: Property path (e.g., "user.profile.name" or "items[0].price")
                  or length operation (e.g., "length(items)" or "items.length")

        Returns:
            The property value, or None if not found
        """
        # Ensure path is a string for length operations
        if not isinstance(path, str):
            # Non-string paths go directly to normal resolution
            try:
                return self._resolve_path(self._data, path)
            except (KeyError, IndexError, TypeError):
                return None

        # First try normal property resolution
        try:
            return self._resolve_path(self._data, path)
        except (KeyError, IndexError, TypeError):
            # Property doesn't exist normally, check for length operations
            pass

        # Check if this is a length operation
        try:
            function_call = FunctionCall.parse(path)
            if function_call and function_call.function_name in ("length", "count"):
                result = self._get_length(path)
                if result is not None:
                    return result
        except ValueError:
            # Not a valid function call
            pass

        # Check for property syntax: path.length (only if normal resolution failed)
        is_length_prop, _ = self._is_length_property(path)
        if is_length_prop:
            result = self._get_length(path)
            if result is not None:
                return result

        # All attempts failed
        return None

    def has_property(self, path: str) -> bool:
        """
        Check if a property exists.

        Args:
            path: Property path to check

        Returns:
            True if property exists, False otherwise
        """
        try:
            self._resolve_path(self._data, path)
            return True
        except (KeyError, IndexError, TypeError):
            return False


# Factory function for creating elements
def create_element(
    data: dict[str, Any] | Element | ElementConfig | ElementDataConfig,
) -> Element:
    """
    Create an Element instance from various data sources.

    Args:
        data: Dictionary, ElementConfig, ElementDataConfig, or existing Element instance

    Returns:
        Element instance
    """
    if isinstance(data, Element):
        return data
    elif isinstance(data, dict):
        return DictElement(data)
    else:
        raise TypeError(f"Cannot create Element from type {type(data)}")


def create_element_from_config(config: ElementConfig) -> Element:
    """
    Create an Element instance from ElementConfig TypedDict.

    Args:
        config: ElementConfig with data and configuration options

    Returns:
        Element instance
    """
    return DictElement(config)
