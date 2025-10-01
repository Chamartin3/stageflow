"""
Submodule imports for the StageFlow process module.

This module handles the imports for process submodules to avoid
complex lazy loading logic in __init__.py.
"""

def get_submodule(name: str):
    """Get a submodule by name with lazy loading."""
    if name == "schema":
        from . import schema
        return schema
    elif name == "validation":
        from . import validation
        return validation
    elif name == "extras":
        from . import extras
        return extras
    else:
        raise AttributeError(f"module 'stageflow.process' has no attribute '{name}'")
