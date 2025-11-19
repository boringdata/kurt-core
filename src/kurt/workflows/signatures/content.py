"""DSPy signatures for content analysis and generation workflows."""

from typing import List

import dspy
from pydantic import BaseModel, Field

# ============================================================================
# Data Models
# ============================================================================


class Cluster(BaseModel):
    """A content cluster."""

    name: str = Field(description="Cluster name")
    description: str = Field(description="Cluster description")
    document_count: int = Field(description="Number of documents in cluster")
    keywords: List[str] = Field(default_factory=list, description="Key terms")


class ClusterQualityMetrics(BaseModel):
    """Quality metrics for a cluster."""

    coherence_score: float = Field(description="How coherent the cluster is (0-1)")
    coverage_score: float = Field(description="How well it covers the topic (0-1)")
    distinctiveness_score: float = Field(description="How distinct from other clusters (0-1)")
    issues: List[str] = Field(default_factory=list, description="Quality issues found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


# ============================================================================
# DSPy Signatures
# ============================================================================


class AnalyzeClusterQuality(dspy.Signature):
    """
    Analyze the quality of content clusters.

    Evaluate:
    1. Coherence: Are documents in the cluster actually related?
    2. Coverage: Does the cluster capture all relevant content for its topic?
    3. Distinctiveness: Is this cluster meaningfully different from others?
    4. Naming: Is the cluster name clear and descriptive?

    Provide actionable suggestions for improving cluster quality.
    """

    clusters: str = dspy.InputField(desc="Clusters to analyze (JSON format)")
    sample_documents: str = dspy.InputField(desc="Sample documents from each cluster (JSON format)")

    analysis: str = dspy.OutputField(
        desc="Quality analysis per cluster (JSON format with scores and suggestions)"
    )


class GenerateClusterReport(dspy.Signature):
    """
    Generate a comprehensive report on content clusters.

    Create a human-readable report that:
    1. Summarizes the clustering results
    2. Highlights key topics and themes
    3. Identifies gaps and opportunities
    4. Provides recommendations for content strategy

    The report should be useful for content strategists and marketers.
    """

    clusters: str = dspy.InputField(desc="Clusters (JSON format)")
    analysis: str = dspy.InputField(desc="Quality analysis (JSON format)")
    domain: str = dspy.InputField(desc="Domain/industry context")

    report: str = dspy.OutputField(desc="Markdown-formatted report")


class SummarizeContent(dspy.Signature):
    """
    Generate concise summaries of content.

    Create summaries that:
    1. Capture key points and main ideas
    2. Maintain context and accuracy
    3. Are appropriate for the target audience
    4. Can be used for meta descriptions, previews, etc.
    """

    content: str = dspy.InputField(desc="Content to summarize (markdown or HTML)")
    summary_type: str = dspy.InputField(
        desc="Type of summary (brief, detailed, seo, social)", default="brief"
    )
    max_length: int = dspy.InputField(desc="Maximum length in words", default=50)

    summary: str = dspy.OutputField(desc="Generated summary")


class ExtractTopics(dspy.Signature):
    """
    Extract main topics and themes from content.

    Identify:
    1. Primary topics covered
    2. Secondary/related topics
    3. Key entities (people, companies, technologies)
    4. Core concepts and terminology

    Focus on extracting structured, actionable topic information.
    """

    content: str = dspy.InputField(desc="Content to analyze (markdown or HTML)")
    domain: str = dspy.InputField(desc="Domain/industry context", default="")

    topics: str = dspy.OutputField(
        desc="Extracted topics (JSON format with topic, relevance, entities)"
    )


class GenerateContentIdeas(dspy.Signature):
    """
    Generate content ideas based on existing content and gaps.

    Analyze existing content to suggest:
    1. Missing topics to cover
    2. Expansion opportunities for existing topics
    3. Content formats to try (guides, tutorials, comparisons)
    4. Questions to answer

    Ideas should be specific, actionable, and aligned with content strategy.
    """

    existing_content: str = dspy.InputField(desc="Summary of existing content (JSON format)")
    clusters: str = dspy.InputField(desc="Content clusters (JSON format)")
    target_audience: str = dspy.InputField(desc="Target audience description")
    goals: str = dspy.InputField(
        desc="Content goals (traffic, conversions, education)", default="traffic"
    )

    ideas: str = dspy.OutputField(
        desc="Content ideas (JSON format with title, description, priority, format)"
    )


class AnalyzeContentGaps(dspy.Signature):
    """
    Identify content gaps and opportunities.

    Compare:
    1. What content exists
    2. What content is missing
    3. What competitors cover
    4. What audience is asking about

    Provide prioritized recommendations for filling gaps.
    """

    existing_topics: str = dspy.InputField(desc="Topics covered in existing content (JSON format)")
    target_keywords: str = dspy.InputField(desc="Target keywords and queries", default="")
    competitor_topics: str = dspy.InputField(
        desc="Topics covered by competitors (JSON format)", default="[]"
    )
    audience_questions: str = dspy.InputField(
        desc="Questions from audience (JSON format)", default="[]"
    )

    gaps: str = dspy.OutputField(
        desc="Content gaps (JSON format with gap, priority, opportunity_size, suggested_content)"
    )


class ClassifyContentType(dspy.Signature):
    """
    Classify content by type and purpose.

    Classify into types:
    - Reference: Documentation, API reference, specs
    - Tutorial: Step-by-step instructions
    - Guide: Conceptual guides, best practices
    - Blog: Blog posts, news, updates
    - Product: Product pages, features
    - Solution: Solution pages, use cases
    - Case Study: Customer stories, examples
    - Landing Page: Marketing pages

    Also identify content purpose: educate, convert, support, engage
    """

    content: str = dspy.InputField(desc="Content to classify (markdown or HTML)")
    url: str = dspy.InputField(desc="URL of the content", default="")

    content_type: str = dspy.OutputField(desc="Primary content type")
    content_purpose: str = dspy.OutputField(desc="Primary purpose")
    confidence: float = dspy.OutputField(desc="Classification confidence (0-1)")


__all__ = [
    "Cluster",
    "ClusterQualityMetrics",
    "AnalyzeClusterQuality",
    "GenerateClusterReport",
    "SummarizeContent",
    "ExtractTopics",
    "GenerateContentIdeas",
    "AnalyzeContentGaps",
    "ClassifyContentType",
]
