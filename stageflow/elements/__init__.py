"""
Elements module for StageFlow - Element and Element Schema functionality.

This module provides:
- Element class and factory functions for data access
- Element schema generation (JSON Schema) from Process definitions

Separation of concerns:
- stageflow.schema: Process schema loading
- stageflow.elements: Element functionality and element schema generation
"""

from stageflow.elements.element import (
    DictElement,
    Element,
    ElementConfig,
    ElementDataConfig,
    create_element,
    create_element_from_config,
)
from stageflow.elements.schema import (
    RequiredFieldAnalyzer,
    SchemaGenerator,
)

__all__ = [
    # Element classes and types
    "Element",
    "DictElement",
    "ElementConfig",
    "ElementDataConfig",
    # Element factory functions
    "create_element",
    "create_element_from_config",
    # Element schema generation
    "SchemaGenerator",
    "RequiredFieldAnalyzer",
]
