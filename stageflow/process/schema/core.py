"""ItemSchema validation logic for StageFlow."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SchemaError(Exception):
    """Exception raised for schema-related errors."""
    pass


class ValidationError:
    """Represents a validation error for a specific field."""

    def __init__(self, field_path: str, message: str):
        self.field_path = field_path
        self.message = message

    def __str__(self) -> str:
        return f"{self.field_path}: {self.message}"

    def __repr__(self) -> str:
        return f"ValidationError(field_path='{self.field_path}', message='{self.message}')"


class ValidationResult:
    """
    Result of schema validation containing validation status, data, and errors.

    Provides detailed information about validation outcome including
    validated data with defaults applied and field-specific error messages.
    """

    def __init__(self, is_valid: bool, validated_data: dict[str, Any] = None, errors: list[ValidationError] = None):
        self.is_valid = is_valid
        self.validated_data = validated_data if validated_data is not None else ({} if is_valid else None)
        self.errors = errors or []

    @property
    def errors_by_field(self) -> dict[str, list[str]]:
        """Group validation errors by field path."""
        result = {}
        for error in self.errors:
            if error.field_path not in result:
                result[error.field_path] = []
            result[error.field_path].append(error.message)
        return result

    def __str__(self) -> str:
        if self.is_valid:
            return f"ValidationResult(valid=True, fields={len(self.validated_data)})"
        else:
            return f"ValidationResult(valid=False, errors={len(self.errors)})"


class FieldDefinition:
    """
    Definition of a field including type, constraints, and validation rules.

    FieldDefinitions specify the expected type, default value, whether the field
    is required, and any custom validation functions that should be applied.
    """

    def __init__(self, type_: type, default: Any = None, required: bool = True, validators: list[Callable] = None):
        self.type_ = type_
        self.default = default
        self.required = required
        self.validators = validators or []

        # Add compatibility attributes for validation logic
        self.min_value = None
        self.max_value = None
        self.min_length = None
        self.max_length = None
        self.pattern = None
        self.enum = None

    @property
    def type(self) -> str:
        """
        Compatibility property for accessing type_ as type string.

        Returns:
            The field type as a string compatible with validation logic
        """
        # Convert Python type objects to string type names for validation compatibility
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null"
        }
        return type_map.get(self.type_, str(self.type_))

    def validate_value(self, value: Any) -> tuple[bool, Any, list[str]]:
        """
        Validate a value against this field definition.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, validated_value, error_messages)
        """
        errors = []

        # Type validation
        if not isinstance(value, self.type_):
            # Only attempt coercion for compatible numeric types
            if (self.type_ is float and isinstance(value, int)) or \
               (self.type_ is int and isinstance(value, float) and value.is_integer()):
                try:
                    validated_value = self.type_(value)
                except (ValueError, TypeError):
                    errors.append(f"Cannot convert {type(value).__name__} to {self.type_.__name__}")
                    return False, value, errors
            else:
                errors.append(f"Expected {self.type_.__name__}, got {type(value).__name__}")
                return False, value, errors
        else:
            validated_value = value

        # Custom validator functions
        for validator in self.validators:
            try:
                if not validator(validated_value):
                    errors.append("Custom validation failed")
            except Exception as e:
                errors.append(f"Validator error: {str(e)}")

        return len(errors) == 0, validated_value, errors


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


@dataclass
class ItemSchema:
    """
    Schema definition for validating element structure and content.

    ItemSchemas define the expected shape of data elements, including
    required fields, types, defaults, and custom validation rules.
    """

    name: str
    fields: dict[str, FieldDefinition] = field(default_factory=dict)
    # Legacy support for existing API
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

        # If using new fields API, sync with legacy fields for backward compatibility
        if self.fields:
            for field_path, field_def in self.fields.items():
                if field_def.required:
                    self.required_fields.add(field_path)
                else:
                    self.optional_fields.add(field_path)
                    if field_def.default is not None:
                        self.default_values[field_path] = field_def.default

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
        Validate element against this schema (legacy method).

        Args:
            element: Element to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        result = self.validate(element)
        return [str(error) for error in result.errors]

    def validate(self, element: "Element") -> ValidationResult:
        """
        Validate element against this schema.

        Args:
            element: Element to validate

        Returns:
            ValidationResult with status, validated data, and errors
        """
        errors = []
        validated_data = {}

        # First, apply defaults for missing optional fields
        defaults = self.get_defaults()
        for field_path, default_value in defaults.items():
            self._set_nested_value(validated_data, field_path, default_value)

        # Process fields defined with FieldDefinition objects
        for field_path, field_def in self.fields.items():
            if element.has_property(field_path):
                value = element.get_property(field_path)
                is_valid, validated_value, field_errors = field_def.validate_value(value)

                if is_valid:
                    self._set_nested_value(validated_data, field_path, validated_value)
                else:
                    for error_msg in field_errors:
                        errors.append(ValidationError(field_path, error_msg))
            elif field_def.required:
                errors.append(ValidationError(field_path, "Required field missing"))
            elif field_def.default is not None:
                self._set_nested_value(validated_data, field_path, field_def.default)

        # Legacy validation for backward compatibility
        legacy_errors = self._validate_legacy_fields(element)
        errors.extend([ValidationError("legacy", err) for err in legacy_errors])

        # Copy over existing element data that passed validation
        element_data = element.to_dict()
        self._merge_validated_data(validated_data, element_data)

        return ValidationResult(
            is_valid=len(errors) == 0,
            validated_data=validated_data if len(errors) == 0 else None,
            errors=errors
        )

    def _validate_legacy_fields(self, element: "Element") -> list[str]:
        """Validate using legacy field definitions for backward compatibility."""
        errors = []

        # Check required fields
        for field_path in self.required_fields:
            if field_path not in self.fields and not element.has_property(field_path):
                errors.append(f"Required field missing: {field_path}")

        # Check field types
        for field_path, expected_type in self.field_types.items():
            if field_path not in self.fields and element.has_property(field_path):
                value = element.get_property(field_path)
                if not self._validate_type(value, expected_type):
                    errors.append(f"Field '{field_path}' has invalid type: expected {expected_type}")

        # Apply custom validation rules
        for field_path, rules in self.validation_rules.items():
            if field_path not in self.fields and element.has_property(field_path):
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
        # Check FieldDefinition first
        if field_path in self.fields:
            return self.fields[field_path].default
        # Fall back to legacy default values
        return self.default_values.get(field_path)

    def get_defaults(self) -> dict[str, Any]:
        """
        Get all default values from schema.

        Returns:
            Dictionary of field paths to default values
        """
        defaults = {}

        # From FieldDefinition objects
        for field_path, field_def in self.fields.items():
            if not field_def.required and field_def.default is not None:
                defaults[field_path] = field_def.default

        # From legacy default values
        for field_path, default_value in self.default_values.items():
            if field_path not in defaults:
                defaults[field_path] = default_value

        return defaults

    def compose_with(self, other: 'ItemSchema') -> 'ItemSchema':
        """
        Create a new schema by composing this schema with another.

        Args:
            other: Schema to compose with (takes precedence)

        Returns:
            New composed schema
        """
        # Merge fields, with other schema taking precedence
        merged_fields = self.fields.copy()
        merged_fields.update(other.fields)

        # Create new schema and manually set fields to avoid __post_init__ conflicts
        composed = ItemSchema(name=f"{self.name}_composed_with_{other.name}")

        # Set fields directly
        composed.fields = merged_fields

        # Determine final field requirements from the merged FieldDefinitions
        for field_path, field_def in merged_fields.items():
            if field_def.required:
                composed.required_fields.add(field_path)
            else:
                composed.optional_fields.add(field_path)
                if field_def.default is not None:
                    composed.default_values[field_path] = field_def.default

        # Merge remaining legacy fields that aren't in FieldDefinitions
        for field_path in self.required_fields | other.required_fields:
            if field_path not in composed.fields:
                composed.required_fields.add(field_path)

        for field_path in self.optional_fields | other.optional_fields:
            if field_path not in composed.fields and field_path not in composed.required_fields:
                composed.optional_fields.add(field_path)

        # Merge other legacy attributes
        composed.field_types = {**self.field_types, **other.field_types}
        composed.validation_rules = {**self.validation_rules, **other.validation_rules}
        composed.metadata = {**self.metadata, **other.metadata}

        # Merge default values that don't conflict with FieldDefinition defaults
        for field_path, default_value in {**self.default_values, **other.default_values}.items():
            if field_path not in composed.fields:
                composed.default_values[field_path] = default_value

        return composed

    @property
    def field_definitions(self) -> dict[str, FieldDefinition]:
        """
        Compatibility property for accessing fields as field_definitions.

        Returns:
            Dictionary of field paths to FieldDefinition objects
        """
        return self.fields

    def add_field(self, name: str, field_def: FieldDefinition) -> None:
        """
        Add a field to the schema.

        Args:
            name: Field name/path
            field_def: Field definition
        """
        self.fields[name] = field_def

        # Update legacy fields for compatibility
        if field_def.required:
            self.required_fields.add(name)
            self.optional_fields.discard(name)
        else:
            self.optional_fields.add(name)
            self.required_fields.discard(name)
            if field_def.default is not None:
                self.default_values[name] = field_def.default

    def remove_field(self, name: str) -> None:
        """
        Remove a field from the schema.

        Args:
            name: Field name/path to remove

        Raises:
            SchemaError: If field doesn't exist
        """
        if name not in self.fields and name not in self.required_fields and name not in self.optional_fields:
            raise SchemaError(f"Field '{name}' not found in schema")

        # Remove from all field collections
        self.fields.pop(name, None)
        self.required_fields.discard(name)
        self.optional_fields.discard(name)
        self.field_types.pop(name, None)
        self.default_values.pop(name, None)
        self.validation_rules.pop(name, None)

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

    def _set_nested_value(self, data: dict, path: str, value: Any) -> None:
        """Set a value in nested dictionary structure using dot notation."""
        keys = path.split('.')
        current = data

        # Navigate/create nested structure
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _merge_validated_data(self, validated_data: dict, element_data: dict) -> None:
        """Merge element data into validated data, preserving validated values."""
        for key, value in element_data.items():
            if key not in validated_data:
                validated_data[key] = value
            elif isinstance(value, dict) and isinstance(validated_data[key], dict):
                self._merge_validated_data(validated_data[key], value)


# Import here to avoid circular imports
from stageflow.element import Element
