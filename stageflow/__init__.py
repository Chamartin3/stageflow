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

# Public API exports - Core functionality
from .element import Element, DictElement, create_element, create_element_from_config
from .process import Process, ProcessDefinition, ProcessElementEvaluationResult
from .stage import Stage, StageDefinition, StageEvaluationResult, Action
from .gate import Gate, GateDefinition, GateResult
from .lock import Lock, LockDefinition, LockResult, LockType
from .schema.loader import load_process, load_process_data, LoadError

# Optional manager functionality (imported separately)
# from .manager import ProcessManager, ManagerConfig, ProcessRegistry, ProcessEditor

__all__ = [
    # Core functionality
    "Element",
    "Process",
    "Stage",
    "Gate",
    "Lock",
    "load_process",
    "__version__",

    # Data types and results
    "ProcessDefinition",
    "ProcessElementEvaluationResult",
    "StageDefinition",
    "StageEvaluationResult",
    "GateDefinition",
    "GateResult",
    "LockDefinition",
    "LockResult",
    "LockType",
    "Action",

    # Utilities
    "create_element",
    "create_element_from_config",
    "load_process_data",
    "LoadError",
]
