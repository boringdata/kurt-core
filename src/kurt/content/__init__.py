"""Content module - answer generation and claim extraction."""

from kurt.content.answer_with_claims import (
    ClaimContext,
    answer_with_claims,
    explain_claim_conflicts,
    retrieve_claim_context,
)

__all__ = [
    "answer_with_claims",
    "explain_claim_conflicts",
    "retrieve_claim_context",
    "ClaimContext",
]
