"""Unit tests for ItemSchemaValidator."""

from stageflow.element import DictElement
from stageflow.process.schema.models import FieldDefinitionModel, ItemSchemaModel
from stageflow.process.schema.validation import (
    ItemSchemaValidator,
    ValidationError,
    ValidationResult,
)


class TestValidationError:
    """Test ValidationError class."""

    def test_validation_error_creation(self):
        """Test ValidationError creation and string representation."""
        error = ValidationError("field.path", "Test error message", "TEST_CODE")
        assert error.field_path == "field.path"
        assert error.message == "Test error message"
        assert error.code == "TEST_CODE"
        assert str(error) == "field.path: Test error message"

    def test_validation_error_repr(self):
        """Test ValidationError repr."""
        error = ValidationError("field", "msg", "code")
        assert "ValidationError" in repr(error)
        assert "field" in repr(error)
        assert "msg" in repr(error)


class TestValidationResult:
    """Test ValidationResult class."""

    def test_valid_result(self):
        """Test valid ValidationResult."""
        result = ValidationResult(True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.missing_fields == []
        assert result.invalid_fields == []

    def test_invalid_result(self):
        """Test invalid ValidationResult."""
        errors = [ValidationError("field1", "error1"), ValidationError("field2", "error2")]
        result = ValidationResult(False, errors, ["field1"], ["field2"])
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.missing_fields == ["field1"]
        assert result.invalid_fields == ["field2"]

    def test_errors_by_field(self):
        """Test errors_by_field property."""
        errors = [
            ValidationError("field1", "error1"),
            ValidationError("field1", "error2"),
            ValidationError("field2", "error3")
        ]
        result = ValidationResult(False, errors)
        errors_by_field = result.errors_by_field
        assert "field1" in errors_by_field
        assert "field2" in errors_by_field
        assert len(errors_by_field["field1"]) == 2
        assert len(errors_by_field["field2"]) == 1

    def test_result_string_representation(self):
        """Test string representation of ValidationResult."""
        valid_result = ValidationResult(True)
        assert "ValidationResult(valid=True)" == str(valid_result)

        invalid_result = ValidationResult(False, [ValidationError("f", "e")], ["m"], ["i"])
        assert "ValidationResult(valid=False, errors=1, missing=1, invalid=1)" == str(invalid_result)


class TestItemSchemaValidator:
    """Test ItemSchemaValidator class."""

    def setup_method(self):
        """Set up validator for each test."""
        self.validator = ItemSchemaValidator()

    def test_validate_element_valid(self):
        """Test validation of valid element."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["name", "email"],
            optional_fields=["age"],
            field_types={"name": "string", "email": "string", "age": "integer"}
        )

        element = DictElement({
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        })

        result = self.validator.validate_element(element, schema)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.missing_fields) == 0
        assert len(result.invalid_fields) == 0

    def test_validate_element_missing_required(self):
        """Test validation with missing required fields."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["name", "email"],
            optional_fields=["age"]
        )

        element = DictElement({
            "name": "John Doe"
            # email is missing
        })

        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.missing_fields == ["email"]
        assert result.invalid_fields == []
        assert "email" in result.errors[0].field_path
        assert "missing" in result.errors[0].message.lower()

    def test_validate_element_invalid_type(self):
        """Test validation with invalid field type."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["name"],
            field_types={"name": "string"}
        )

        element = DictElement({
            "name": 123  # Should be string
        })

        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.invalid_fields == ["name"]
        assert "type" in result.errors[0].message.lower()

    def test_validate_element_with_field_definitions(self):
        """Test validation using field definitions."""
        field_def = FieldDefinitionModel(
            type="string",
            required=True,
            min_length=2,
            max_length=10
        )

        schema = ItemSchemaModel(
            name="test_schema",
            field_definitions={"name": field_def}
        )

        # Valid element
        element = DictElement({"name": "John"})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is True

        # Too short
        element = DictElement({"name": "J"})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert "below minimum" in str(result.errors[0])

        # Too long
        element = DictElement({"name": "ThisIsWayTooLong"})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert "above maximum" in str(result.errors[0])

    def test_get_missing_fields(self):
        """Test get_missing_fields method."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["name", "email"],
            optional_fields=["age"]
        )

        element = DictElement({"name": "John"})
        missing = self.validator.get_missing_fields(element, schema)
        assert missing == ["email"]

        element = DictElement({"name": "John", "email": "john@example.com"})
        missing = self.validator.get_missing_fields(element, schema)
        assert missing == []

    def test_get_default_values(self):
        """Test get_default_values method."""
        schema = ItemSchemaModel(
            name="test_schema",
            optional_fields=["age", "city"],
            default_values={"age": 18, "city": "Unknown"},
            field_definitions={
                "score": FieldDefinitionModel(type="number", required=False, default=0.0)
            }
        )

        defaults = self.validator.get_default_values(schema)
        assert defaults["age"] == 18
        assert defaults["city"] == "Unknown"
        assert defaults["score"] == 0.0

    def test_validate_field_constraints_string(self):
        """Test string field constraints."""
        field_def = FieldDefinitionModel(
            type="string",
            min_length=2,
            max_length=10,
            pattern=r"^[A-Z][a-z]+$"
        )

        # Valid
        errors = self.validator.validate_field_constraints("John", field_def)
        assert errors == []

        # Too short
        errors = self.validator.validate_field_constraints("J", field_def)
        assert len(errors) == 2  # Both length and pattern fail
        assert any("below minimum" in err for err in errors)
        assert any("pattern" in err for err in errors)

        # Invalid pattern
        errors = self.validator.validate_field_constraints("john", field_def)
        assert len(errors) == 1
        assert "pattern" in errors[0]

    def test_validate_field_constraints_number(self):
        """Test number field constraints."""
        field_def = FieldDefinitionModel(
            type="number",
            min_value=0.0,
            max_value=100.0
        )

        # Valid
        errors = self.validator.validate_field_constraints(50.5, field_def)
        assert errors == []

        # Too low
        errors = self.validator.validate_field_constraints(-5, field_def)
        assert len(errors) == 1
        assert "below minimum" in errors[0]

        # Too high
        errors = self.validator.validate_field_constraints(150, field_def)
        assert len(errors) == 1
        assert "above maximum" in errors[0]

    def test_validate_field_constraints_integer(self):
        """Test integer field constraints."""
        field_def = FieldDefinitionModel(
            type="integer",
            min_value=1,
            max_value=10
        )

        # Valid
        errors = self.validator.validate_field_constraints(5, field_def)
        assert errors == []

        # Float when integer expected
        errors = self.validator.validate_field_constraints(5.5, field_def)
        assert len(errors) == 1
        assert "Expected type 'integer'" in errors[0]

    def test_validate_field_constraints_array(self):
        """Test array field constraints."""
        field_def = FieldDefinitionModel(
            type="array",
            min_length=1,
            max_length=5
        )

        # Valid
        errors = self.validator.validate_field_constraints([1, 2, 3], field_def)
        assert errors == []

        # Too short
        errors = self.validator.validate_field_constraints([], field_def)
        assert len(errors) == 1
        assert "below minimum" in errors[0]

        # Too long
        errors = self.validator.validate_field_constraints(list(range(10)), field_def)
        assert len(errors) == 1
        assert "above maximum" in errors[0]

    def test_validate_field_constraints_enum(self):
        """Test enum constraints."""
        field_def = FieldDefinitionModel(
            type="string",
            enum=["red", "green", "blue"]
        )

        # Valid
        errors = self.validator.validate_field_constraints("red", field_def)
        assert errors == []

        # Invalid
        errors = self.validator.validate_field_constraints("yellow", field_def)
        assert len(errors) == 1
        assert "must be one of" in errors[0]

    def test_validate_field_constraints_wrong_type(self):
        """Test constraints validation with wrong type."""
        field_def = FieldDefinitionModel(
            type="string",
            min_length=5
        )

        # Pass integer to string field
        errors = self.validator.validate_field_constraints(123, field_def)
        assert len(errors) == 1
        assert "Expected type 'string'" in errors[0]

    def test_validate_field_constraints_null_type(self):
        """Test null type validation."""
        field_def = FieldDefinitionModel(type="null")

        # Valid null
        errors = self.validator.validate_field_constraints(None, field_def)
        assert errors == []

        # Invalid non-null
        errors = self.validator.validate_field_constraints("not null", field_def)
        assert len(errors) == 1
        assert "Expected type 'null'" in errors[0]

    def test_custom_validation_rules(self):
        """Test custom validation rules from legacy validation_rules."""
        schema = ItemSchemaModel(
            name="test_schema",
            required_fields=["score"],
            validation_rules={
                "score": {"min": 0, "max": 100}
            }
        )

        element = DictElement({"score": 50})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is True

        element = DictElement({"score": 150})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert "above maximum" in str(result.errors[0])

    def test_complex_nested_validation(self):
        """Test validation with complex nested schema."""
        field_def_name = FieldDefinitionModel(
            type="string",
            required=True,
            min_length=1
        )
        field_def_age = FieldDefinitionModel(
            type="integer",
            required=False,
            min_value=0,
            max_value=150,
            default=25
        )

        schema = ItemSchemaModel(
            name="person_schema",
            required_fields=["name"],
            optional_fields=["age", "email"],
            field_types={"email": "string"},
            default_values={"email": "unknown@example.com"},
            field_definitions={
                "name": field_def_name,
                "age": field_def_age
            }
        )

        # Valid element
        element = DictElement({
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com"
        })
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is True

        # Missing required field
        element = DictElement({"age": 30})
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert "name" in result.missing_fields

        # Invalid age
        element = DictElement({
            "name": "Bob",
            "age": 200  # Too old
        })
        result = self.validator.validate_element(element, schema)
        assert result.is_valid is False
        assert "age" in result.invalid_fields

        # Check defaults
        defaults = self.validator.get_default_values(schema)
        assert defaults["age"] == 25
        assert defaults["email"] == "unknown@example.com"
