"""DSPy-based conversation completion detection.

Provides intelligent detection of when a multi-turn conversation should end
by analyzing agent responses, conversation context, and workspace state.
"""

import dspy


class ConversationCompletionCheck(dspy.Signature):
    """Analyze if an AI agent's conversation turn indicates completion or requires continuation.

    Focus on the CONVERSATION FLOW, not workspace state. Determine:
    1. Is the agent asking a question that needs a user response?
    2. Has the agent clearly signaled task completion?
    3. Is the agent waiting for input vs. just providing information?
    """

    agent_message = dspy.InputField(desc="The most recent message from the AI agent")
    conversation_context = dspy.InputField(
        desc="Recent conversation turns showing the flow and progress"
    )

    is_asking_question = dspy.OutputField(
        desc="Boolean: true if agent is asking for user input, false if statement/completion"
    )
    reason = dspy.OutputField(
        desc="Brief explanation: what indicates question vs completion (one sentence)"
    )


def check_conversation_completion_with_llm(
    agent_message: str,
    conversation_history: list,
    provider: str = "openai",
) -> tuple[bool, str]:
    """Use DSPy LLM to determine if agent is asking a question.

    This is the intelligent fallback when simple heuristics are uncertain.
    Focuses purely on conversation flow analysis.

    Args:
        agent_message: The agent's most recent response
        conversation_history: List of recent conversation turns
        provider: LLM provider - "openai" or "anthropic" (default: "openai")

    Returns:
        Tuple of (is_asking_question, reason)
        - is_asking_question: True if agent is asking for user input
        - reason: Explanation for the decision

    Example:
        >>> is_asking, reason = check_conversation_completion_with_llm(
        ...     "Your project name:",
        ...     [{"speaker": "agent", "message": "Let me create your project..."}],
        ...     provider="openai"
        ... )
        >>> print(is_asking, reason)
        True "Agent is prompting for project name input"
    """
    try:
        import os
        from pathlib import Path

        from dotenv import load_dotenv

        # Load .env file from eval directory
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # Configure DSPy with the selected provider
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return None, "OpenAI API key not set", "low"

            lm = dspy.LM(
                "openai/gpt-4o-mini",
                api_key=api_key,
                max_tokens=150,
                temperature=0.2,  # Low temperature for consistency
            )

        elif provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return None, "Anthropic API key not set", "low"

            lm = dspy.LM(
                "anthropic/claude-3-5-haiku-20241022",
                api_key=api_key,
                max_tokens=150,
                temperature=0.2,
            )

        else:
            return None, f"Unknown LLM provider '{provider}'", "low"

        dspy.configure(lm=lm)

        # Build conversation context from recent turns
        context_summary = f"Recent conversation ({len(conversation_history)} turns):\n"

        # Include last 4 turns for context (limit to recent exchanges)
        for turn in conversation_history[-4:]:
            speaker = turn.get("speaker", "unknown")
            message = turn.get("message", "")[:150]  # Truncate very long messages
            context_summary += f"{speaker.upper()}: {message}\n"

        # Use DSPy ChainOfThought for reasoning
        completion_checker = dspy.ChainOfThought(ConversationCompletionCheck)
        result = completion_checker(
            agent_message=agent_message,
            conversation_context=context_summary.strip(),
        )

        # Parse boolean result
        is_asking_str = str(result.is_asking_question).strip().lower()
        is_asking_question = is_asking_str in ["true", "yes", "1"]

        return is_asking_question, result.reason.strip()

    except Exception as e:
        # Return None to indicate LLM check failed
        import sys

        print(f"Warning: DSPy completion check failed ({e})", file=sys.stderr)
        return None, str(e)


def should_continue_conversation(
    agent_message: str,
    conversation_history: list,
    llm_provider: str = "openai",
    use_llm_fallback: bool = True,
) -> tuple[bool, str]:
    """Two-tier system to determine if conversation should continue.

    Tier 1: Fast heuristics (pattern matching) - catches obvious cases
    Tier 2: LLM-based analysis (for uncertain cases) - intelligent fallback

    Args:
        agent_message: The agent's most recent response
        conversation_history: List of recent conversation turns
        llm_provider: LLM provider for tier 2 ("openai" or "anthropic")
        use_llm_fallback: Enable LLM fallback for uncertain cases (default: True)

    Returns:
        Tuple of (should_continue, reason)
        - should_continue: True if agent is asking question (continue conversation)
        - reason: Explanation for the decision

    Example:
        >>> should_continue, reason = should_continue_conversation(
        ...     "Project created successfully!",
        ...     []
        ... )
        >>> print(should_continue, reason)
        False "heuristic: Explicit completion signal detected"
    """
    text_lower = agent_message.lower().strip()

    # TIER 1: FAST HEURISTICS
    # ========================

    # 1. Strong question indicators (HIGHEST PRIORITY - always continue if asking question)
    # Question marks and question phrases override any completion signals
    strong_question_indicators = [
        "?",  # Question mark
        "would you like",
        "do you want",
        "please provide",
        "what would you",
        "what is your",
        "what's your",
        "which option",
        "how should i",
        "should i",
        "[press enter",  # Input prompts like [Press Enter to skip]
        "press enter to",
        "[enter to",
        "[skip",
        "can you provide",
        "let me know",
        "please enter",
        "please specify",
    ]
    if any(ind in text_lower for ind in strong_question_indicators):
        return True, "heuristic: Strong question indicator detected"

    # 2. Strong completion signals (high confidence - end conversation)
    # Only checked AFTER confirming no questions are being asked
    strong_completion_signals = [
        "task complete",
        "setup complete",
        "project created successfully",
        "all done",
        "finished",
        "ready to proceed",
        "project is ready",
        "you're all set",
        "successfully created",
        "completed successfully",
        "initialization complete",
        "setup is complete",
        "all set",
    ]
    if any(signal in text_lower for signal in strong_completion_signals):
        return False, "heuristic: Explicit completion signal detected"

    # 3. Input prompt patterns (medium confidence - likely a question)
    import re

    input_prompt_patterns = [
        r"your\s+\w+\s*:",  # "Your project name:"
        r"^\s*\*{0,2}\s*\w+\s+name\s*:\*{0,2}",  # "Project name:" or "**Project name:**"
        r"enter\s+(your\s+)?\w+",  # "Enter your project name"
        r"provide\s+(your\s+)?\w+",  # "Provide your email"
    ]
    has_input_prompt = any(re.search(pattern, text_lower) for pattern in input_prompt_patterns)

    if has_input_prompt:
        # Medium confidence - could be a question, but let's verify with LLM
        # if LLM fallback is enabled
        if not use_llm_fallback:
            return True, "heuristic: Input prompt pattern detected"
        # Otherwise fall through to LLM for intelligent analysis

    # TIER 2: LLM FALLBACK
    # ====================
    # If we reach here, heuristics are uncertain - use LLM for intelligent decision

    if not use_llm_fallback:
        # Default to continuing conversation if LLM fallback is disabled
        return True, "heuristic: Uncertain case, defaulting to continue"

    is_asking_question, reason = check_conversation_completion_with_llm(
        agent_message,
        conversation_history,
        provider=llm_provider,
    )

    if is_asking_question is None:
        # LLM failed - default to continuing conversation
        return True, f"llm_fallback_failed: {reason}, defaulting to continue"

    # LLM decision: continue if asking question, stop if not
    return is_asking_question, f"llm: {reason}"
