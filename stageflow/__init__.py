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
from stageflow.core.element import Element
from stageflow.core.process import Process
from stageflow.core.result import StatusResult
from stageflow.loaders.yaml_loader import load_process

__all__ = [
    "Element",
    "Process",
    "StatusResult",
    "load_process",
    "__version__",
]
