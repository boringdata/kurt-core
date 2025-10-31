"""Kurt Evaluation Framework

Simple framework for testing Kurt agent behavior using Claude Code SDK.
"""

from .conversation import ConversationTurn, Scenario, UserAgent
from .evaluator import (
    Assertion,
    ConversationContains,
    DatabaseHasDocuments,
    FileContains,
    FileExists,
    MetricEquals,
    ToolWasUsed,
)
from .metrics import MetricsCollector, collect_metrics
from .runner import ScenarioRunner
from .workspace import IsolatedWorkspace

__all__ = [
    "IsolatedWorkspace",
    "ConversationTurn",
    "UserAgent",
    "Scenario",
    "Assertion",
    "FileExists",
    "FileContains",
    "DatabaseHasDocuments",
    "ToolWasUsed",
    "MetricEquals",
    "ConversationContains",
    "collect_metrics",
    "MetricsCollector",
    "ScenarioRunner",
]
