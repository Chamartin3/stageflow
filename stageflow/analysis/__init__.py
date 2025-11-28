"""StageFlow process analysis module.

Provides unified analysis capabilities for process definitions.
Only the ProcessAnalyzer is exposed as the public API.

Usage:
    from stageflow.analysis import ProcessAnalyzer

    analyzer = ProcessAnalyzer(process)
    issues = analyzer.analyze()
"""

from .analyzer import ProcessAnalyzer

__all__ = ["ProcessAnalyzer"]
