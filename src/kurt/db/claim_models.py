"""Claim extraction database models for Kurt."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from kurt.db.tables import TableNames


class ClaimType(str, Enum):
    """Types of claims that can be extracted from documents.

    Each type has a specific focus to guide extraction.
    """

    # What it IS or CAN/CANNOT DO
    CAPABILITY = "capability"  # What something CAN DO
    LIMITATION = "limitation"  # What something CANNOT DO
    DEFINITION = "definition"  # WHAT something IS
    FEATURE = "feature"  # Built-in functionality (kept for backward compatibility)

    # How to USE or how it WORKS
    INSTRUCTION = "instruction"  # HOW TO use (includes process steps)
    EXPLANATION = "explanation"  # HOW/WHY it works (includes background)

    # Relationships and requirements
    REQUIREMENT = "requirement"  # Prerequisites, dependencies, compatibility
    INTEGRATION = "integration"  # How systems work together

    # Metrics and comparisons
    PERFORMANCE = "performance"  # Speed, scale, statistics, comparisons
    COMPARISON = "comparison"  # Comparing alternatives (kept for backward compatibility)

    # Business
    COMMERCIAL = "commercial"  # Pricing, availability, licensing

    @classmethod
    def get_description(cls, claim_type: "ClaimType") -> str:
        """Get the description and examples for a claim type."""
        # Define metadata inside the method to avoid enum member issues
        metadata = {
            "capability": (
                "What something CAN DO or provides",
                "X enables Y",
                "X supports Z",
                "X provides/enables/supports Y",
            ),
            "limitation": (
                "What something CANNOT DO or constraints",
                "X does not support Y",
                "X is limited to Z",
                "X cannot handle Y",
            ),
            "definition": (
                "WHAT something IS - definitions and categorizations",
                "X is a type of Y",
                "Embeddings are vectors",
                "X is [explanation of concept]",
            ),
            "feature": (
                "Built-in functionality or included components",
                "X includes Y",
                "X has Z feature",
                "X comes with Y",
            ),
            "instruction": (
                "HOW TO use - CRITICAL: Extract code/SQL VERBATIM, never summarize",
                "SELECT embedding('exact text')",
                "CREATE TABLE ... (full SQL)",
                "To use X, do Y",
                "RULE: ANY code in ```blocks → Extract THE ENTIRE CODE exactly",
            ),
            "explanation": (
                "HOW or WHY something works - technical explanations and background",
                "X works by converting Y to Z",
                "The purpose of X is Y",
                "What are X questions/answers",
                "Full-text search vs semantic search comparisons",
            ),
            "requirement": (
                "Prerequisites, dependencies, compatibility needs",
                "X requires Y",
                "X is compatible with Y",
                "Must have Z installed",
            ),
            "integration": (
                "How systems work together or connect",
                "X uses Y's API",
                "X powered by Y",
                "X integrates with Z",
            ),
            "performance": (
                "Speed, scale, metrics, and statistics",
                "X processes Y per second",
                "X has 99% uptime",
                "X scales to Y",
            ),
            "comparison": (
                "Comparing alternatives or approaches",
                "X is faster than Y",
                "X vs Y",
                "Unlike X, Y does Z",
            ),
            "commercial": (
                "Business aspects - pricing, availability, licensing",
                "X costs Y per month",
                "Available in Z regions",
                "Licensed under MIT",
            ),
        }

        meta = metadata.get(claim_type.value, ("",))
        if len(meta) == 1:
            return meta[0]
        desc = meta[0]
        examples = ", ".join(f"'{ex}'" for ex in meta[1:])
        return f"{desc} (e.g., {examples})"

    @classmethod
    def get_all_descriptions(cls) -> str:
        """Get formatted descriptions for all claim types for use in prompts."""
        lines = []
        for claim_type in cls:
            desc = cls.get_description(claim_type)
            lines.append(f"             * {claim_type.value}: {desc}")
        return "\n".join(lines)

    @classmethod
    def get_extraction_guidelines(cls) -> str:
        """Get detailed extraction guidelines for claims."""
        return """
           - CRITICAL EXTRACTION RULES:
             * Extract 10-20 claims for technical documentation (not just 5-7)
             * VERBATIM CODE RULE: If you see SQL/code, extract it EXACTLY - character for character
             * For INSTRUCTION claims: ANY code in ```sql blocks → Extract THE ENTIRE CODE
             * NEVER summarize code as "You can use X" - extract the actual code
             * ALWAYS extract explanations of what things are (EXPLANATION or DEFINITION claims)
             * Key concepts/features MUST be entities in your entities list
             * Link claims to ALL relevant entities mentioned

           - EXAMPLES - What TO extract vs what NOT to extract:
             ❌ WRONG: "The embedding() function can be used to create embeddings" (vague capability)
             ✓ RIGHT: "SELECT embedding('Ducks are known for their distinctive quacking sound');" (exact instruction)

             ❌ WRONG: "You can use SELECT embedding with text" (summary)
             ✓ RIGHT: "SELECT embedding('text') AS text_embedding;" (exact SQL)

             ❌ WRONG: "Using CTAS is recommended" (vague)
             ✓ RIGHT: "CREATE TABLE embeddings AS SELECT id, embedding(text_column) AS vec FROM documents;" (exact SQL)
        """


class Claim(SQLModel, table=True):
    """Claims extracted from documents.

    A claim is a factual statement extracted from a document that can be:
    - Verified or contradicted by other sources
    - Linked to entities it describes
    - Tracked to its exact source location
    """

    __tablename__ = TableNames.GRAPH_CLAIMS

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Claim content
    statement: str = Field(index=True)  # The claim text
    claim_type: ClaimType = Field(index=True)  # Type of claim

    # Entity linkage (every claim must be about at least one entity)
    subject_entity_id: UUID = Field(foreign_key="graph_entities.id", index=True)  # Primary entity

    # Source tracking
    source_document_id: UUID = Field(foreign_key="documents.id", index=True)
    source_quote: str  # Exact quote from document containing the claim
    source_location_start: int  # Character offset start in document
    source_location_end: int  # Character offset end in document
    source_context: Optional[str] = None  # Surrounding context for disambiguation

    # Temporal information
    temporal_qualifier: Optional[str] = (
        None  # e.g., "as of v2.0", "since 2023", "deprecated in v3.0"
    )
    extracted_date: Optional[datetime] = None  # Date mentioned in the claim
    version_info: Optional[str] = None  # Version information if applicable

    # Confidence and validation
    extraction_confidence: float = Field(default=0.0)  # LLM confidence in extraction (0.0-1.0)
    source_authority: float = Field(default=0.5)  # Authority score of source (0.0-1.0)
    corroboration_score: float = Field(default=0.0)  # Score based on supporting claims (0.0-1.0)
    overall_confidence: float = Field(default=0.0)  # Combined confidence score (0.0-1.0)

    # Resolution status
    is_verified: bool = Field(default=False)  # Manually verified by user
    is_superseded: bool = Field(default=False)  # Replaced by newer claim
    superseded_by_id: Optional[UUID] = Field(default=None, foreign_key="graph_claims.id")

    # Vector embedding for similarity search
    embedding: Optional[bytes] = None  # 512-dim float32 vector (2048 bytes)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_with_git_commit: Optional[str] = None  # Git commit when claim was extracted


class ClaimEntity(SQLModel, table=True):
    """Junction table linking claims to additional entities they reference.

    While every claim has a primary subject_entity_id, claims often reference
    multiple entities. This table captures those additional relationships.
    """

    __tablename__ = TableNames.GRAPH_CLAIM_ENTITIES

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    claim_id: UUID = Field(foreign_key="graph_claims.id", index=True)
    entity_id: UUID = Field(foreign_key="graph_entities.id", index=True)

    # Role of entity in the claim
    entity_role: str = Field(default="referenced")  # subject, object, referenced, compared_to

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimRelationship(SQLModel, table=True):
    """Relationships between claims.

    Used to track:
    - Conflicting claims (IN_CONFLICT relationship)
    - Supporting claims
    - Derived claims
    - Temporal succession (newer version of claim)
    """

    __tablename__ = TableNames.GRAPH_CLAIM_RELATIONSHIPS

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_claim_id: UUID = Field(foreign_key="graph_claims.id", index=True)
    target_claim_id: UUID = Field(foreign_key="graph_claims.id", index=True)

    relationship_type: str = Field(index=True)  # in_conflict, supports, contradicts, supersedes

    # Conflict resolution
    resolution_status: Optional[str] = Field(default=None)  # pending, resolved, ignored
    resolved_by_user: Optional[str] = Field(default=None)  # Username who resolved
    resolution_notes: Optional[str] = Field(default=None)  # Notes on resolution
    resolved_at: Optional[datetime] = Field(default=None)

    # Confidence in relationship
    confidence: float = Field(default=0.0)  # Confidence in relationship (0.0-1.0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
