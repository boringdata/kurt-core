"""Content gap analysis using DSPy.

Identifies missing topics, coverage gaps, and content opportunities
by analyzing existing content and comparing against target topics.
"""

import logging
from typing import List, Optional

import dspy
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class ContentGap(BaseModel):
    """A gap in content coverage."""

    topic: str = Field(description="Topic or subject area with gap")
    gap_type: str = Field(
        description="Type of gap: missing, shallow, outdated, inconsistent, or fragmented"
    )
    description: str = Field(description="Description of the gap and why it matters")
    suggested_content: str = Field(description="Suggested content to fill the gap")
    priority: str = Field(description="Priority: high, medium, or low")
    reasoning: str = Field(description="Why this gap should be addressed")


class TopicCoverage(BaseModel):
    """Coverage analysis for a topic."""

    topic: str = Field(description="Topic being analyzed")
    coverage_score: int = Field(description="Coverage score (1-10, 10 = comprehensive)")
    covered_aspects: List[str] = Field(description="Aspects that are well covered")
    missing_aspects: List[str] = Field(description="Aspects that are missing or shallow")
    recommendation: str = Field(description="Recommendation for improving coverage")


class ContentSuggestion(BaseModel):
    """A suggestion for new content."""

    title: str = Field(description="Suggested content title")
    content_type: str = Field(
        description="Type: tutorial, guide, reference, blog_post, product_page, case_study"
    )
    description: str = Field(description="What this content should cover (2-3 sentences)")
    target_audience: str = Field(description="Primary audience (e.g., developers, product managers)")
    rationale: str = Field(description="Why this content would be valuable")


# ============================================================================
# DSPy Signatures
# ============================================================================


class IdentifyContentGaps(dspy.Signature):
    """Analyze content collection to identify gaps in coverage.

    Review the provided content inventory (titles, descriptions, URLs) to identify:
    1. Missing topics that should be covered
    2. Topics with shallow coverage that need more depth
    3. Outdated content that needs refreshing
    4. Inconsistent coverage across related topics
    5. Fragmented information that should be consolidated

    ANALYSIS APPROACH:
    1. Identify the main topic areas covered by existing content
    2. Look for patterns in what's covered vs. what's missing
    3. Consider the target audience and their likely information needs
    4. Assess whether coverage is balanced across topics
    5. Identify opportunities for new or improved content

    GAP TYPES:
    - missing: Topic not covered at all
    - shallow: Topic mentioned but lacks depth or detail
    - outdated: Content exists but is outdated (based on publish dates)
    - inconsistent: Coverage varies greatly across related topics
    - fragmented: Information scattered across multiple docs that should be unified

    PRIORITIZATION:
    - high: Critical gap affecting user understanding or product adoption
    - medium: Important but not blocking
    - low: Nice-to-have improvement
    """

    content_inventory: str = dspy.InputField(
        description="Inventory of existing content (URLs, titles, descriptions)"
    )
    target_topics: Optional[str] = dspy.InputField(
        description="Optional: Specific topics to analyze (comma-separated)", default=None
    )
    audience: Optional[str] = dspy.InputField(
        description="Optional: Target audience (e.g., 'developers', 'product teams')", default=None
    )
    gaps: List[ContentGap] = dspy.OutputField(description="List of identified content gaps")


class AnalyzeTopicCoverage(dspy.Signature):
    """Analyze coverage of specific topics across content collection.

    For each target topic, assess:
    1. What aspects are well covered
    2. What aspects are missing or underdeveloped
    3. Overall coverage score (1-10)
    4. Recommendations for improvement

    SCORING RUBRIC (1-10):
    - 1-2: Barely mentioned, no substance
    - 3-4: Basic introduction but major gaps
    - 5-6: Moderate coverage but missing key aspects
    - 7-8: Good coverage with minor gaps
    - 9-10: Comprehensive, authoritative coverage

    GUIDELINES:
    1. Consider breadth (range of topics) AND depth (detail level)
    2. Assess whether coverage matches likely user needs
    3. Identify specific aspects that need more attention
    4. Provide actionable recommendations
    """

    content_inventory: str = dspy.InputField(
        description="Inventory of existing content (URLs, titles, descriptions)"
    )
    topics: List[str] = dspy.InputField(description="Topics to analyze coverage for")
    coverage: List[TopicCoverage] = dspy.OutputField(description="Coverage analysis for each topic")


class GenerateContentSuggestions(dspy.Signature):
    """Generate specific content suggestions to address gaps.

    Based on identified gaps and coverage analysis, suggest concrete content
    pieces that would improve the collection.

    GUIDELINES:
    1. Suggest specific, actionable content pieces (not vague ideas)
    2. Include clear title and description
    3. Match content type to the gap (tutorial for how-to, reference for API details, etc.)
    4. Specify target audience clearly
    5. Explain why this content would be valuable

    CONTENT TYPES:
    - tutorial: Step-by-step guide to accomplish a task
    - guide: Conceptual explanation or best practices
    - reference: Technical documentation or API reference
    - blog_post: Thought leadership or announcement
    - product_page: Product marketing page
    - case_study: Customer success story
    """

    gaps: str = dspy.InputField(description="Content gaps identified (JSON or text summary)")
    coverage_analysis: Optional[str] = dspy.InputField(
        description="Optional: Topic coverage analysis (JSON or text)", default=None
    )
    max_suggestions: int = dspy.InputField(
        description="Maximum number of suggestions to generate", default=5
    )
    suggestions: List[ContentSuggestion] = dspy.OutputField(description="List of content suggestions")


# ============================================================================
# Gap Analysis Functions
# ============================================================================


def analyze_content_gaps(
    include_pattern: Optional[str] = None,
    target_topics: Optional[List[str]] = None,
    audience: Optional[str] = None,
) -> List[ContentGap]:
    """
    Identify gaps in content coverage.

    Args:
        include_pattern: Optional glob pattern to filter content
        target_topics: Optional list of specific topics to analyze
        audience: Optional target audience (e.g., "developers")

    Returns:
        List of ContentGap objects

    Example:
        gaps = analyze_content_gaps(
            include_pattern="*/docs/*",
            target_topics=["authentication", "webhooks", "rate limiting"],
            audience="developers"
        )
        for gap in gaps:
            print(f"[{gap.priority}] {gap.topic}: {gap.description}")
    """
    from kurt.content.document import list_content

    # Get content inventory
    docs = list_content(include_pattern=include_pattern, with_status="FETCHED")

    if not docs:
        raise ValueError("No content found to analyze")

    # Build inventory string
    inventory_lines = []
    for doc in docs:
        line = f"- {doc.title or 'Untitled'}"
        if doc.source_url:
            line += f" ({doc.source_url})"
        if doc.description:
            line += f": {doc.description[:100]}"
        inventory_lines.append(line)

    inventory = "\n".join(inventory_lines)

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Analyze gaps
    analyzer = dspy.ChainOfThought(IdentifyContentGaps)
    result = analyzer(
        content_inventory=inventory,
        target_topics=", ".join(target_topics) if target_topics else None,
        audience=audience,
    )

    logger.info(f"Identified {len(result.gaps)} content gaps")
    return result.gaps


def analyze_topic_coverage(
    topics: List[str],
    include_pattern: Optional[str] = None,
) -> List[TopicCoverage]:
    """
    Analyze coverage of specific topics.

    Args:
        topics: List of topics to analyze
        include_pattern: Optional glob pattern to filter content

    Returns:
        List of TopicCoverage objects

    Example:
        coverage = analyze_topic_coverage(
            topics=["API authentication", "webhooks", "rate limiting"],
            include_pattern="*/docs/*"
        )
        for topic_coverage in coverage:
            print(f"{topic_coverage.topic}: {topic_coverage.coverage_score}/10")
            print(f"  Missing: {', '.join(topic_coverage.missing_aspects)}")
    """
    from kurt.content.document import list_content

    # Get content inventory
    docs = list_content(include_pattern=include_pattern, with_status="FETCHED")

    if not docs:
        raise ValueError("No content found to analyze")

    # Build inventory string
    inventory_lines = []
    for doc in docs:
        line = f"- {doc.title or 'Untitled'}"
        if doc.source_url:
            line += f" ({doc.source_url})"
        if doc.description:
            line += f": {doc.description[:100]}"
        inventory_lines.append(line)

    inventory = "\n".join(inventory_lines)

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Analyze coverage
    analyzer = dspy.ChainOfThought(AnalyzeTopicCoverage)
    result = analyzer(content_inventory=inventory, topics=topics)

    logger.info(f"Analyzed coverage for {len(result.coverage)} topics")
    return result.coverage


def generate_content_suggestions(
    gaps: Optional[List[ContentGap]] = None,
    coverage: Optional[List[TopicCoverage]] = None,
    max_suggestions: int = 5,
    include_pattern: Optional[str] = None,
) -> List[ContentSuggestion]:
    """
    Generate content suggestions to address gaps.

    Args:
        gaps: Optional list of gaps (if not provided, will analyze first)
        coverage: Optional coverage analysis (if not provided, will skip)
        max_suggestions: Maximum number of suggestions to generate
        include_pattern: Optional glob pattern to filter content (for analysis)

    Returns:
        List of ContentSuggestion objects

    Example:
        # Generate suggestions from existing gap analysis
        gaps = analyze_content_gaps(target_topics=["webhooks"])
        suggestions = generate_content_suggestions(gaps=gaps, max_suggestions=3)

        # Or analyze and generate in one go
        suggestions = generate_content_suggestions(
            include_pattern="*/docs/*",
            max_suggestions=5
        )

        for suggestion in suggestions:
            print(f"[{suggestion.content_type}] {suggestion.title}")
            print(f"  {suggestion.description}")
    """
    import json

    # If gaps not provided, analyze first
    if gaps is None:
        gaps = analyze_content_gaps(include_pattern=include_pattern)

    # Convert gaps to JSON for prompt
    gaps_json = json.dumps([gap.dict() for gap in gaps], indent=2)

    # Convert coverage to JSON if provided
    coverage_json = None
    if coverage:
        coverage_json = json.dumps([cov.dict() for cov in coverage], indent=2)

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Generate suggestions
    generator = dspy.ChainOfThought(GenerateContentSuggestions)
    result = generator(
        gaps=gaps_json, coverage_analysis=coverage_json, max_suggestions=max_suggestions
    )

    logger.info(f"Generated {len(result.suggestions)} content suggestions")
    return result.suggestions


def full_gap_analysis(
    include_pattern: Optional[str] = None,
    target_topics: Optional[List[str]] = None,
    audience: Optional[str] = None,
    max_suggestions: int = 5,
) -> dict:
    """
    Run complete content gap analysis workflow.

    Performs:
    1. Gap identification
    2. Topic coverage analysis (if target_topics provided)
    3. Content suggestions generation

    Args:
        include_pattern: Optional glob pattern to filter content
        target_topics: Optional list of specific topics to analyze
        audience: Optional target audience
        max_suggestions: Maximum content suggestions to generate

    Returns:
        Dict with:
            - gaps: List[ContentGap]
            - coverage: List[TopicCoverage] (if target_topics provided)
            - suggestions: List[ContentSuggestion]

    Example:
        analysis = full_gap_analysis(
            include_pattern="*/docs/*",
            target_topics=["authentication", "webhooks"],
            audience="developers",
            max_suggestions=3
        )

        print(f"Found {len(analysis['gaps'])} gaps")
        print(f"Generated {len(analysis['suggestions'])} suggestions")
    """
    # Step 1: Identify gaps
    logger.info("Step 1: Identifying content gaps...")
    gaps = analyze_content_gaps(
        include_pattern=include_pattern, target_topics=target_topics, audience=audience
    )

    # Step 2: Analyze topic coverage (if topics provided)
    coverage = None
    if target_topics:
        logger.info("Step 2: Analyzing topic coverage...")
        coverage = analyze_topic_coverage(topics=target_topics, include_pattern=include_pattern)

    # Step 3: Generate content suggestions
    logger.info("Step 3: Generating content suggestions...")
    suggestions = generate_content_suggestions(
        gaps=gaps, coverage=coverage, max_suggestions=max_suggestions
    )

    return {"gaps": gaps, "coverage": coverage, "suggestions": suggestions}
