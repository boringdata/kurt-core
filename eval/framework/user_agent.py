"""DSPy-based user agent for simulating user responses in evaluation scenarios."""

from typing import Any, Dict, Optional

import dspy


class UserAgentResponse(dspy.Signature):
    """Simulate a user responding to an AI agent's question."""

    user_instructions = dspy.InputField(desc="Instructions for how the user should respond")
    conversation_history = dspy.InputField(desc="Previous conversation context")
    agent_question = dspy.InputField(desc="The question the agent just asked")
    user_response = dspy.OutputField(desc="Brief, direct user response (1-2 words max)")


def respond_with_dspy(
    agent_message: str,
    system_prompt: str,
    context: Dict[str, Any],
    provider: str = "openai",
) -> Optional[str]:
    """Generate response using DSPy LLM.

    Args:
        agent_message: The message from the agent
        system_prompt: Instructions for how the user should respond
        context: Current workspace context (includes conversation_history)
        provider: LLM provider - "openai" or "anthropic" (default: "openai")

    Returns:
        LLM-generated response string, or None if API fails

    Example:
        >>> response = respond_with_dspy(
        ...     "What is your project name?",
        ...     "When asked about project name: respond 'test-blog'",
        ...     {"conversation_history": []},
        ...     provider="openai"
        ... )
        >>> print(response)
        test-blog
    """
    try:
        import os
        from pathlib import Path

        # Load .env file from eval directory
        from dotenv import load_dotenv

        env_file = Path(__file__).parent.parent / ".env"  # eval/.env
        if env_file.exists():
            load_dotenv(env_file)
        else:
            import sys

            print(f"Warning: .env file not found at {env_file}", file=sys.stderr)

        # Configure DSPy with the selected provider
        if provider == "openai":
            # Use OpenAI (gpt-4o-mini is cheap and fast)
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                import sys

                print("Warning: OPENAI_API_KEY not set, user agent will fail", file=sys.stderr)
                return None

            lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key, max_tokens=100, temperature=0.3)

        elif provider == "anthropic":
            # Use Anthropic Claude
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                import sys

                print("Warning: ANTHROPIC_API_KEY not set, user agent will fail", file=sys.stderr)
                return None

            lm = dspy.LM(
                "anthropic/claude-3-5-haiku-20241022",
                api_key=api_key,
                max_tokens=100,
                temperature=0.3,
            )

        else:
            import sys

            print(f"Warning: Unknown LLM provider '{provider}'", file=sys.stderr)
            return None

        dspy.configure(lm=lm)

        # Build conversation history context
        history_context = ""
        if "conversation_history" in context and context["conversation_history"]:
            history_context = "\n\nConversation so far:\n"
            for turn in context["conversation_history"]:
                speaker = turn.get("speaker", "unknown")
                message = turn.get("message", "")
                history_context += f"{speaker.upper()}: {message}\n"

        # Use DSPy ChainOfThought
        responder = dspy.ChainOfThought(UserAgentResponse)
        result = responder(
            user_instructions=system_prompt,
            conversation_history=history_context or "No previous conversation",
            agent_question=agent_message,
        )

        return result.user_response.strip()

    except Exception as e:
        # Return None to trigger fallback
        import sys

        print(f"Warning: DSPy user agent failed ({e})", file=sys.stderr)
        return None
