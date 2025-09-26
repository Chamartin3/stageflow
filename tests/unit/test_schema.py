"""Unit tests for ItemSchema validation."""


import pytest

from stageflow.core.element import DictElement
from stageflow.process.schema.core import (
    FieldDefinition,
    ItemSchema,
    SchemaError,
    ValidationResult,
)


class TestFieldDefinition:
    """Test FieldDefinition class functionality."""

    def test_field_definition_creation(self):
        """Test basic FieldDefinition creation."""
        field = FieldDefinition(type_=str, required=True)
        assert field.type_ is str
        assert field.required is True
        assert field.default is None
        assert field.validators == []

    def test_field_definition_with_default(self):
        """Test FieldDefinition with default value."""
        field = FieldDefinition(type_=str, default="test", required=False)
        assert field.default == "test"
        assert field.required is False

    def test_field_definition_with_validators(self):
        """Test FieldDefinition with custom validators."""
        def length_validator(value):
            return len(str(value)) > 5

        field = FieldDefinition(type_=str, validators=[length_validator])
        assert len(field.validators) == 1

    def test_validate_value_success(self):
        """Test successful value validation."""
        field = FieldDefinition(type_=str, required=True)
        is_valid, validated_value, errors = field.validate_value("test")
        assert is_valid is True
        assert validated_value == "test"
        assert errors == []

    def test_validate_value_type_failure(self):
        """Test value validation with type mismatch."""
        field = FieldDefinition(type_=str, required=True)
        is_valid, validated_value, errors = field.validate_value(123)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_value_with_custom_validator(self):
        """Test value validation with custom validator."""
        def min_length_validator(value):
            return len(str(value)) >= 5

        field = FieldDefinition(type_=str, validators=[min_length_validator])

        # Should pass
        is_valid, _, errors = field.validate_value("hello")
        assert is_valid is True
        assert errors == []

        # Should fail
        is_valid, _, errors = field.validate_value("hi")
        assert is_valid is False
        assert len(errors) > 0


class TestValidationResult:
    """Test ValidationResult class functionality."""

    def test_validation_result_success(self):
        """Test successful validation result."""
        data = {"name": "John", "age": 30}
        result = ValidationResult(is_valid=True, validated_data=data)
        assert result.is_valid is True
        assert result.validated_data == data
        assert result.errors == []

    def test_validation_result_failure(self):
        """Test failed validation result."""
        from stageflow.process.schema.core import ValidationError
        errors = [ValidationError("name", "Name is required")]
        result = ValidationResult(is_valid=False, errors=errors)
        assert result.is_valid is False
        assert result.validated_data is None
        assert len(result.errors) == 1

    def test_errors_by_field(self):
        """Test errors grouped by field."""
        from stageflow.process.schema.core import ValidationError
        errors = [
            ValidationError("name", "Name is required"),
            ValidationError("name", "Name too short"),
            ValidationError("age", "Age must be positive")
        ]
        result = ValidationResult(is_valid=False, errors=errors)
        errors_by_field = result.errors_by_field

        assert "name" in errors_by_field
        assert "age" in errors_by_field
        assert len(errors_by_field["name"]) == 2
        assert len(errors_by_field["age"]) == 1


class TestItemSchemaEnhanced:
    """Test enhanced ItemSchema functionality."""

    def test_schema_with_field_definitions(self):
        """Test schema creation with FieldDefinition objects."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=0)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        assert schema.name == "test_schema"
        assert "name" in schema.fields
        assert "age" in schema.fields

    def test_validate_with_validation_result(self):
        """Test validation returning ValidationResult object."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=25)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        element = DictElement({"name": "John"})

        result = schema.validate(element)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.validated_data["name"] == "John"
        assert result.validated_data["age"] == 25  # Default applied

    def test_get_defaults(self):
        """Test getting default values from schema."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=25),
            "active": FieldDefinition(type_=bool, required=False, default=True)
        }
        schema = ItemSchema(name="test_schema", fields=fields)
        defaults = schema.get_defaults()

        assert defaults["age"] == 25
        assert defaults["active"] is True
        assert "name" not in defaults  # Required field, no default

    def test_compose_with_other_schema(self):
        """Test schema composition with another schema."""
        schema1_fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False, default=25)
        }
        schema1 = ItemSchema(name="base_schema", fields=schema1_fields)

        schema2_fields = {
            "email": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=True)  # Override age
        }
        schema2 = ItemSchema(name="extension_schema", fields=schema2_fields)

        composed = schema1.compose_with(schema2)
        assert "name" in composed.fields
        assert "email" in composed.fields
        assert "age" in composed.fields
        assert composed.fields["age"].required is True  # Should use schema2's definition

    def test_add_field(self):
        """Test adding field to existing schema."""
        schema = ItemSchema(name="test_schema")
        new_field = FieldDefinition(type_=str, required=True)

        schema.add_field("name", new_field)
        assert "name" in schema.fields
        assert schema.fields["name"] == new_field

    def test_remove_field(self):
        """Test removing field from schema."""
        fields = {
            "name": FieldDefinition(type_=str, required=True),
            "age": FieldDefinition(type_=int, required=False)
        }
        schema = ItemSchema(name="test_schema", fields=fields)

        schema.remove_field("age")
        assert "age" not in schema.fields
        assert "name" in schema.fields

    def test_remove_nonexistent_field(self):
        """Test removing non-existent field raises error."""
        schema = ItemSchema(name="test_schema")

        with pytest.raises(SchemaError):
            schema.remove_field("nonexistent")


class TestSchemaValidationEdgeCases:
    """Test edge cases and error scenarios."""

    def test_validation_with_nested_data(self):
        """Test validation with nested object structures."""
        fields = {
            "user.name": FieldDefinition(type_=str, required=True),
            "user.profile.age": FieldDefinition(type_=int, required=False, default=18)
        }
        schema = ItemSchema(name="nested_schema", fields=fields)

        element = DictElement({
            "user": {
                "name": "John",
                "profile": {}
            }
        })

        result = schema.validate(element)
        assert result.is_valid is True
        assert result.validated_data["user"]["name"] == "John"
        assert result.validated_data["user"]["profile"]["age"] == 18

    def test_validation_with_custom_field_validators(self):
        """Test validation with custom field validators."""
        def email_validator(value):
            return "@" in str(value)

        fields = {
            "email": FieldDefinition(type_=str, required=True, validators=[email_validator])
        }
        schema = ItemSchema(name="email_schema", fields=fields)

        # Valid email
        element1 = DictElement({"email": "test@example.com"})
        result1 = schema.validate(element1)
        assert result1.is_valid is True

        # Invalid email
        element2 = DictElement({"email": "invalid-email"})
        result2 = schema.validate(element2)
        assert result2.is_valid is False

