"""Schema types for StageFlow initial/final schema lifecycle."""

from enum import StrEnum

from typing_extensions import TypedDict


class SchemaType(StrEnum):
    """Type of schema to generate."""

    INITIAL = "initial"  # Fields only (entry requirements)
    FINAL = "final"  # Initial + actions + gate locks (exit requirements)


class PropertySource(StrEnum):
    """Source of a property in the schema."""

    FIELD = "field"  # Declared in stage fields
    ACTION = "action"  # From action's related_properties
    GATE_LOCK = "gate_lock"  # From gate lock's property_path


class InferredType(StrEnum):
    """JSON Schema types inferred from locks."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


class ExtractedProperty(TypedDict):
    """Property extracted from a lock or action."""

    path: str
    inferred_type: InferredType


class PropertySchema(TypedDict, total=False):
    """Schema definition for a single property."""

    type: InferredType
    required: bool
    default: str | int | float | bool | list | dict | None
    description: str
    source: PropertySource


class StageSchema(TypedDict):
    """Schema for a stage (initial or final)."""

    properties: dict[str, PropertySchema]
    stage_id: str
    stage_name: str
