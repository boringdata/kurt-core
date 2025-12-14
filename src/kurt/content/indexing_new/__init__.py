"""
Kurt Content Indexing - Model-based refactor.

This package provides a declarative, model-based approach to content indexing.
"""

from .framework import TableReader, TableWriter, model

__all__ = ["model", "TableReader", "TableWriter"]
