"""Test fixtures for StageFlow.

This package provides comprehensive test fixtures organized by domain:

- core_models: Fixtures for Element, Lock, Gate, Stage, and Process objects
- sample_data: Realistic sample datasets and edge case data
- process_schemas: YAML/JSON process schema fixtures for various workflow patterns
- mock_objects: Mock objects and test doubles for external dependencies
- parameters: Parameterized fixtures for comprehensive edge case testing

All fixtures are automatically available in test modules through conftest.py imports.
"""

__all__ = [
    "core_models",
    "sample_data",
    "process_schemas",
    "mock_objects",
    "parameters"
]
