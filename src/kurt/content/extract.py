"""On-demand extraction functions using DSPy.

This module provides LLM-based extraction that runs during the writing workflow,
NOT during initial content ingestion. Extractions are returned directly to the
LLM assistant for use in drafting, not stored in the database.

Philosophy: Extract what you need, when you need it.
"""

import logging
from typing import List, Optional

import dspy
from pydantic import BaseModel, Field

from kurt.content.document import get_document

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class Claim(BaseModel):
    """A factual claim extracted from content."""

    claim_text: str = Field(description="The factual claim (complete sentence)")
    evidence: str = Field(description="Supporting evidence or quote from the source")
    confidence: str = Field(
        description="Confidence level: high (explicitly stated), medium (implied), low (inferred)"
    )


class Entity(BaseModel):
    """A named entity extracted from content."""

    name: str = Field(description="Entity name (canonical form)")
    entity_type: str = Field(
        description="Type: product_feature, company, technology, concept, metric"
    )
    description: str = Field(description="Brief description of the entity (1 sentence)")
    mentions: int = Field(description="Number of times mentioned in content")


class KeyTakeaway(BaseModel):
    """A key takeaway or main point from content."""

    takeaway: str = Field(description="The key point (1-2 sentences)")
    category: str = Field(
        description="Category: technical_concept, best_practice, limitation, use_case, comparison"
    )
    supporting_quote: Optional[str] = Field(
        description="Representative quote from content (if available)"
    )


class CompetitiveDifference(BaseModel):
    """A competitive differentiation point."""

    feature: str = Field(description="Feature or capability name")
    our_approach: str = Field(description="How we handle it")
    their_approach: Optional[str] = Field(description="How competitor handles it (if mentioned)")
    advantage: Optional[str] = Field(description="Why our approach is better (if claimed)")


# ============================================================================
# DSPy Signatures
# ============================================================================


class ExtractClaims(dspy.Signature):
    """Extract factual claims from document content.

    Identify specific, verifiable factual claims made in the content.
    Focus on claims that could be cited in marketing/technical writing.

    GUIDELINES:
    1. Extract complete, standalone claims (not fragments)
    2. Include quantitative claims (metrics, percentages, comparisons)
    3. Include qualitative claims (capabilities, features, limitations)
    4. Include attribution (who said it, if mentioned)
    5. Assess confidence based on how explicitly the claim is stated

    WHAT TO EXTRACT:
    - Product capabilities and features
    - Performance metrics and benchmarks
    - Adoption statistics and customer data
    - Technical specifications
    - Comparative statements
    - Expert opinions and testimonials

    WHAT TO SKIP:
    - Vague marketing language without specific claims
    - Purely promotional statements
    - Redundant restatements of the same claim
    """

    content: str = dspy.InputField(description="Document content (markdown)")
    focus_area: Optional[str] = dspy.InputField(
        description="Optional focus area (e.g., 'pricing', 'integrations', 'performance')",
        default=None,
    )
    claims: List[Claim] = dspy.OutputField(description="List of extracted factual claims")


class ExtractEntities(dspy.Signature):
    """Extract and categorize named entities from document content.

    Identify key entities mentioned in the content and categorize them.
    Focus on entities that provide context for writing (products, features, technologies).

    ENTITY TYPES:
    - product_feature: Product features, capabilities, components
    - company: Company names (competitors, partners, customers)
    - technology: Technologies, frameworks, tools, standards
    - concept: Technical concepts, methodologies, architectural patterns
    - metric: Named metrics, KPIs, measurements

    GUIDELINES:
    1. Use canonical names (e.g., "PostgreSQL" not "postgres")
    2. Count total mentions across the document
    3. Provide concise descriptions (1 sentence)
    4. Merge variants of the same entity (e.g., "Stripe API" and "API" → "Stripe API")
    """

    content: str = dspy.InputField(description="Document content (markdown)")
    entity_types: Optional[List[str]] = dspy.InputField(
        description="Optional filter: only extract these entity types", default=None
    )
    entities: List[Entity] = dspy.OutputField(description="List of extracted entities")


class ExtractTakeaways(dspy.Signature):
    """Extract key takeaways and main points from document content.

    Identify the most important points a reader should remember from this content.
    Focus on actionable insights, technical concepts, and practical guidance.

    CATEGORIES:
    - technical_concept: Core technical concepts explained
    - best_practice: Recommended approaches and patterns
    - limitation: Known limitations, constraints, or edge cases
    - use_case: Specific use cases and scenarios
    - comparison: Comparisons between approaches/tools

    GUIDELINES:
    1. Extract 3-7 key takeaways (prioritize quality over quantity)
    2. Make takeaways self-contained (understandable without full context)
    3. Include supporting quotes when they add credibility
    4. Focus on insights that could inform writing decisions
    """

    content: str = dspy.InputField(description="Document content (markdown)")
    max_takeaways: int = dspy.InputField(
        description="Maximum number of takeaways to extract", default=5
    )
    takeaways: List[KeyTakeaway] = dspy.OutputField(description="List of key takeaways")


class ExtractCompetitiveInfo(dspy.Signature):
    """Extract competitive differentiation points from document content.

    Analyze content to identify how products/approaches are differentiated.
    Focus on explicit comparisons and unique selling points.

    GUIDELINES:
    1. Extract specific feature differences (not vague claims)
    2. Include both "what we do" and "what they do" when mentioned
    3. Note advantages/disadvantages when explicitly stated
    4. Focus on technical and functional differences (not marketing fluff)

    USE CASES:
    - Competitor documentation analysis
    - Product comparison pages
    - Migration guides
    - Technical blog posts with comparisons
    """

    content: str = dspy.InputField(description="Document content (markdown)")
    our_product: str = dspy.InputField(description="Name of our product/service")
    their_product: Optional[str] = dspy.InputField(
        description="Name of competitor product (if analyzing competitor content)", default=None
    )
    differences: List[CompetitiveDifference] = dspy.OutputField(
        description="List of competitive differentiation points"
    )


# ============================================================================
# Extraction Functions
# ============================================================================


def extract_claims(document_id: str, focus_area: Optional[str] = None) -> List[Claim]:
    """
    Extract factual claims from a document.

    Args:
        document_id: Document UUID (full or partial)
        focus_area: Optional focus (e.g., "pricing", "integrations")

    Returns:
        List of Claim objects

    Example:
        claims = extract_claims("550e8400", focus_area="performance")
        for claim in claims:
            print(f"{claim.claim_text} (confidence: {claim.confidence})")
    """
    from kurt.config import load_config

    # Get document
    doc = get_document(document_id)

    if not doc.content_path:
        raise ValueError(f"Document {document_id} has no content")

    # Read content
    config = load_config()
    content_path = config.get_absolute_sources_path() / doc.content_path

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Extract claims
    extractor = dspy.ChainOfThought(ExtractClaims)
    result = extractor(content=content, focus_area=focus_area)

    logger.info(f"Extracted {len(result.claims)} claims from document {doc.id}")
    return result.claims


def extract_entities(
    document_id: str, entity_types: Optional[List[str]] = None
) -> List[Entity]:
    """
    Extract named entities from a document.

    Args:
        document_id: Document UUID (full or partial)
        entity_types: Optional filter (e.g., ["product_feature", "technology"])

    Returns:
        List of Entity objects

    Example:
        entities = extract_entities("550e8400", entity_types=["product_feature"])
        for entity in entities:
            print(f"{entity.name} ({entity.entity_type}): {entity.description}")
    """
    from kurt.config import load_config

    # Get document
    doc = get_document(document_id)

    if not doc.content_path:
        raise ValueError(f"Document {document_id} has no content")

    # Read content
    config = load_config()
    content_path = config.get_absolute_sources_path() / doc.content_path

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Extract entities
    extractor = dspy.ChainOfThought(ExtractEntities)
    result = extractor(content=content, entity_types=entity_types)

    logger.info(f"Extracted {len(result.entities)} entities from document {doc.id}")
    return result.entities


def extract_takeaways(document_id: str, max_takeaways: int = 5) -> List[KeyTakeaway]:
    """
    Extract key takeaways from a document.

    Args:
        document_id: Document UUID (full or partial)
        max_takeaways: Maximum number of takeaways to extract

    Returns:
        List of KeyTakeaway objects

    Example:
        takeaways = extract_takeaways("550e8400", max_takeaways=3)
        for takeaway in takeaways:
            print(f"[{takeaway.category}] {takeaway.takeaway}")
    """
    from kurt.config import load_config

    # Get document
    doc = get_document(document_id)

    if not doc.content_path:
        raise ValueError(f"Document {document_id} has no content")

    # Read content
    config = load_config()
    content_path = config.get_absolute_sources_path() / doc.content_path

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Extract takeaways
    extractor = dspy.ChainOfThought(ExtractTakeaways)
    result = extractor(content=content, max_takeaways=max_takeaways)

    logger.info(f"Extracted {len(result.takeaways)} takeaways from document {doc.id}")
    return result.takeaways


def extract_competitive_info(
    document_id: str, our_product: str, their_product: Optional[str] = None
) -> List[CompetitiveDifference]:
    """
    Extract competitive differentiation points from a document.

    Args:
        document_id: Document UUID (full or partial)
        our_product: Name of our product/service
        their_product: Name of competitor product (if analyzing competitor content)

    Returns:
        List of CompetitiveDifference objects

    Example:
        diffs = extract_competitive_info("550e8400", our_product="Acme Platform")
        for diff in diffs:
            print(f"{diff.feature}: {diff.our_approach} vs {diff.their_approach}")
    """
    from kurt.config import load_config

    # Get document
    doc = get_document(document_id)

    if not doc.content_path:
        raise ValueError(f"Document {document_id} has no content")

    # Read content
    config = load_config()
    content_path = config.get_absolute_sources_path() / doc.content_path

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Configure DSPy LM
    from kurt.config.base import get_config_or_default

    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    # Extract competitive info
    extractor = dspy.ChainOfThought(ExtractCompetitiveInfo)
    result = extractor(content=content, our_product=our_product, their_product=their_product)

    logger.info(f"Extracted {len(result.differences)} competitive points from document {doc.id}")
    return result.differences


# ============================================================================
# Batch Extraction
# ============================================================================


def extract_from_multiple(
    document_ids: List[str], extraction_type: str, **kwargs
) -> dict[str, List]:
    """
    Extract from multiple documents at once.

    Args:
        document_ids: List of document UUIDs
        extraction_type: "claims", "entities", "takeaways", or "competitive"
        **kwargs: Arguments to pass to extraction function

    Returns:
        Dict mapping document_id to list of extracted items

    Example:
        results = extract_from_multiple(
            ["550e8400", "660e9500"],
            extraction_type="claims",
            focus_area="performance"
        )
        for doc_id, claims in results.items():
            print(f"{doc_id}: {len(claims)} claims")
    """
    extractors = {
        "claims": extract_claims,
        "entities": extract_entities,
        "takeaways": extract_takeaways,
        "competitive": extract_competitive_info,
    }

    if extraction_type not in extractors:
        raise ValueError(
            f"Invalid extraction type: {extraction_type}. "
            f"Must be one of: {', '.join(extractors.keys())}"
        )

    extractor = extractors[extraction_type]
    results = {}

    for doc_id in document_ids:
        try:
            results[doc_id] = extractor(doc_id, **kwargs)
        except Exception as e:
            logger.error(f"Failed to extract from {doc_id}: {e}")
            results[doc_id] = []

    return results
