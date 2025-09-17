"""
Extension system for StageFlow.

This module provides the extension framework including custom lock
registries, property resolvers, and snapshot providers.
"""

from stageflow.extensions.registry import CustomLockRegistry
from stageflow.extensions.resolvers import JsonPathResolver, PropertyResolver
from stageflow.extensions.snapshots import InMemorySnapshotProvider, SnapshotProvider

__all__ = [
    "CustomLockRegistry",
    "PropertyResolver",
    "JsonPathResolver",
    "SnapshotProvider",
    "InMemorySnapshotProvider",
]
