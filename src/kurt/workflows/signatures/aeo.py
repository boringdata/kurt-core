"""DSPy signatures for AEO (AI Engine Optimization) workflows.

Signatures for:
- Mining and analyzing questions
- Generating FAQ content
- Creating schema markup (JSON-LD)
"""

from typing import List

import dspy
from pydantic import BaseModel, Field

# ============================================================================
# Data Models
# ============================================================================


class Question(BaseModel):
    """A question from community sources."""

    question: str = Field(description="The question text")
    context: str = Field(description="Context or source of the question")
    frequency: int = Field(default=1, description="How often this question appears")
    keywords: List[str] = Field(default_factory=list, description="Key terms in the question")


class QuestionCluster(BaseModel):
    """A cluster of related questions by topic."""

    topic: str = Field(description="Topic name for this cluster")
    description: str = Field(description="Description of what this topic covers")
    questions: List[Question] = Field(description="Questions in this cluster")
    priority: int = Field(default=0, description="Priority score (higher = more important)")


class FAQPage(BaseModel):
    """A generated FAQ page."""

    slug: str = Field(description="URL slug for the page")
    title: str = Field(description="Page title")
    meta_description: str = Field(description="Meta description for SEO")
    introduction: str = Field(description="Introductory paragraph")
    faqs: List["FAQItem"] = Field(description="FAQ items")
    related_topics: List[str] = Field(default_factory=list, description="Related topics to link to")


class FAQItem(BaseModel):
    """A single FAQ item."""

    question: str = Field(description="The question")
    answer: str = Field(description="The answer")
    keywords: List[str] = Field(default_factory=list, description="Keywords for this FAQ")


class SchemaMarkup(BaseModel):
    """JSON-LD schema markup."""

    context: str = Field(default="https://schema.org", alias="@context")
    type: str = Field(alias="@type")
    main_entity: List[dict] = Field(alias="mainEntity")


# ============================================================================
# DSPy Signatures
# ============================================================================


class AnalyzeQuestions(dspy.Signature):
    """
    Analyze a collection of questions and cluster them by topic.

    Given a list of questions from community sources (Reddit, forums, support tickets),
    identify common themes and group related questions together.

    Focus on:
    1. Identifying core topics that questions are about
    2. Grouping semantically similar questions
    3. Ranking clusters by importance (frequency, complexity, business value)
    4. Extracting key terms and concepts
    """

    questions: str = dspy.InputField(desc="List of questions (JSON format)")
    domain: str = dspy.InputField(desc="Domain/industry context")

    clusters: str = dspy.OutputField(
        desc="Question clusters (JSON format with topic, questions, priority)"
    )


class GenerateFAQContent(dspy.Signature):
    """
    Generate comprehensive FAQ page content from question clusters.

    Create well-structured FAQ pages that:
    1. Answer questions clearly and comprehensively
    2. Use natural language that resonates with the target audience
    3. Include relevant keywords naturally
    4. Provide practical, actionable information
    5. Link to related topics where appropriate

    Content should be optimized for both human readers AND AI search engines.
    """

    clusters: str = dspy.InputField(desc="Question clusters (JSON format)")
    domain: str = dspy.InputField(desc="Domain/industry context")
    brand_voice: str = dspy.InputField(
        desc="Brand voice guidelines (e.g., professional, friendly, technical)"
    )
    existing_content: str = dspy.InputField(
        desc="Existing content to reference for consistency", default=""
    )

    faq_pages: str = dspy.OutputField(
        desc="Generated FAQ pages (JSON format with slug, title, content, faqs)"
    )


class GenerateJSONLD(dspy.Signature):
    """
    Generate JSON-LD schema markup for FAQ pages.

    Create structured data markup following schema.org FAQPage specification.
    This helps AI search engines understand and cite the content.

    Requirements:
    1. Valid JSON-LD syntax
    2. Proper schema.org FAQPage structure
    3. Each question/answer as separate entities
    4. Include relevant metadata
    """

    faq_pages: str = dspy.InputField(desc="FAQ pages with questions and answers (JSON format)")
    base_url: str = dspy.InputField(desc="Base URL for the website")

    schema_markup: str = dspy.OutputField(desc="JSON-LD schema markup for each page (JSON format)")


class GenerateSchemaMarkup(dspy.Signature):
    """
    Generate schema.org markup for various content types.

    Supports multiple schema types:
    - FAQPage: Frequently asked questions
    - HowTo: Step-by-step guides
    - Article: Blog posts and articles
    - Product: Product pages
    - Organization: About/company pages

    Creates valid JSON-LD markup that enhances visibility in AI search results.
    """

    content: str = dspy.InputField(desc="Content to mark up (JSON format)")
    schema_type: str = dspy.InputField(
        desc="Schema type (FAQPage, HowTo, Article, Product, Organization)"
    )
    base_url: str = dspy.InputField(desc="Base URL for the website")
    additional_metadata: str = dspy.InputField(
        desc="Additional metadata (JSON format)", default="{}"
    )

    schema_markup: str = dspy.OutputField(desc="JSON-LD schema markup (JSON format)")


class AnalyzeCitationOpportunities(dspy.Signature):
    """
    Analyze content for citation opportunities in AI search engines.

    Identify where content could be better structured to increase the likelihood
    of being cited by ChatGPT, Perplexity, Claude, and other AI search tools.

    Focus on:
    1. Clear, definitive statements that answer common questions
    2. Structured data opportunities (lists, tables, FAQs)
    3. Authority signals (stats, research, expert quotes)
    4. Topic coverage gaps
    5. Comparison opportunities
    """

    content: str = dspy.InputField(desc="Content to analyze (markdown or HTML)")
    domain: str = dspy.InputField(desc="Domain/industry")
    target_keywords: str = dspy.InputField(desc="Target keywords (comma-separated)")

    opportunities: str = dspy.OutputField(
        desc="Citation opportunities (JSON format with type, description, priority, example)"
    )


class OptimizeForAISearch(dspy.Signature):
    """
    Optimize content for AI search engine visibility.

    Restructure and enhance content to maximize the chances of being cited
    by AI search engines while maintaining quality for human readers.

    Optimization strategies:
    1. Add clear, quotable definitions and explanations
    2. Structure as FAQs where appropriate
    3. Include specific facts, stats, and data points
    4. Use clear headings and lists
    5. Add context and examples
    6. Include comparisons and alternatives
    """

    content: str = dspy.InputField(desc="Original content (markdown or HTML)")
    target_queries: str = dspy.InputField(desc="Target queries/questions to answer")
    optimization_goals: str = dspy.InputField(
        desc="Goals (citations, traffic, conversions)", default="citations"
    )

    optimized_content: str = dspy.OutputField(desc="Optimized content (markdown)")
    changes_summary: str = dspy.OutputField(desc="Summary of changes made")


__all__ = [
    "Question",
    "QuestionCluster",
    "FAQPage",
    "FAQItem",
    "SchemaMarkup",
    "AnalyzeQuestions",
    "GenerateFAQContent",
    "GenerateJSONLD",
    "GenerateSchemaMarkup",
    "AnalyzeCitationOpportunities",
    "OptimizeForAISearch",
]
