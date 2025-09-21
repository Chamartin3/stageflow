"""Pydantic models for comprehensive StageFlow schema validation.

This module provides comprehensive validation models for StageFlow process definitions
using pydantic v2. These models ensure schema integrity and provide detailed error
messages for malformed configurations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


# Configuration for all models
class BaseStageFlowModel(BaseModel):
    """Base model with common configuration for all StageFlow validation models."""

    model_config = ConfigDict(
        extra="forbid",  # Don't allow extra fields
        validate_assignment=True,  # Validate on assignment
        str_strip_whitespace=True,  # Strip whitespace from strings
        frozen=False,  # Allow field modification for composition
        use_enum_values=True,  # Use enum values in serialization
    )


# Core Validation Models

class FieldDefinitionModel(BaseStageFlowModel):
    """Pydantic model for field definition validation."""

    type: Literal["string", "number", "integer", "boolean", "array", "object", "null"] = Field(
        description="Type constraint for the field"
    )
    default: Any | None = Field(
        default=None,
        description="Default value for the field if not provided"
    )
    required: bool = Field(
        default=True,
        description="Whether the field is required"
    )
    validators: list[str] | None = Field(
        default_factory=list,
        description="List of validator names to apply to the field"
    )

    # Type-specific constraints
    min_value: int | float | None = Field(
        default=None,
        description="Minimum value for numeric fields"
    )
    max_value: int | float | None = Field(
        default=None,
        description="Maximum value for numeric fields"
    )
    min_length: int | None = Field(
        default=None,
        description="Minimum length for string/array fields",
        ge=0
    )
    max_length: int | None = Field(
        default=None,
        description="Maximum length for string/array fields",
        ge=0
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern for string validation"
    )
    enum: list[Any] | None = Field(
        default=None,
        description="List of allowed values"
    )

    @field_validator("pattern")
    @classmethod
    def validate_regex_pattern(cls, v):
        """Validate that pattern is a valid regex."""
        if v is not None:
            import re
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @model_validator(mode="after")
    def validate_constraints(self):
        """Validate field constraints are compatible with type."""
        # Numeric constraints only apply to numeric types
        if self.type not in ("number", "integer") and (self.min_value is not None or self.max_value is not None):
            raise ValueError(f"Numeric constraints not allowed for type '{self.type}'")

        # Length constraints only apply to string/array types
        if self.type not in ("string", "array") and (self.min_length is not None or self.max_length is not None):
            raise ValueError(f"Length constraints not allowed for type '{self.type}'")

        # Pattern only applies to string type
        if self.type != "string" and self.pattern is not None:
            raise ValueError(f"Pattern constraint not allowed for type '{self.type}'")

        # Validate min/max relationship
        if (
            self.min_value is not None and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError(f"min_value ({self.min_value}) cannot be greater than max_value ({self.max_value})")

        if (
            self.min_length is not None and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError(f"min_length ({self.min_length}) cannot be greater than max_length ({self.max_length})")

        return self


class ItemSchemaModel(BaseStageFlowModel):
    """Pydantic model for item schema validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Schema name identifier"
    )
    required_fields: list[str] = Field(
        default_factory=list,
        description="List of required field paths"
    )
    optional_fields: list[str] = Field(
        default_factory=list,
        description="List of optional field paths"
    )
    field_types: dict[str, str] = Field(
        default_factory=dict,
        description="Type constraints for specific fields"
    )
    field_definitions: dict[str, FieldDefinitionModel] = Field(
        default_factory=dict,
        description="Comprehensive field definitions with validation rules"
    )
    default_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Default values for optional fields"
    )
    validation_rules: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom validation rules per field (legacy support)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional schema metadata"
    )

    @field_validator("required_fields", "optional_fields")
    @classmethod
    def validate_field_paths(cls, v):
        """Ensure field paths are valid."""
        if not isinstance(v, list):
            return v

        for field_path in v:
            if not isinstance(field_path, str) or not field_path.strip():
                raise ValueError(f"Invalid field path: {field_path}")
            # Basic dot notation validation
            if field_path.startswith('.') or field_path.endswith('.') or '..' in field_path:
                raise ValueError(f"Invalid field path format: {field_path}")

        return v

    @field_validator("field_types")
    @classmethod
    def validate_field_types(cls, v):
        """Validate field type specifications."""
        if not isinstance(v, dict):
            return v

        valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
        for field_path, field_type in v.items():
            if field_type not in valid_types:
                raise ValueError(f"Invalid type '{field_type}' for field '{field_path}'. Valid types: {valid_types}")

        return v

    @model_validator(mode="after")
    def validate_field_consistency(self):
        """Validate consistency between field definitions."""
        # Check for overlap between required and optional fields
        required_set = set(self.required_fields)
        optional_set = set(self.optional_fields)
        overlap = required_set & optional_set
        if overlap:
            raise ValueError(f"Fields cannot be both required and optional: {sorted(overlap)}")

        # Validate that default values are only for optional/defined fields
        all_optional = optional_set | {name for name, defn in self.field_definitions.items() if not defn.required}
        invalid_defaults = set(self.default_values.keys()) - all_optional
        if invalid_defaults:
            raise ValueError(f"Default values provided for non-optional fields: {sorted(invalid_defaults)}")

        # Validate field_definitions are consistent with legacy fields
        for field_path, field_def in self.field_definitions.items():
            if field_def.required and field_path in optional_set:
                raise ValueError(f"Field '{field_path}' marked as required in definition but listed as optional")
            if not field_def.required and field_path in required_set:
                raise ValueError(f"Field '{field_path}' marked as optional in definition but listed as required")

        return self


class LockModel(BaseStageFlowModel):
    """Pydantic model for lock validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Lock identifier"
    )
    type: str = Field(
        description="Lock type (e.g., EXISTS, EQUALS, REGEX_MATCH, etc.)"
    )
    property: str = Field(
        description="Element property path this lock validates"
    )
    benchmark: Any | None = Field(
        default=None,
        description="Expected value or pattern for comparison locks"
    )
    negate: bool = Field(
        default=False,
        description="Whether to negate the lock result"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional lock metadata"
    )

    @field_validator("property")
    @classmethod
    def validate_property_path(cls, v):
        """Validate property path format."""
        if not v or not v.strip():
            raise ValueError("Property path cannot be empty")

        # Basic dot notation validation
        if v.startswith('.') or v.endswith('.') or '..' in v:
            raise ValueError(f"Invalid property path format: {v}")

        return v.strip()

    @model_validator(mode="after")
    def validate_lock_configuration(self):
        """Validate lock type and benchmark consistency."""
        # Define which lock types require benchmarks
        benchmark_required_types = {
            "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN",
            "GREATER_EQUAL", "LESS_EQUAL", "REGEX_MATCH", "CONTAINS",
            "MIN_LENGTH", "MAX_LENGTH", "IN_LIST", "TYPE_IS"
        }

        benchmark_optional_types = {
            "EXISTS", "NOT_EXISTS", "IS_EMPTY", "NOT_EMPTY",
            "IS_NULL", "NOT_NULL", "IS_NUMERIC", "IS_BOOLEAN"
        }

        if self.type in benchmark_required_types and self.benchmark is None:
            raise ValueError(f"Lock type '{self.type}' requires a benchmark value")

        if self.type in benchmark_optional_types and self.benchmark is not None:
            # Issue a warning but don't fail validation
            pass

        return self


class GateModel(BaseStageFlowModel):
    """Pydantic model for gate validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Gate identifier"
    )
    locks: list[LockModel] = Field(
        min_length=1,
        description="List of locks that comprise this gate"
    )
    logic: Literal["AND", "OR", "XOR", "NAND", "NOR"] = Field(
        default="AND",
        description="Boolean logic for combining lock results"
    )
    target_stage: str | None = Field(
        default=None,
        description="Target stage name for successful gate evaluation"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional gate metadata"
    )

    @field_validator("locks")
    @classmethod
    def validate_unique_lock_names(cls, v):
        """Ensure lock names within a gate are unique."""
        if not v:
            return v

        lock_names = [lock.name for lock in v]
        duplicates = {name for name in lock_names if lock_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate lock names in gate: {sorted(duplicates)}")

        return v


class ActionDefinitionModel(BaseStageFlowModel):
    """Pydantic model for action definition validation."""

    type: Literal[
        "complete_field",
        "validate_data",
        "wait_for_condition",
        "transition_stage",
        "retry_operation",
        "external_action",
        "manual_review"
    ] = Field(
        description="Type of action to be performed"
    )
    description: str = Field(
        min_length=1,
        max_length=500,
        description="Human-readable description of the action"
    )
    priority: Literal["low", "normal", "high", "critical"] = Field(
        default="normal",
        description="Priority level of the action"
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that should be met for this action"
    )
    template_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Variables for template resolution"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional action metadata"
    )

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, v):
        """Ensure description is not just whitespace."""
        if not v.strip():
            raise ValueError("Action description cannot be empty or just whitespace")
        return v


class StageActionDefinitionsModel(BaseStageFlowModel):
    """Pydantic model for stage action definitions validation."""

    fulfilling: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for fulfilling state"
    )
    qualifying: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for qualifying state"
    )
    awaiting: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for awaiting state"
    )
    advancing: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for advancing state"
    )
    regressing: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for regressing state"
    )
    completed: list[ActionDefinitionModel] = Field(
        default_factory=list,
        description="Actions for completed state"
    )


class StageModel(BaseStageFlowModel):
    """Pydantic model for stage validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Stage identifier"
    )
    gates: list[GateModel] = Field(
        default_factory=list,
        description="List of gates for this stage"
    )
    schema: ItemSchemaModel | None = Field(
        default=None,
        description="Expected schema for elements in this stage"
    )
    expected_schema: ItemSchemaModel | None = Field(
        default=None,
        description="Alias for schema field for backward compatibility"
    )
    allow_partial: bool = Field(
        default=False,
        description="Whether partial gate fulfillment is acceptable"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional stage metadata"
    )
    action_definitions: StageActionDefinitionsModel | None = Field(
        default=None,
        description="Declarative action definitions for different evaluation states"
    )

    @field_validator("gates")
    @classmethod
    def validate_unique_gate_names(cls, v):
        """Ensure gate names within a stage are unique."""
        if not v:
            return v

        gate_names = [gate.name for gate in v]
        duplicates = {name for name in gate_names if gate_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate gate names in stage: {sorted(duplicates)}")

        return v

    @model_validator(mode="after")
    def validate_schema_consistency(self):
        """Validate schema field consistency."""
        # Handle expected_schema alias
        if self.expected_schema is not None:
            if self.schema is not None and self.schema != self.expected_schema:
                raise ValueError("Cannot specify both 'schema' and 'expected_schema' with different values")
            if self.schema is None:
                self.schema = self.expected_schema

        return self


class ProcessConfigModel(BaseStageFlowModel):
    """Pydantic model for process configuration validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Process name identifier"
    )
    initial_stage: str | None = Field(
        default=None,
        description="Name of the initial stage"
    )
    final_stage: str | None = Field(
        default=None,
        description="Name of the final stage"
    )
    allow_stage_skipping: bool = Field(
        default=False,
        description="Whether stages can be skipped"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Whether metrics collection is enabled"
    )
    max_batch_size: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum batch size for processing"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional process metadata"
    )


class ProcessModel(BaseStageFlowModel):
    """Pydantic model for complete process validation."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Process name identifier"
    )
    stages: list[StageModel] | dict[str, StageModel] = Field(
        description="Stages in the process (can be list or dictionary)"
    )
    stage_order: list[str] | None = Field(
        default=None,
        description="Explicit stage order (auto-generated if not provided)"
    )
    initial_stage: str | None = Field(
        default=None,
        description="Name of the initial stage"
    )
    final_stage: str | None = Field(
        default=None,
        description="Name of the final stage"
    )
    allow_stage_skipping: bool = Field(
        default=False,
        description="Whether stages can be skipped"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional process metadata"
    )

    @field_validator("stages")
    @classmethod
    def validate_unique_stage_names(cls, v):
        """Ensure stage names are unique within the process."""
        if not v:
            return v

        if isinstance(v, dict):
            # Dictionary format - keys should be stage names
            stage_names = list(v.keys())
            # Also check if stage objects have names that match keys
            for key, stage in v.items():
                if hasattr(stage, 'name') and stage.name and stage.name != key:
                    raise ValueError(f"Stage key '{key}' does not match stage name '{stage.name}'")
        else:
            # List format - extract names from stage objects
            stage_names = [stage.name for stage in v]

        duplicates = {name for name in stage_names if stage_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate stage names in process: {sorted(duplicates)}")

        return v

    @model_validator(mode="after")
    def validate_process_structure(self):
        """Validate process structure and stage references."""
        if not self.stages:
            raise ValueError("Process must contain at least one stage")

        # Get stage names based on format (dict or list)
        if isinstance(self.stages, dict):
            stage_names = set(self.stages.keys())
            stages_list = list(self.stages.values())
            # Set stage names to match keys if they're not already set
            for key, stage in self.stages.items():
                if not hasattr(stage, 'name') or not stage.name:
                    stage.name = key
        else:
            stage_names = {stage.name for stage in self.stages}
            stages_list = self.stages

        # Validate stage_order if provided
        if self.stage_order is not None:
            order_names = set(self.stage_order)

            # Check for missing stages in order
            missing_from_order = stage_names - order_names
            if missing_from_order:
                raise ValueError(f"Stages missing from stage_order: {sorted(missing_from_order)}")

            # Check for extra stages in order
            extra_in_order = order_names - stage_names
            if extra_in_order:
                raise ValueError(f"stage_order contains non-existent stages: {sorted(extra_in_order)}")
        else:
            # Auto-generate stage order
            if isinstance(self.stages, dict):
                self.stage_order = list(self.stages.keys())
            else:
                self.stage_order = [stage.name for stage in self.stages]

        # Validate initial_stage reference
        if self.initial_stage is not None and self.initial_stage not in stage_names:
            raise ValueError(f"initial_stage '{self.initial_stage}' does not exist in stages")

        # Validate final_stage reference
        if self.final_stage is not None and self.final_stage not in stage_names:
            raise ValueError(f"final_stage '{self.final_stage}' does not exist in stages")

        # Validate gate target_stage references
        for stage in stages_list:
            for gate in stage.gates:
                if gate.target_stage is not None and gate.target_stage not in stage_names:
                    raise ValueError(
                        f"Gate '{gate.name}' in stage '{stage.name}' "
                        f"references non-existent target_stage '{gate.target_stage}'"
                    )

        return self

    @computed_field
    @property
    def stage_count(self) -> int:
        """Number of stages in the process."""
        return len(self.stages)

    @computed_field
    @property
    def total_gates(self) -> int:
        """Total number of gates across all stages."""
        stages = self.stages.values() if isinstance(self.stages, dict) else self.stages
        return sum(len(stage.gates) for stage in stages)

    @computed_field
    @property
    def total_locks(self) -> int:
        """Total number of locks across all gates."""
        stages = self.stages.values() if isinstance(self.stages, dict) else self.stages
        return sum(
            len(gate.locks)
            for stage in stages
            for gate in stage.gates
        )


# Top-level schema model that can contain process definitions
class StageFlowSchemaModel(BaseStageFlowModel):
    """Top-level schema model for StageFlow definitions."""

    version: str = Field(
        default="1.0",
        description="Schema version"
    )
    process: ProcessModel = Field(
        description="Process definition"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Top-level metadata"
    )
    created_at: datetime | None = Field(
        default_factory=datetime.now,
        description="Schema creation timestamp"
    )
    created_by: str | None = Field(
        default=None,
        description="Schema creator identifier"
    )
    schema_id: str | UUID | None = Field(
        default_factory=uuid4,
        description="Unique schema identifier"
    )

    @field_validator("version")
    @classmethod
    def validate_version_format(cls, v):
        """Validate version format."""
        import re
        if not re.match(r"^\d+\.\d+$", v):
            raise ValueError(f"Invalid version format: {v}. Expected format: 'major.minor'")
        return v


# Validation utilities and custom validators

class ValidationContext:
    """Context object for validation operations."""

    def __init__(self, strict_mode: bool = True, allow_extra_fields: bool = False):
        self.strict_mode = strict_mode
        self.allow_extra_fields = allow_extra_fields
        self.warnings: list[str] = []
        self.validation_path: list[str] = []

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        path = ".".join(self.validation_path) if self.validation_path else "root"
        self.warnings.append(f"{path}: {message}")

    def push_path(self, segment: str) -> None:
        """Push a path segment onto the validation path."""
        self.validation_path.append(segment)

    def pop_path(self) -> None:
        """Pop the last path segment from the validation path."""
        if self.validation_path:
            self.validation_path.pop()


def validate_stageflow_schema(
    schema_data: dict[str, Any],
    context: ValidationContext | None = None
) -> StageFlowSchemaModel:
    """
    Validate a complete StageFlow schema definition.

    Args:
        schema_data: Dictionary containing the schema definition
        context: Validation context for warnings and configuration

    Returns:
        Validated StageFlowSchemaModel instance

    Raises:
        ValidationError: If validation fails
    """
    if context is None:
        context = ValidationContext()

    try:
        # Handle different input formats
        if "process" not in schema_data:
            # Assume the data itself is a process definition
            schema_data = {"process": schema_data}

        model = StageFlowSchemaModel(**schema_data)

        # Additional business logic validation
        _validate_business_rules(model, context)

        return model

    except Exception as e:
        # Enhance error message with validation context
        path = ".".join(context.validation_path) if context.validation_path else "root"
        raise ValueError(f"Validation failed at {path}: {str(e)}") from e


def validate_process_definition(
    process_data: dict[str, Any],
    context: ValidationContext | None = None
) -> ProcessModel:
    """
    Validate a process definition.

    Args:
        process_data: Dictionary containing the process definition
        context: Validation context for warnings and configuration

    Returns:
        Validated ProcessModel instance

    Raises:
        ValidationError: If validation fails
    """
    if context is None:
        context = ValidationContext()

    context.push_path("process")
    try:
        model = ProcessModel(**process_data)
        _validate_process_business_rules(model, context)
        return model
    finally:
        context.pop_path()


def _validate_business_rules(model: StageFlowSchemaModel, context: ValidationContext) -> None:
    """Validate business rules for the complete schema."""
    _validate_process_business_rules(model.process, context)


def _validate_process_business_rules(process: ProcessModel, context: ValidationContext) -> None:
    """Validate business rules for process definitions."""
    # Check for unreachable stages
    if len(process.stages) > 1:
        for i, current_stage in enumerate(process.stages[1:], 1):
            previous_stage = process.stages[i - 1]

            # Check if there's any way to transition from previous to current
            has_transition = False
            for gate in previous_stage.gates:
                if gate.target_stage == current_stage.name:
                    has_transition = True
                    break

            if not has_transition and context.strict_mode:
                context.add_warning(
                    f"Stage '{current_stage.name}' may be unreachable from '{previous_stage.name}' "
                    f"- no gates target this stage"
                )

    # Validate schema consistency across stages
    for stage in process.stages:
        context.push_path(f"stages.{stage.name}")
        try:
            _validate_stage_business_rules(stage, context)
        finally:
            context.pop_path()


def _validate_stage_business_rules(stage: StageModel, context: ValidationContext) -> None:
    """Validate business rules for individual stages."""
    # Check for gates without target stages (may be terminal)
    terminal_gates = [gate for gate in stage.gates if gate.target_stage is None]
    if len(terminal_gates) > 1:
        context.add_warning(
            f"Stage '{stage.name}' has {len(terminal_gates)} gates without target stages. "
            f"Consider consolidating terminal conditions."
        )

    # Validate gate logic complexity
    for gate in stage.gates:
        if len(gate.locks) > 10:
            context.add_warning(
                f"Gate '{gate.name}' has {len(gate.locks)} locks. "
                f"Consider breaking down complex gates for maintainability."
            )

        # Check for potentially conflicting locks
        property_paths = [lock.property for lock in gate.locks]
        if len(set(property_paths)) != len(property_paths):
            context.add_warning(
                f"Gate '{gate.name}' has multiple locks checking the same properties. "
                f"Verify this is intentional."
            )


# Export all models and utilities
__all__ = [
    "BaseStageFlowModel",
    "FieldDefinitionModel",
    "ItemSchemaModel",
    "LockModel",
    "GateModel",
    "StageModel",
    "ProcessConfigModel",
    "ProcessModel",
    "StageFlowSchemaModel",
    "ValidationContext",
    "validate_stageflow_schema",
    "validate_process_definition",
]
