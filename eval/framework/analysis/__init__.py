"""Analysis tools for evaluation results.

This module provides tools for comparing different approaches,
aggregating results, and generating reports.
"""

from .aggregate import aggregate_transcripts
from .aggregate import main as aggregate_main
from .compare import generate_report_from_dirs
from .compare import main as compare_main

__all__ = [
    "generate_report_from_dirs",
    "aggregate_transcripts",
    "compare_main",
    "aggregate_main",
]
