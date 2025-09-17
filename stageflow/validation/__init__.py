"""
Validation and linting module for StageFlow.

This module provides process schema validation, structural analysis,
and regression detection capabilities.
"""

from stageflow.validation.linter import LintResult, LintSeverity, ProcessLinter
from stageflow.validation.regression import RegressionDetector, RegressionResult

__all__ = [
    "ProcessLinter",
    "LintResult",
    "LintSeverity",
    "RegressionDetector",
    "RegressionResult",
]
