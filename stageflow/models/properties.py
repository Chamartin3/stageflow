"""
Stage property definitions with validation.

Single file containing:
- Property type enum
- Pydantic models for validation
- Parser for YAML → models
- Validator for element values
"""

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# Property Types Enum
# ============================================================================


class PropertyType(str, Enum):
    """Supported property types."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"


# ============================================================================
# Property Models (Pydantic with inheritance)
# ============================================================================


class Property(BaseModel):
    """
    Base property with common fields.

    All property types inherit from this - reduces verbosity!
    """

    type: PropertyType
    required: bool = True
    default: Any | None = None
    description: str | None = None

    class Config:
        use_enum_values = True  # Serialize enum as string


class StringProperty(Property):
    """String property - inherits common fields from Property."""

    type: PropertyType = PropertyType.STRING

    # String-specific constraints
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    pattern: str | None = None
    format: str | None = None  # email, uri, uuid
    enum: list[str] | None = None

    @field_validator("pattern")
    @classmethod
    def validate_regex(cls, v: str | None) -> str | None:
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex: {e}") from e
        return v

    @model_validator(mode="after")
    def validate_constraints(self) -> "StringProperty":
        if self.min_length and self.max_length:
            if self.min_length > self.max_length:
                raise ValueError("min_length > max_length")
        return self


class NumberProperty(Property):
    """Number property (int/float) - inherits from Property."""

    type: PropertyType  # INT or FLOAT

    # Number-specific constraints
    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "NumberProperty":
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError("min > max")
        return self


class BoolProperty(Property):
    """Boolean property - simple, just inherits."""

    type: PropertyType = PropertyType.BOOL


class ListProperty(Property):
    """List property - inherits from Property."""

    type: PropertyType = PropertyType.LIST

    # List-specific constraints
    min_items: int | None = Field(None, ge=0)
    max_items: int | None = Field(None, ge=0)
    item_type: PropertyType | None = None
    unique: bool = False

    @model_validator(mode="after")
    def validate_constraints(self) -> "ListProperty":
        if self.min_items and self.max_items:
            if self.min_items > self.max_items:
                raise ValueError("min_items > max_items")
        return self


class DictProperty(Property):
    """Dictionary/object property - inherits from Property."""

    type: PropertyType = PropertyType.DICT

    # Nested properties
    properties: dict[str, "Property"] | None = None
    required_properties: list[str] | None = None


# ============================================================================
# Parser: YAML → Pydantic Models
# ============================================================================


class PropertiesParser:
    """Parse YAML property specs into validated Pydantic models."""

    # Type mapping for creating models
    TYPE_MODELS = {
        PropertyType.STRING: StringProperty,
        PropertyType.INT: NumberProperty,
        PropertyType.FLOAT: NumberProperty,
        PropertyType.BOOL: BoolProperty,
        PropertyType.LIST: ListProperty,
        PropertyType.DICT: DictProperty,
    }

    @classmethod
    def parse(cls, spec: Any) -> dict[str, Property]:
        """
        Parse any property spec format.

        Examples:
            >>> parse(["email", "password"])
            {"email": StringProperty(...), "password": StringProperty(...)}

            >>> parse({"email": "string", "age": "int"})
            {"email": StringProperty(...), "age": NumberProperty(...)}

            >>> parse([{"email": {"type": "string", "description": "User email"}}])
            {"email": StringProperty(description="User email", ...)}
        """
        # Level 1: List format (simple strings or single-key dicts)
        if isinstance(spec, list):
            result = {}
            for item in spec:
                # Simple string: "email"
                if isinstance(item, str):
                    if "." in item:
                        cls._add_nested(result, item, "string")
                    else:
                        result[item] = StringProperty()
                # Single-key dict: {"email": "string"} or {"email": {...}}
                elif isinstance(item, dict) and len(item) == 1:
                    name, value = next(iter(item.items()))
                    if isinstance(value, str):
                        result[name] = cls._from_type(value)
                    elif isinstance(value, dict):
                        if "type" in value:
                            result[name] = cls._from_dict(value)
                        else:
                            nested_props = cls.parse(value)
                            result[name] = DictProperty(properties=nested_props)
                    elif value is None:
                        result[name] = StringProperty()
                    else:
                        raise ValueError(f"Invalid spec for '{name}' in list")
                else:
                    raise ValueError(f"Invalid list item: {item}")
            return result

        # Level 2 & 3: Dictionary
        if isinstance(spec, dict):
            result = {}
            for name, value in spec.items():
                # Dot notation: profile.name
                if "." in name:
                    cls._add_nested(result, name, value)
                # Level 2: Type shortcut
                elif isinstance(value, str):
                    result[name] = cls._from_type(value)
                # Level 3: Full spec or nested properties
                elif isinstance(value, dict):
                    # Check if it's a full spec (has "type" key) or nested properties
                    if "type" in value:
                        result[name] = cls._from_dict(value)
                    else:
                        # Nested properties - create DictProperty
                        nested_props = cls.parse(value)
                        result[name] = DictProperty(properties=nested_props)
                # None value means optional string (default type)
                elif value is None:
                    result[name] = StringProperty()
                else:
                    raise ValueError(f"Invalid spec for '{name}'")
            return result

        raise ValueError(f"Invalid spec: {type(spec)}")

    # Type aliases for common type names
    TYPE_ALIASES = {
        "str": "string",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }

    @classmethod
    def _normalize_type(cls, type_name: str) -> str:
        """Normalize type name using aliases."""
        return cls.TYPE_ALIASES.get(type_name, type_name)

    @classmethod
    def _from_type(cls, type_name: str) -> Property:
        """Create property from type name."""
        normalized = cls._normalize_type(type_name)
        try:
            prop_type = PropertyType(normalized)
        except ValueError as e:
            raise ValueError(f"Unknown type: {type_name}") from e

        model_class = cls.TYPE_MODELS[prop_type]
        return model_class(type=prop_type)

    @classmethod
    def _from_dict(cls, spec: dict) -> Property:
        """Create property from full spec - Pydantic validates!"""
        type_name = spec.get("type", "string")
        normalized = cls._normalize_type(type_name)
        prop_type = PropertyType(normalized)
        model_class = cls.TYPE_MODELS[prop_type]
        # Convert type string to enum in the spec
        spec_copy = {**spec, "type": prop_type}
        return model_class(**spec_copy)

    @classmethod
    def _add_nested(
        cls, result: dict[str, Property], path: str, spec: Any
    ) -> None:
        """Handle dot notation: profile.name → nested structure."""
        parts = path.split(".")

        # Navigate/create nested structure
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = DictProperty(properties={})
            elif not isinstance(current[part], DictProperty):
                # Convert existing property to DictProperty
                current[part] = DictProperty(properties={})
            if current[part].properties is None:
                current[part].properties = {}
            current = current[part].properties

        # Add final property
        final = parts[-1]
        if isinstance(spec, str):
            current[final] = cls._from_type(spec)
        else:
            current[final] = cls._from_dict(spec)


# ============================================================================
# Validator: Property Models → Element Validation
# ============================================================================


class PropertyValidator:
    """Validate element values against property models."""

    @staticmethod
    def validate(prop: Property, value: Any) -> tuple[bool, list[str]]:
        """
        Validate a value against a property.

        Returns: (is_valid, error_messages)
        """
        errors = []

        # Type check
        if not PropertyValidator._check_type(prop.type, value):
            errors.append(f"Expected {prop.type.value}, got {type(value).__name__}")
            return (False, errors)

        # Type-specific validation
        if isinstance(prop, StringProperty):
            errors.extend(PropertyValidator._validate_string(prop, value))
        elif isinstance(prop, NumberProperty):
            errors.extend(PropertyValidator._validate_number(prop, value))
        elif isinstance(prop, ListProperty):
            errors.extend(PropertyValidator._validate_list(prop, value))

        return (len(errors) == 0, errors)

    @staticmethod
    def _check_type(prop_type: PropertyType, value: Any) -> bool:
        """Check value type."""
        type_map = {
            PropertyType.STRING: str,
            PropertyType.INT: int,
            PropertyType.FLOAT: (int, float),
            PropertyType.BOOL: bool,
            PropertyType.LIST: list,
            PropertyType.DICT: dict,
        }
        return isinstance(value, type_map[prop_type])

    @staticmethod
    def _validate_string(prop: StringProperty, value: str) -> list[str]:
        """Validate string constraints."""
        errors = []

        if prop.min_length and len(value) < prop.min_length:
            errors.append(f"Too short (min: {prop.min_length})")

        if prop.max_length and len(value) > prop.max_length:
            errors.append(f"Too long (max: {prop.max_length})")

        if prop.pattern and not re.match(prop.pattern, value):
            errors.append("Pattern mismatch")

        if prop.enum and value not in prop.enum:
            errors.append(f"Must be one of: {prop.enum}")

        if prop.format:
            if not PropertyValidator._validate_format(prop.format, value):
                errors.append(f"Invalid {prop.format}")

        return errors

    @staticmethod
    def _validate_number(prop: NumberProperty, value: int | float) -> list[str]:
        """Validate number constraints."""
        errors = []

        if prop.min is not None and value < prop.min:
            errors.append(f"Too small (min: {prop.min})")

        if prop.max is not None and value > prop.max:
            errors.append(f"Too large (max: {prop.max})")

        return errors

    @staticmethod
    def _validate_list(prop: ListProperty, value: list) -> list[str]:
        """Validate list constraints."""
        errors = []

        if prop.min_items and len(value) < prop.min_items:
            errors.append(f"Too few items (min: {prop.min_items})")

        if prop.max_items and len(value) > prop.max_items:
            errors.append(f"Too many items (max: {prop.max_items})")

        if prop.unique and len(value) != len({str(v) for v in value}):
            errors.append("Items must be unique")

        return errors

    @staticmethod
    def _validate_format(format_name: str, value: str) -> bool:
        """Validate common formats."""
        formats = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "uri": r"^https?://[^\s]+$",
            "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        }
        pattern = formats.get(format_name)
        return bool(pattern and re.match(pattern, value, re.IGNORECASE))
