"""LLM client for content generation using DSPy."""

import logging
from typing import Optional

import dspy

from kurt.config import get_config_or_default

logger = logging.getLogger(__name__)


def get_llm_client(provider: str = "anthropic", model: Optional[str] = None) -> dspy.LM:
    """
    Get configured LLM client for content generation.

    Args:
        provider: LLM provider (anthropic, openai, etc.)
        model: Specific model to use (defaults to provider default)

    Returns:
        Configured DSPy LM instance

    Raises:
        ValueError: If provider is not supported or configuration is missing
    """
    config = get_config_or_default()

    if provider == "anthropic":
        api_key = getattr(config, "ANTHROPIC_API_KEY", None)
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Set it in .env or export ANTHROPIC_API_KEY=your_key"
            )

        model = model or "claude-3-5-sonnet-20241022"
        logger.info(f"Initializing Anthropic LLM: {model}")

        return dspy.LM(
            model=f"anthropic/{model}",
            api_key=api_key,
            max_tokens=4096,
        )

    elif provider == "openai":
        api_key = getattr(config, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Set it in .env or export OPENAI_API_KEY=your_key"
            )

        model = model or "gpt-4-turbo-preview"
        logger.info(f"Initializing OpenAI LLM: {model}")

        return dspy.LM(
            model=f"openai/{model}",
            api_key=api_key,
            max_tokens=4096,
        )

    else:
        raise ValueError(
            f"Unsupported provider: {provider}. " f"Supported providers: anthropic, openai"
        )


class ContentWriter(dspy.Signature):
    """Generate high-quality content based on goal and source materials.

    You are an expert content writer creating professional B2B technical content.
    Use the provided source documents and context to write accurate, engaging content
    that achieves the stated goal.

    Follow these guidelines:
    - Write in the specified tone and format
    - Use source materials accurately and cite them when appropriate
    - Include specific examples and details from the sources
    - Structure content with clear headings and logical flow
    - Include code examples if requested and available in sources
    - Make content actionable and valuable for the reader
    """

    goal: str = dspy.InputField(
        desc="The purpose and objective of the content (what it should achieve)"
    )
    format: str = dspy.InputField(desc="Content format (blog-post, tutorial, guide, etc.)")
    tone: str = dspy.InputField(desc="Writing tone (professional, conversational, technical, etc.)")
    source_context: str = dspy.InputField(
        desc="Relevant excerpts from source documents to reference and build upon"
    )
    additional_instructions: str = dspy.InputField(
        desc="Additional requirements (word count, include code examples, etc.)"
    )

    title: str = dspy.OutputField(desc="Compelling title for the content")
    content: str = dspy.OutputField(
        desc="Full content in markdown format with proper structure and formatting"
    )
    sources_used: str = dspy.OutputField(
        desc="Comma-separated list of source document IDs/titles that were referenced"
    )


class ContentGenerator:
    """High-level content generation orchestrator using DSPy."""

    def __init__(self, provider: str = "anthropic", model: Optional[str] = None):
        """
        Initialize content generator.

        Args:
            provider: LLM provider to use
            model: Specific model to use
        """
        self.lm = get_llm_client(provider=provider, model=model)
        self.provider = provider
        self.model = model or self._get_default_model(provider)

    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider."""
        defaults = {
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4-turbo-preview",
        }
        return defaults.get(provider, "unknown")

    def generate(
        self,
        goal: str,
        format: str,
        tone: str,
        source_context: str,
        additional_instructions: str = "",
    ) -> tuple[str, str, str]:
        """
        Generate content using LLM.

        Args:
            goal: Content generation goal
            format: Content format
            tone: Writing tone
            source_context: Source material to reference
            additional_instructions: Additional requirements

        Returns:
            Tuple of (title, content, sources_used)
        """
        with dspy.context(lm=self.lm):
            writer = dspy.ChainOfThought(ContentWriter)

            result = writer(
                goal=goal,
                format=format,
                tone=tone,
                source_context=source_context,
                additional_instructions=additional_instructions or "None",
            )

            return result.title, result.content, result.sources_used
