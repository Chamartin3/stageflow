"""Runtime validation logic for StageFlow schemas using Pydantic models."""

from typing import Any

from stageflow.element import Element
from stageflow.process.schema.models import FieldDefinitionModel, ItemSchemaModel


class ValidationError:
    """Represents a validation error for a specific field."""

    def __init__(self, field_path: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field_path = field_path
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"{self.field_path}: {self.message}"

    def __repr__(self) -> str:
        return f"ValidationError(field_path='{self.field_path}', message='{self.message}', code='{self.code}')"


class ValidationResult:
    """
    Result of schema validation containing validation status and errors.

    Provides detailed information about validation outcome including
    field-specific error messages and missing fields.
    """

    def __init__(self, is_valid: bool, errors: list[ValidationError] | None = None, missing_fields: list[str] | None = None, invalid_fields: list[str] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []

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
            return "ValidationResult(valid=True)"
        else:
            return f"ValidationResult(valid=False, errors={len(self.errors)}, missing={len(self.missing_fields)}, invalid={len(self.invalid_fields)})"


class ItemSchemaValidator:
    """
    Runtime validator for ItemSchema using Pydantic models.

    Provides comprehensive validation of elements against schema definitions,
    including type checking, constraint validation, and default value handling.
    """

    def validate_element(self, element: Element, schema: ItemSchemaModel) -> ValidationResult:
        """
        Validate an element against an ItemSchema.

        Args:
            element: Element to validate
            schema: ItemSchema model defining validation rules

        Returns:
            ValidationResult with validation status and detailed errors
        """
        errors = []
        missing_fields = []
        invalid_fields = []

        # Check required fields
        for field_path in schema.required_fields:
            if not element.has_property(field_path):
                missing_fields.append(field_path)
                errors.append(ValidationError(field_path, "Required field is missing", "MISSING_REQUIRED"))

        # Check optional fields that are present
        for field_path in schema.optional_fields:
            if element.has_property(field_path):
                value = element.get_property(field_path)
                field_errors = self._validate_field_value(field_path, value, schema)
                if field_errors:
                    invalid_fields.append(field_path)
                    errors.extend(field_errors)

        # Validate field definitions with constraints
        for field_path, field_def in schema.field_definitions.items():
            if element.has_property(field_path):
                value = element.get_property(field_path)
                field_errors = self.validate_field_constraints(value, field_def)
                if field_errors:
                    invalid_fields.append(field_path)
                    errors.extend([ValidationError(field_path, msg, "CONSTRAINT_VIOLATION") for msg in field_errors])
            elif field_def.required:
                if field_path not in missing_fields:
                    missing_fields.append(field_path)
                    errors.append(ValidationError(field_path, "Required field is missing", "MISSING_REQUIRED"))

        # Check legacy field types
        for field_path, expected_type in schema.field_types.items():
            if field_path not in schema.field_definitions and element.has_property(field_path):
                value = element.get_property(field_path)
                if not self._validate_type(value, expected_type):
                    invalid_fields.append(field_path)
                    errors.append(ValidationError(field_path, f"Expected type '{expected_type}'", "TYPE_MISMATCH"))

        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, missing_fields, invalid_fields)

    def get_missing_fields(self, element: Element, schema: ItemSchemaModel) -> list[str]:
        """
        Get list of required fields that are missing from the element.

        Args:
            element: Element to check
            schema: ItemSchema model

        Returns:
            List of missing field paths
        """
        missing = []
        for field_path in schema.required_fields:
            if not element.has_property(field_path):
                missing.append(field_path)

        # Also check field definitions
        for field_path, field_def in schema.field_definitions.items():
            if field_def.required and not element.has_property(field_path):
                if field_path not in missing:
                    missing.append(field_path)

        return missing

    def get_default_values(self, schema: ItemSchemaModel) -> dict[str, Any]:
        """
        Extract default values from schema.

        Args:
            schema: ItemSchema model

        Returns:
            Dictionary mapping field paths to default values
        """
        defaults = dict(schema.default_values)  # Copy legacy defaults

        # Add defaults from field definitions
        for field_path, field_def in schema.field_definitions.items():
            if field_def.default is not None:
                defaults[field_path] = field_def.default

        return defaults

    def validate_field_constraints(self, value: Any, field_def: FieldDefinitionModel) -> list[str]:
        """
        Validate a value against field definition constraints.

        Args:
            value: Value to validate
            field_def: Field definition with constraints

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Type validation
        if not self._validate_field_type(value, field_def.type):
            errors.append(f"Expected type '{field_def.type}', got '{type(value).__name__}'")
            return errors  # Don't continue with other validations if type is wrong

        # Numeric constraints
        if field_def.type in ("number", "integer"):
            if field_def.min_value is not None and value < field_def.min_value:
                errors.append(f"Value {value} is below minimum {field_def.min_value}")
            if field_def.max_value is not None and value > field_def.max_value:
                errors.append(f"Value {value} is above maximum {field_def.max_value}")
            if field_def.type == "integer" and isinstance(value, float) and not value.is_integer():
                errors.append("Integer type must be a whole number")

        # String constraints
        elif field_def.type == "string":
            if field_def.min_length is not None and len(value) < field_def.min_length:
                errors.append(f"String length {len(value)} is below minimum {field_def.min_length}")
            if field_def.max_length is not None and len(value) > field_def.max_length:
                errors.append(f"String length {len(value)} is above maximum {field_def.max_length}")
            if field_def.pattern is not None:
                import re
                try:
                    if not re.match(field_def.pattern, value):
                        errors.append("String does not match required pattern")
                except re.error:
                    errors.append("Invalid regex pattern in field definition")

        # Array constraints
        elif field_def.type == "array":
            if field_def.min_length is not None and len(value) < field_def.min_length:
                errors.append(f"Array length {len(value)} is below minimum {field_def.min_length}")
            if field_def.max_length is not None and len(value) > field_def.max_length:
                errors.append(f"Array length {len(value)} is above maximum {field_def.max_length}")

        # Enum constraint
        if field_def.enum is not None:
            if value not in field_def.enum:
                errors.append(f"Value must be one of: {field_def.enum}")

        return errors

    def _validate_field_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate value type against expected type string.

        Args:
            value: Value to check
            expected_type: Expected type string

        Returns:
            True if type matches
        """
        if value is None:
            return expected_type == "null"

        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return False

        if isinstance(expected_python_type, tuple):
            return isinstance(value, expected_python_type)
        else:
            return isinstance(value, expected_python_type)

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Legacy type validation method.

        Args:
            value: Value to validate
            expected_type: Expected type string

        Returns:
            True if valid
        """
        return self._validate_field_type(value, expected_type)

    def _validate_field_value(self, field_path: str, value: Any, schema: ItemSchemaModel) -> list[ValidationError]:
        """
        Validate a field value against schema constraints.

        Args:
            field_path: Path to the field
            value: Field value
            schema: ItemSchema model

        Returns:
            List of validation errors
        """
        errors = []

        # Check field type from legacy field_types
        if field_path in schema.field_types:
            expected_type = schema.field_types[field_path]
            if not self._validate_type(value, expected_type):
                errors.append(ValidationError(field_path, f"Expected type '{expected_type}'", "TYPE_MISMATCH"))

        # Check validation rules
        if field_path in schema.validation_rules:
            rules = schema.validation_rules[field_path]
            rule_errors = self._validate_custom_rules(field_path, value, rules)
            errors.extend([ValidationError(field_path, msg, "RULE_VIOLATION") for msg in rule_errors])

        return errors

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
                    errors.append(f"Value below minimum {rules['min']}")
            except (ValueError, TypeError):
                errors.append("Cannot compare value to minimum")

        if "max" in rules:
            try:
                if float(value) > float(rules["max"]):
                    errors.append(f"Value above maximum {rules['max']}")
            except (ValueError, TypeError):
                errors.append("Cannot compare value to maximum")

        # String length constraints
        if "min_length" in rules and isinstance(value, str):
            if len(value) < rules["min_length"]:
                errors.append(f"Length below minimum {rules['min_length']}")

        if "max_length" in rules and isinstance(value, str):
            if len(value) > rules["max_length"]:
                errors.append(f"Length above maximum {rules['max_length']}")

        # Pattern matching
        if "pattern" in rules and isinstance(value, str):
            import re
            try:
                if not re.match(rules["pattern"], value):
                    errors.append("Does not match required pattern")
            except re.error:
                errors.append("Invalid pattern")

        # Enumeration constraints
        if "enum" in rules:
            if value not in rules["enum"]:
                errors.append(f"Must be one of: {rules['enum']}")

        return errors
