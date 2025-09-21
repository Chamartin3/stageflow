"""Central data models for StageFlow using TypedDict contracts.

This module provides all TypedDict data contracts for StageFlow, establishing
clear data communication interfaces between components. These contracts separate
schema validation from object instantiation and provide type safety throughout
the framework.

The models in this module represent the canonical data interfaces for:
- Process configurations and definitions
- Element data and metadata structures
- Evaluation results and status information
- Integration with specialized subsystems (gates, stages, etc.)

All TypedDict contracts follow these principles:
- Required fields are explicit, optional fields use NotRequired
- Comprehensive type annotations for all fields
- Clear documentation for each contract
- Consistent naming and structure conventions
- Integration with existing specialized modules

Example Usage:
    Basic data contract usage:
        >>> from stageflow.models import ProcessConfig, ElementConfig
        >>> process_config: ProcessConfig = {
        ...     "name": "user_validation",
        ...     "stages": [...]
        ... }
        >>> element_config: ElementConfig = {
        ...     "data": {"user": "john", "email": "john@example.com"},
        ...     "metadata": {"source": "api"}
        ... }

    Integration with loaders:
        >>> from stageflow.models import ProcessConfig
        >>> from stageflow.loaders import load_yaml
        >>> config: ProcessConfig = load_yaml("process.yaml")

    Type-safe object construction:
        >>> from stageflow.models import ProcessConfig
        >>> from stageflow.process import Process
        >>> config: ProcessConfig = {...}
        >>> process = Process.from_config(config)
"""

from typing import Any, NotRequired, TypedDict, Union
from typing_extensions import TypedDict as TypedDictExt

# Import specialized data contracts from modules
from stageflow.gates import (
    LockConfig,
    GateConfig,
    GateSetConfig,
    ValidatorConfig,
    AnyLockConfig,
    AnyGateConfig,
)

# Import stage-related contracts when available
# Note: StageConfig will be imported from stages module when Task 036 is complete
# For now, we'll define it locally and can refactor later


# Core Element Data Contracts
class ElementDataConfig(TypedDict):
    """Configuration interface for element data structures.

    Defines the required and optional fields for element data that will be
    evaluated against process stages. This contract ensures consistent
    data structure expectations across the framework.
    """

    # Core data payload - the actual data being validated
    # This is intentionally flexible to support various data formats
    data: dict[str, Any]  # Primary data payload for evaluation

    # Optional metadata and configuration
    metadata: NotRequired[dict[str, Any]]  # Additional metadata about the data
    source: NotRequired[str]  # Source identifier for the data
    timestamp: NotRequired[str]  # ISO timestamp of data creation/update
    version: NotRequired[str]  # Version identifier for the data

    # Data integrity and validation hints
    checksum: NotRequired[str]  # Data integrity checksum
    schema_version: NotRequired[str]  # Expected schema version
    validation_context: NotRequired[dict[str, Any]]  # Context for validation

    # Element behavior configuration
    immutable: NotRequired[bool]  # Whether element data should be treated as immutable
    allow_partial_access: NotRequired[bool]  # Whether partial property access is allowed
    property_access_mode: NotRequired[str]  # Property access strategy ("strict" | "lenient")


class ElementConfig(TypedDict):
    """Configuration interface for Element creation and behavior.

    Comprehensive contract for creating Element instances with proper
    data structures, access patterns, and behavioral configuration.
    """

    # Core element configuration
    data: dict[str, Any]  # Element data payload

    # Element identification and metadata
    element_id: NotRequired[str]  # Unique identifier for the element
    name: NotRequired[str]  # Human-readable name for the element
    description: NotRequired[str]  # Description of the element
    metadata: NotRequired[dict[str, Any]]  # Additional element metadata

    # Data access and behavior configuration
    property_resolver: NotRequired[str]  # Property resolution strategy
    access_mode: NotRequired[str]  # Access mode ("readonly" | "copy" | "reference")
    path_separator: NotRequired[str]  # Custom path separator (default: ".")
    allow_missing_properties: NotRequired[bool]  # Whether missing properties are allowed

    # Validation and integrity
    validate_on_access: NotRequired[bool]  # Whether to validate property access
    schema_hints: NotRequired[dict[str, Any]]  # Hints for property validation
    type_coercion: NotRequired[bool]  # Whether to enable automatic type coercion

    # Performance and caching
    enable_caching: NotRequired[bool]  # Whether to cache property resolutions
    cache_size_limit: NotRequired[int]  # Maximum cache size
    eager_load_paths: NotRequired[list[str]]  # Paths to eagerly resolve and cache


# Process Configuration Data Contracts
class ProcessMetadataConfig(TypedDict):
    """Configuration interface for process metadata."""

    # Basic identification
    description: NotRequired[str]  # Human-readable process description
    version: NotRequired[str]  # Process definition version
    author: NotRequired[str]  # Process definition author
    created_at: NotRequired[str]  # ISO timestamp of creation
    updated_at: NotRequired[str]  # ISO timestamp of last update

    # Process behavior configuration
    timeout_ms: NotRequired[int]  # Maximum evaluation time in milliseconds
    max_iterations: NotRequired[int]  # Maximum evaluation iterations
    retry_policy: NotRequired[dict[str, Any]]  # Retry configuration

    # Documentation and categorization
    tags: NotRequired[list[str]]  # Process categorization tags
    documentation_url: NotRequired[str]  # Link to process documentation
    examples: NotRequired[list[dict[str, Any]]]  # Example configurations

    # Integration metadata
    external_dependencies: NotRequired[list[str]]  # External system dependencies
    api_version: NotRequired[str]  # API version compatibility
    feature_flags: NotRequired[dict[str, bool]]  # Feature flag configuration


# Forward declaration for StageConfig - will be updated when stages module is complete
class StageConfig(TypedDict):
    """Configuration interface for stage definitions.

    Note: This is a placeholder definition. When Task 036 (Stages Module Creation)
    is complete, this should be imported from the stages module instead.
    """

    # Core stage identification
    name: str  # Stage name identifier

    # Stage validation components
    gates: NotRequired[list[GateConfig]]  # Gates for this stage
    schema: NotRequired[dict[str, Any]]  # Expected data schema

    # Stage behavior
    allow_partial: NotRequired[bool]  # Whether partial fulfillment is allowed
    timeout_ms: NotRequired[int]  # Stage evaluation timeout

    # Metadata and documentation
    description: NotRequired[str]  # Human-readable description
    metadata: NotRequired[dict[str, Any]]  # Additional stage metadata

    # Action definitions for different states
    action_definitions: NotRequired[dict[str, list[dict[str, Any]]]]  # State-based actions


class ProcessConfig(TypedDict):
    """Configuration interface for Process creation and behavior.

    Comprehensive contract for defining multi-stage validation processes
    with proper stage ordering, transition logic, and behavioral configuration.
    """

    # Core process identification
    name: str  # Process name identifier

    # Process structure and flow
    stages: Union[list[StageConfig], dict[str, StageConfig]]  # Process stages
    stage_order: NotRequired[list[str]]  # Explicit stage order
    initial_stage: NotRequired[str]  # Name of initial stage
    final_stage: NotRequired[str]  # Name of final stage

    # Process behavior configuration
    allow_stage_skipping: NotRequired[bool]  # Whether stages can be skipped
    regression_detection: NotRequired[bool]  # Whether regression detection is enabled
    parallel_evaluation: NotRequired[bool]  # Whether parallel evaluation is allowed
    strict_ordering: NotRequired[bool]  # Whether stage order must be enforced

    # Evaluation and performance settings
    max_evaluation_depth: NotRequired[int]  # Maximum evaluation recursion depth
    evaluation_timeout_ms: NotRequired[int]  # Global evaluation timeout
    enable_metrics: NotRequired[bool]  # Whether metrics collection is enabled
    enable_caching: NotRequired[bool]  # Whether result caching is enabled

    # Process metadata and documentation
    metadata: NotRequired[ProcessMetadataConfig]  # Process metadata
    description: NotRequired[str]  # Short process description
    version: NotRequired[str]  # Process version

    # Advanced configuration
    error_handling: NotRequired[dict[str, Any]]  # Error handling configuration
    logging_config: NotRequired[dict[str, Any]]  # Logging configuration
    hooks: NotRequired[dict[str, list[str]]]  # Process lifecycle hooks


# Evaluation Result Data Contracts
class ActionConfig(TypedDict):
    """Configuration interface for action definitions."""

    # Core action definition
    type: str  # Action type identifier
    description: str  # Human-readable description

    # Action execution parameters
    priority: NotRequired[str]  # Action priority ("low" | "normal" | "high" | "critical")
    conditions: NotRequired[list[str]]  # Conditions for action execution
    parameters: NotRequired[dict[str, Any]]  # Action-specific parameters

    # Action metadata
    metadata: NotRequired[dict[str, Any]]  # Additional action metadata
    timeout_ms: NotRequired[int]  # Action execution timeout
    retry_policy: NotRequired[dict[str, Any]]  # Retry configuration for action

    # Template and interpolation
    template_vars: NotRequired[dict[str, str]]  # Variables for template resolution
    interpolation_mode: NotRequired[str]  # Template interpolation mode


class ValidationErrorConfig(TypedDict):
    """Configuration interface for validation error information."""

    # Core error identification
    code: str  # Error code identifier
    message: str  # Human-readable error message

    # Error location and context
    property_path: NotRequired[str]  # Property path where error occurred
    stage_name: NotRequired[str]  # Stage where error occurred
    gate_name: NotRequired[str]  # Gate where error occurred
    lock_name: NotRequired[str]  # Lock where error occurred

    # Error details and debugging
    expected_value: NotRequired[Any]  # Expected value for validation
    actual_value: NotRequired[Any]  # Actual value that failed validation
    validation_rule: NotRequired[str]  # Validation rule that failed
    context: NotRequired[dict[str, Any]]  # Additional error context

    # Error metadata
    severity: NotRequired[str]  # Error severity ("info" | "warning" | "error" | "critical")
    category: NotRequired[str]  # Error category
    timestamp: NotRequired[str]  # ISO timestamp of error occurrence
    metadata: NotRequired[dict[str, Any]]  # Additional error metadata


class EvaluationMetricsConfig(TypedDict):
    """Configuration interface for evaluation performance metrics."""

    # Timing metrics
    total_duration_ms: NotRequired[float]  # Total evaluation duration
    stage_durations_ms: NotRequired[dict[str, float]]  # Per-stage durations
    gate_durations_ms: NotRequired[dict[str, float]]  # Per-gate durations

    # Evaluation statistics
    stages_evaluated: NotRequired[int]  # Number of stages evaluated
    gates_evaluated: NotRequired[int]  # Number of gates evaluated
    locks_evaluated: NotRequired[int]  # Number of locks evaluated

    # Success/failure metrics
    successful_evaluations: NotRequired[int]  # Number of successful evaluations
    failed_evaluations: NotRequired[int]  # Number of failed evaluations
    skipped_evaluations: NotRequired[int]  # Number of skipped evaluations

    # Resource usage
    memory_usage_mb: NotRequired[float]  # Peak memory usage
    cache_hits: NotRequired[int]  # Number of cache hits
    cache_misses: NotRequired[int]  # Number of cache misses


class ResultConfig(TypedDict):
    """Configuration interface for evaluation result data.

    Comprehensive contract for evaluation outcomes including state information,
    actions, errors, and performance metrics. Used to communicate evaluation
    results between components with full type safety.
    """

    # Core evaluation outcome
    state: str  # Current evaluation state
    stage_name: str  # Name of current stage

    # Evaluation success/failure
    passed: bool  # Whether evaluation passed overall
    completed: bool  # Whether evaluation completed (vs. partial/interrupted)

    # Proposed transitions and actions
    proposed_stage: NotRequired[str]  # Suggested next stage
    actions: NotRequired[list[ActionConfig]]  # Recommended actions
    next_states: NotRequired[list[str]]  # Possible next states

    # Detailed evaluation results
    stage_results: NotRequired[dict[str, dict[str, Any]]]  # Per-stage results
    gate_results: NotRequired[dict[str, dict[str, Any]]]  # Per-gate results
    lock_results: NotRequired[dict[str, dict[str, Any]]]  # Per-lock results

    # Errors and warnings
    errors: NotRequired[list[ValidationErrorConfig]]  # Validation errors
    warnings: NotRequired[list[ValidationErrorConfig]]  # Validation warnings

    # Evaluation metadata and context
    evaluation_id: NotRequired[str]  # Unique evaluation identifier
    timestamp: NotRequired[str]  # ISO timestamp of evaluation
    context: NotRequired[dict[str, Any]]  # Evaluation context
    metadata: NotRequired[dict[str, Any]]  # Additional result metadata

    # Performance and debugging information
    metrics: NotRequired[EvaluationMetricsConfig]  # Performance metrics
    debug_info: NotRequired[dict[str, Any]]  # Debug information
    trace: NotRequired[list[dict[str, Any]]]  # Evaluation trace


# Schema and Validation Data Contracts
class SchemaDefinitionConfig(TypedDict):
    """Configuration interface for schema definitions."""

    # Core schema identification
    name: str  # Schema name identifier
    version: NotRequired[str]  # Schema version

    # Field definitions
    required_fields: NotRequired[list[str]]  # Required field paths
    optional_fields: NotRequired[list[str]]  # Optional field paths
    field_types: NotRequired[dict[str, str]]  # Field type constraints

    # Advanced schema configuration
    field_definitions: NotRequired[dict[str, dict[str, Any]]]  # Comprehensive field definitions
    default_values: NotRequired[dict[str, Any]]  # Default values for fields
    validation_rules: NotRequired[dict[str, dict[str, Any]]]  # Custom validation rules

    # Schema metadata
    description: NotRequired[str]  # Human-readable description
    metadata: NotRequired[dict[str, Any]]  # Additional schema metadata


# Loader Configuration Data Contracts
class LoaderConfig(TypedDict):
    """Configuration interface for schema loaders."""

    # Core loader configuration
    format: str  # Loader format ("yaml" | "json" | "xml" | etc.)

    # File and source configuration
    file_path: NotRequired[str]  # Source file path
    content: NotRequired[str]  # Direct content string
    encoding: NotRequired[str]  # File encoding (default: "utf-8")

    # Loader behavior
    validate_schema: NotRequired[bool]  # Whether to validate during loading
    strict_mode: NotRequired[bool]  # Whether to use strict validation
    allow_extra_fields: NotRequired[bool]  # Whether extra fields are allowed

    # Include and reference resolution
    resolve_includes: NotRequired[bool]  # Whether to resolve include directives
    include_base_path: NotRequired[str]  # Base path for include resolution
    max_include_depth: NotRequired[int]  # Maximum include depth

    # Error handling and reporting
    continue_on_error: NotRequired[bool]  # Whether to continue on validation errors
    collect_warnings: NotRequired[bool]  # Whether to collect validation warnings
    detailed_errors: NotRequired[bool]  # Whether to provide detailed error information

    # Performance configuration
    enable_caching: NotRequired[bool]  # Whether to enable loader caching
    cache_size_limit: NotRequired[int]  # Maximum cache size

    # Metadata
    metadata: NotRequired[dict[str, Any]]  # Additional loader metadata


# Configuration Integration and Utility Types
class ConfigurationManifest(TypedDict):
    """Configuration manifest for complete StageFlow system setup."""

    # Core system components
    process: ProcessConfig  # Main process configuration
    elements: NotRequired[list[ElementConfig]]  # Element configurations
    loaders: NotRequired[dict[str, LoaderConfig]]  # Loader configurations

    # System-wide settings
    global_settings: NotRequired[dict[str, Any]]  # Global configuration settings
    feature_flags: NotRequired[dict[str, bool]]  # Feature flag configuration
    environment: NotRequired[str]  # Environment identifier

    # Integration configuration
    external_systems: NotRequired[dict[str, dict[str, Any]]]  # External system configs
    api_endpoints: NotRequired[dict[str, str]]  # API endpoint configurations

    # Security and compliance
    security_config: NotRequired[dict[str, Any]]  # Security configuration
    compliance_rules: NotRequired[list[dict[str, Any]]]  # Compliance rules

    # Metadata and versioning
    manifest_version: NotRequired[str]  # Manifest version
    created_at: NotRequired[str]  # ISO timestamp of creation
    metadata: NotRequired[dict[str, Any]]  # Additional manifest metadata


# Type aliases for convenience and backward compatibility
AnyConfig = Union[ProcessConfig, ElementConfig, ResultConfig, SchemaDefinitionConfig]
AnyDataContract = Union[ElementDataConfig, ProcessMetadataConfig, ActionConfig, ValidationErrorConfig]

# Re-export gate and lock contracts for convenience
__all__ = [
    # Core data contracts
    "ElementDataConfig",
    "ElementConfig",
    "ProcessConfig",
    "ProcessMetadataConfig",
    "StageConfig",
    "ResultConfig",

    # Specialized data contracts
    "ActionConfig",
    "ValidationErrorConfig",
    "EvaluationMetricsConfig",
    "SchemaDefinitionConfig",
    "LoaderConfig",

    # System configuration
    "ConfigurationManifest",

    # Type aliases
    "AnyConfig",
    "AnyDataContract",

    # Re-exported from gates module
    "LockConfig",
    "GateConfig",
    "GateSetConfig",
    "ValidatorConfig",
    "AnyLockConfig",
    "AnyGateConfig",
]

# Module metadata
__version__ = "1.0.0"
__author__ = "StageFlow Team"
__description__ = "Central data models and TypedDict contracts for StageFlow"