"""Content generation workflow using DBOS for durability."""

import logging
import time
from pathlib import Path
from typing import Optional
from uuid import UUID

from dbos import DBOS

from .context import ContextBuilder
from .llm_client import ContentGenerator
from .models import ContentGenerationRequest, GeneratedContent, SourceReference

logger = logging.getLogger(__name__)


@DBOS.step()
def build_generation_context(request: ContentGenerationRequest) -> tuple[str, list[dict]]:
    """
    Build context from source documents and entities.

    This step is checkpointed - if the workflow crashes, it won't rebuild context.

    Args:
        request: Content generation request

    Returns:
        Tuple of (context_string, source_references_as_dicts)
    """
    logger.info("Building generation context...")

    builder = ContextBuilder(request)
    context_string, sources = builder.build_context()

    # Convert SourceReference objects to dicts for serialization
    sources_dict = [
        {
            "document_id": str(source.document_id),
            "document_title": source.document_title,
            "document_url": source.document_url,
            "relevance_score": source.relevance_score,
            "excerpts_used": source.excerpts_used,
        }
        for source in sources
    ]

    logger.info(f"Context built: {len(context_string)} chars, {len(sources)} sources")

    return context_string, sources_dict


@DBOS.step()
def generate_content_with_llm(
    request: ContentGenerationRequest,
    context_string: str,
) -> tuple[str, str, str, str, int]:
    """
    Generate content using LLM.

    This step is checkpointed - if the workflow crashes after LLM call,
    it won't call the LLM again.

    Args:
        request: Content generation request
        context_string: Context to provide to LLM

    Returns:
        Tuple of (title, content, sources_used, model_name, approximate_tokens)
    """
    logger.info(f"Generating content with {request.ai_provider}...")

    start_time = time.time()

    # Initialize generator
    generator = ContentGenerator(
        provider=request.ai_provider,
        model=request.ai_model,
    )

    # Build additional instructions
    instructions_parts = []
    if request.target_word_count:
        instructions_parts.append(f"Target word count: ~{request.target_word_count} words")
    if request.include_code_examples:
        instructions_parts.append("Include code examples where appropriate")
    if request.include_citations:
        instructions_parts.append("Cite sources using [Source: Title] format")

    additional_instructions = ". ".join(instructions_parts) if instructions_parts else ""

    # Generate content
    title, content, sources_used = generator.generate(
        goal=request.goal,
        format=request.format.value,
        tone=request.tone.value,
        source_context=context_string,
        additional_instructions=additional_instructions,
    )

    generation_time = time.time() - start_time

    # Estimate tokens (rough: 4 chars = 1 token)
    estimated_tokens = (len(context_string) + len(content) + len(title)) // 4

    logger.info(
        f"Content generated in {generation_time:.1f}s: "
        f"{len(content)} chars, ~{estimated_tokens} tokens"
    )

    return title, content, sources_used, generator.model, estimated_tokens


@DBOS.step()
def save_generated_content(
    output_path: Optional[str],
    content_markdown: str,
) -> Optional[str]:
    """
    Save generated content to file.

    Args:
        output_path: Where to save (None = don't save)
        content_markdown: Content to save

    Returns:
        Path where content was saved, or None
    """
    if not output_path:
        return None

    output_file = Path(output_path)

    # Create parent directories if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content_markdown)

    logger.info(f"Content saved to: {output_file}")

    return str(output_file.absolute())


@DBOS.workflow()
def generate_content_workflow(request_dict: dict) -> dict:
    """
    Main workflow for content generation.

    This workflow is durable and resumable - if it crashes at any point,
    it will resume from the last checkpoint.

    Args:
        request_dict: ContentGenerationRequest as dict (for serialization)

    Returns:
        GeneratedContent as dict
    """
    # Reconstruct request from dict
    request = ContentGenerationRequest(**request_dict)

    logger.info(f"Starting content generation: {request.goal}")

    # Step 1: Build context (checkpointed)
    context_string, sources_dict = build_generation_context(request)

    # Step 2: Generate content with LLM (checkpointed)
    title, content, sources_used, model_name, estimated_tokens = generate_content_with_llm(
        request, context_string
    )

    # Reconstruct SourceReference objects from dicts
    sources = [
        SourceReference(
            document_id=UUID(s["document_id"]),
            document_title=s["document_title"],
            document_url=s["document_url"],
            relevance_score=s["relevance_score"],
            excerpts_used=s["excerpts_used"],
        )
        for s in sources_dict
    ]

    # Count words
    word_count = len(content.split())

    # Create result object
    result = GeneratedContent(
        request=request,
        title=title,
        content=content,
        word_count=word_count,
        sources=sources,
        entities_used=request.source_entity_names,
        ai_provider=request.ai_provider,
        ai_model=model_name,
        tokens_used=estimated_tokens,
    )

    # Step 3: Save to file if requested (checkpointed)
    if request.output_path:
        content_markdown = result.to_markdown(include_metadata=request.add_frontmatter)
        saved_path = save_generated_content(request.output_path, content_markdown)
        logger.info(f"Workflow complete - saved to: {saved_path}")
    else:
        logger.info("Workflow complete - content not saved to file")

    # Return as dict for serialization
    return {
        "id": str(result.id),
        "title": result.title,
        "content": result.content,
        "word_count": result.word_count,
        "sources": [
            {
                "document_id": str(s.document_id),
                "document_title": s.document_title,
                "document_url": s.document_url,
            }
            for s in result.sources
        ],
        "ai_provider": result.ai_provider,
        "ai_model": result.ai_model,
        "tokens_used": result.tokens_used,
        "generated_at": result.generated_at.isoformat(),
    }
