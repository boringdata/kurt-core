"""Shared pytest configuration and fixtures for eval tests."""

import shutil
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def cleanup_test_result_directories():
    """Clean up test directories in eval/results after all tests complete."""
    yield

    # After all tests complete, clean up any test directories
    test_patterns = [
        "test*",
        "minimal",
        "setup_only",
        "prompt_only",
        "with_assertions",
        "with_project",
        "full_featured",
        "conversational_*",
    ]

    results_path = Path("eval/results")
    if results_path.exists():
        for pattern in test_patterns:
            for dir_path in results_path.glob(pattern):
                if dir_path.is_dir():
                    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def cleanup_per_test():
    """Clean up test directories after each test."""
    yield

    # List of known test directories that should be cleaned
    test_dirs = [
        "eval/results/test_scenario",
        "eval/results/test",
        "eval/results/test_conv",
        "eval/results/test_judge",
        "eval/results/minimal",
        "eval/results/setup_only",
        "eval/results/prompt_only",
        "eval/results/with_assertions",
        "eval/results/with_project",
        "eval/results/full_test",
        "eval/results/full_featured",
    ]

    # Clean up specific directories
    for dir_path in test_dirs:
        path = Path(dir_path)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    # Also clean up pattern-based directories
    results_path = Path("eval/results")
    if results_path.exists():
        for pattern in ["conversational_*", "test*"]:
            for dir_path in results_path.glob(pattern):
                if dir_path.is_dir():
                    shutil.rmtree(dir_path, ignore_errors=True)