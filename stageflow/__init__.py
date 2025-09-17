"""
StageFlow: A declarative multi-stage validation framework.

StageFlow provides a reusable, non-mutating way to evaluate where a data-bearing
Element stands within a multi-stage Process. The framework enables consistent
decisions, auditability of rules, and safe reuse across domains by expressing
logic as data (schemas) rather than code.

Core Components:
    - Element: Data wrapper for evaluation
    - Process: Multi-stage validation workflow
    - Stage: Individual validation stage with gates
    - Gate: Composed validation rules
    - Lock: Individual validation constraints
    - StatusResult: Evaluation outcome

Example Usage:
    ```python
    from stageflow import Process, Element, load_process

    # Load process from schema
    process = load_process("path/to/process.yaml")

    # Create element wrapper
    element = Element(your_data_dict)

    # Evaluate current state
    result = process.evaluate(element)
    print(f"State: {result.state}")
    print(f"Actions: {result.actions}")
    ```
"""

__version__ = "0.1.0"

# Public API exports
from stageflow.core.element import Element, create_element_from_config
from stageflow.process import Process
from stageflow.process.result import StatusResult
from stageflow.process.schema.loaders.yaml import load_process, load_process_config
from stageflow.models import (
    # Core data contracts
    ElementConfig,
    ElementDataConfig,
    ProcessConfig,
    ResultConfig,
    StageConfig,

    # Specialized data contracts
    ActionConfig,
    ValidationErrorConfig,
    EvaluationMetricsConfig,
    SchemaDefinitionConfig,
    LoaderConfig,

    # System configuration
    ConfigurationManifest,

    # Re-exported from gates module
    LockConfig,
    GateConfig,
    GateSetConfig,
    ValidatorConfig,
)

__all__ = [
    # Core functionality
    "Element",
    "Process",
    "StatusResult",
    "load_process",
    "__version__",

    # Data contracts support
    "create_element_from_config",
    "load_process_config",

    # Core data contracts
    "ElementConfig",
    "ElementDataConfig",
    "ProcessConfig",
    "ResultConfig",
    "StageConfig",

    # Specialized data contracts
    "ActionConfig",
    "ValidationErrorConfig",
    "EvaluationMetricsConfig",
    "SchemaDefinitionConfig",
    "LoaderConfig",

    # System configuration
    "ConfigurationManifest",

    # Gate and lock contracts
    "LockConfig",
    "GateConfig",
    "GateSetConfig",
    "ValidatorConfig",
]
