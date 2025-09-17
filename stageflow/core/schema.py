"""ItemSchema validation logic for StageFlow."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ItemSchemaModel(BaseModel):
    """
    Pydantic model for item schema validation.

    Defines the structure and validation rules for schema definitions
    that describe the expected shape of elements.
    """

    required_fields: list[str] = Field(default_factory=list, description="List of required field paths")
    optional_fields: list[str] = Field(default_factory=list, description="List of optional field paths")
    field_types: dict[str, str] = Field(default_factory=dict, description="Type constraints for fields")
    default_values: dict[str, Any] = Field(default_factory=dict, description="Default values for fields")
    validation_rules: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Custom validation rules per field"
    )

    @field_validator("required_fields", "optional_fields", mode="before")
    @classmethod
    def validate_field_lists(cls, v):
        """Ensure field lists contain valid property paths."""
        if not isinstance(v, list):
            return v
        for field_path in v:
            if not isinstance(field_path, str) or not field_path.strip():
                raise ValueError(f"Invalid field path: {field_path}")
        return v

    @field_validator("field_types", mode="before")
    @classmethod
    def validate_field_types(cls, v):
        """Validate field type specifications."""
        if not isinstance(v, dict):
            return v
        valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
        for field_path, field_type in v.items():
            if field_type not in valid_types:
                raise ValueError(f"Invalid type '{field_type}' for field '{field_path}'")
        return v

    model_config = {
        "extra": "forbid",  # Don't allow extra fields
        "validate_assignment": True,
    }


@dataclass(frozen=True)
class ItemSchema:
    """
    Schema definition for validating element structure and content.

    ItemSchemas define the expected shape of data elements, including
    required fields, types, defaults, and custom validation rules.
    """

    name: str
    required_fields: set[str] = field(default_factory=set)
    optional_fields: set[str] = field(default_factory=set)
    field_types: dict[str, str] = field(default_factory=dict)
    default_values: dict[str, Any] = field(default_factory=dict)
    validation_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate schema configuration after initialization."""
        if not self.name:
            raise ValueError("Schema must have a name")

        # Check for overlap between required and optional fields
        overlap = self.required_fields & self.optional_fields
        if overlap:
            raise ValueError(f"Fields cannot be both required and optional: {overlap}")

        # Validate that default values are only provided for optional fields
        invalid_defaults = set(self.default_values.keys()) - self.optional_fields
        if invalid_defaults:
            raise ValueError(f"Default values provided for non-optional fields: {invalid_defaults}")

    @classmethod
    def from_dict(cls, name: str, schema_dict: dict[str, Any]) -> "ItemSchema":
        """
        Create ItemSchema from dictionary representation.

        Args:
            name: Schema name
            schema_dict: Dictionary containing schema definition

        Returns:
            ItemSchema instance
        """
        # Validate input using Pydantic model
        model = ItemSchemaModel(**schema_dict)

        return cls(
            name=name,
            required_fields=set(model.required_fields),
            optional_fields=set(model.optional_fields),
            field_types=model.field_types,
            default_values=model.default_values,
            validation_rules=model.validation_rules,
            metadata=schema_dict.get("metadata", {}),
        )

    def validate_element(self, element: "Element") -> list[str]:
        """
        Validate element against this schema.

        Args:
            element: Element to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        for field_path in self.required_fields:
            if not element.has_property(field_path):
                errors.append(f"Required field missing: {field_path}")

        # Check field types
        for field_path, expected_type in self.field_types.items():
            if element.has_property(field_path):
                value = element.get_property(field_path)
                if not self._validate_type(value, expected_type):
                    errors.append(f"Field '{field_path}' has invalid type: expected {expected_type}")

        # Apply custom validation rules
        for field_path, rules in self.validation_rules.items():
            if element.has_property(field_path):
                value = element.get_property(field_path)
                field_errors = self._validate_custom_rules(field_path, value, rules)
                errors.extend(field_errors)

        return errors

    def get_all_fields(self) -> set[str]:
        """
        Get all fields referenced by this schema.

        Returns:
            Set of all field paths (required + optional)
        """
        return self.required_fields | self.optional_fields

    def is_field_required(self, field_path: str) -> bool:
        """
        Check if a field is required by this schema.

        Args:
            field_path: Field path to check

        Returns:
            True if field is required, False otherwise
        """
        return field_path in self.required_fields

    def get_field_type(self, field_path: str) -> str | None:
        """
        Get expected type for a field.

        Args:
            field_path: Field path to check

        Returns:
            Expected type string, or None if no type constraint
        """
        return self.field_types.get(field_path)

    def get_default_value(self, field_path: str) -> Any:
        """
        Get default value for a field.

        Args:
            field_path: Field path to check

        Returns:
            Default value, or None if no default specified
        """
        return self.default_values.get(field_path)

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate value against expected type.

        Args:
            value: Value to validate
            expected_type: Expected type string

        Returns:
            True if value matches expected type
        """
        if value is None:
            return expected_type == "null"

        type_validators = {
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)),
            "integer": lambda v: isinstance(v, int),
            "boolean": lambda v: isinstance(v, bool),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
            "null": lambda v: v is None,
        }

        validator_func = type_validators.get(expected_type)
        if validator_func:
            return validator_func(value)

        return False

    def _validate_custom_rules(self, field_path: str, value: Any, rules: dict[str, Any]) -> list[str]:
        """
        Apply custom validation rules to field value.

        Args:
            field_path: Field being validated
            value: Field value
            rules: Custom validation rules

        Returns:
            List of validation error messages
        """
        errors = []

        # Minimum/maximum value constraints
        if "min" in rules:
            try:
                if float(value) < float(rules["min"]):
                    errors.append(f"Field '{field_path}' below minimum value {rules['min']}")
            except (ValueError, TypeError):
                errors.append(f"Field '{field_path}' cannot be compared to minimum value")

        if "max" in rules:
            try:
                if float(value) > float(rules["max"]):
                    errors.append(f"Field '{field_path}' above maximum value {rules['max']}")
            except (ValueError, TypeError):
                errors.append(f"Field '{field_path}' cannot be compared to maximum value")

        # String length constraints
        if "min_length" in rules and isinstance(value, str):
            if len(value) < rules["min_length"]:
                errors.append(f"Field '{field_path}' below minimum length {rules['min_length']}")

        if "max_length" in rules and isinstance(value, str):
            if len(value) > rules["max_length"]:
                errors.append(f"Field '{field_path}' above maximum length {rules['max_length']}")

        # Pattern matching
        if "pattern" in rules and isinstance(value, str):
            import re

            try:
                if not re.match(rules["pattern"], value):
                    errors.append(f"Field '{field_path}' does not match required pattern")
            except re.error:
                errors.append(f"Invalid pattern for field '{field_path}'")

        # Enumeration constraints
        if "enum" in rules:
            if value not in rules["enum"]:
                errors.append(f"Field '{field_path}' must be one of: {rules['enum']}")

        return errors


# Import here to avoid circular imports
from stageflow.core.element import Element
