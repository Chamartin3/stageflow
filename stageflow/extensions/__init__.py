"""
Extension system for StageFlow.

This module provides the extension framework including custom lock
registries for extending validation capabilities.
"""

from stageflow.extensions.registry import CustomLockRegistry

__all__ = [
    "CustomLockRegistry",
]
