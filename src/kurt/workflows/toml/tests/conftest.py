"""
Pytest configuration for TOML workflow tests.

Ensures tool registry is populated before tests that need it.
"""

import pytest


@pytest.fixture(autouse=True)
def ensure_tools_registered():
    """
    Autouse fixture that ensures all tools are registered before each test.

    This is needed because some other test modules call clear_registry()
    which can leave the registry empty when workflow tests run.

    The issue: clear_registry() clears TOOLS but doesn't remove modules from
    sys.modules. Importing a module again doesn't re-run decorators like
    @register_tool. So we need to manually register tools that are missing.
    """
    from kurt.tools.core.registry import TOOLS

    # List of tool modules and their tool names
    # Each tuple is (module_path, tool_name, tool_class_name)
    tools_to_ensure = [
        ("kurt.tools.map", "map", "MapTool"),
        ("kurt.tools.fetch", "fetch", "FetchTool"),
        ("kurt.tools.sql", "sql", "SQLTool"),
        ("kurt.tools.write_db", "write-db", "WriteTool"),
        ("kurt.tools.batch_embedding", "batch-embedding", "BatchEmbeddingTool"),
        ("kurt.tools.batch_llm", "batch-llm", "BatchLLMTool"),
        ("kurt.tools.agent", "agent", "AgentTool"),
        ("kurt.tools.research", "research", "ResearchTool"),
        ("kurt.tools.signals", "signals", "SignalsTool"),
    ]

    import importlib

    for module_path, tool_name, tool_class_name in tools_to_ensure:
        if tool_name not in TOOLS:
            try:
                module = importlib.import_module(module_path)
                tool_class = getattr(module, tool_class_name)
                TOOLS[tool_name] = tool_class
            except (ImportError, AttributeError):
                pass  # Tool not available in this installation

    yield
