"""DSPy signatures for workflows.

This module contains DSPy signature definitions used in workflow steps.
"""

from kurt.workflows.signatures.aeo import (
    AnalyzeQuestions,
    GenerateFAQContent,
    GenerateJSONLD,
    GenerateSchemaMarkup,
)
from kurt.workflows.signatures.content import (
    AnalyzeClusterQuality,
    GenerateClusterReport,
    SummarizeContent,
)

__all__ = [
    # AEO signatures
    "AnalyzeQuestions",
    "GenerateFAQContent",
    "GenerateJSONLD",
    "GenerateSchemaMarkup",
    # Content signatures
    "AnalyzeClusterQuality",
    "GenerateClusterReport",
    "SummarizeContent",
]
