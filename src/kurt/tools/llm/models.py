"""
Built-in output schema models for the LLM tool.

These models can be referenced by name in the LLMConfig.output_schema field.
Custom workflow models can be added in workflows/<name>/models.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractEntities(BaseModel):
    """Extract named entities from text."""

    entities: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of entities with 'name', 'type', and optional 'description'",
    )


class ExtractKeywords(BaseModel):
    """Extract keywords or key phrases from text."""

    keywords: list[str] = Field(
        default_factory=list,
        description="List of extracted keywords or key phrases",
    )


class SentimentAnalysis(BaseModel):
    """Analyze sentiment of text."""

    sentiment: str = Field(
        default="neutral",
        description="Sentiment classification: 'positive', 'negative', or 'neutral'",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the sentiment classification",
    )


class Summarize(BaseModel):
    """Summarize text content."""

    summary: str = Field(
        default="",
        description="Concise summary of the input text",
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="List of key points extracted from the text",
    )
