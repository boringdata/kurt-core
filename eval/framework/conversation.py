"""Conversation structures for multi-turn agent interactions.

Defines how scenarios can include user responses and simulate conversations.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional


@dataclass
class ConversationTurn:
    """A single turn in a conversation.

    Attributes:
        speaker: Who is speaking ('user' or 'agent')
        message: The message content
        expected_tools: Optional list of tools expected to be used (for agent turns)
        wait_for_completion: Whether to wait for agent to finish before next turn
    """

    speaker: Literal["user", "agent"]
    message: str
    expected_tools: Optional[List[str]] = None
    wait_for_completion: bool = True


@dataclass
class UserAgent:
    """Simulates user responses in a conversation.

    The UserAgent can provide pre-defined responses or use conditional logic
    to respond dynamically based on what the agent asks.

    Example:
        >>> user_agent = UserAgent(responses={
        ...     "goal": "Write a blog post",
        ...     "has_sources": "yes"
        ... })
        >>>
        >>> # When agent asks about goal:
        >>> response = user_agent.respond_to(
        ...     "What's your goal for this project?",
        ...     context={}
        ... )
        >>> # Returns: "Write a blog post"
    """

    # Pre-defined responses keyed by keywords
    responses: Dict[str, str] = field(default_factory=dict)

    # Custom response function for complex logic
    custom_responder: Optional[Callable[[str, Dict], str]] = None

    # Default response if no match found
    default_response: str = "yes"

    def respond_to(self, agent_message: str, context: Dict[str, Any]) -> str:
        """Generate a response to an agent message.

        Args:
            agent_message: The message from the agent
            context: Current workspace context

        Returns:
            User response string
        """
        # Try custom responder first
        if self.custom_responder:
            response = self.custom_responder(agent_message, context)
            if response:
                return response

        # Try keyword matching
        message_lower = agent_message.lower()
        for keyword, response in self.responses.items():
            if keyword.lower() in message_lower:
                return response

        # Fall back to default
        return self.default_response

    @staticmethod
    def simple(default: str = "yes") -> "UserAgent":
        """Create a simple user agent that always responds with the same answer.

        Args:
            default: The response to always give

        Returns:
            UserAgent instance
        """
        return UserAgent(default_response=default)


@dataclass
class Scenario:
    """Defines a complete test scenario.

    A scenario includes:
    - Name and description
    - Initial prompt or conversation flow
    - Optional user agent for multi-turn interactions
    - Assertions to validate results
    - Expected metrics

    Example:
        >>> scenario = Scenario(
        ...     name="basic_init",
        ...     description="Initialize a Kurt project",
        ...     initial_prompt="Initialize a new Kurt project",
        ...     assertions=[
        ...         FileExists("kurt.config"),
        ...         FileExists(".kurt/kurt.sqlite"),
        ...     ]
        ... )
    """

    # Scenario metadata
    name: str
    description: str

    # How to start (either simple prompt or full conversation)
    initial_prompt: Optional[str] = None
    conversation: Optional[List[ConversationTurn]] = None

    # User agent for responding to questions
    user_agent: Optional[UserAgent] = None

    # Validation
    assertions: List[Any] = field(default_factory=list)  # List of Assertion objects

    # Expected outcomes (for metrics comparison)
    expected_metrics: Dict[str, Any] = field(default_factory=dict)

    # Workspace setup options
    needs_claude_plugin: bool = True  # If True, installs .claude/ from kurt-demo (default: True)

    def __post_init__(self):
        """Validate scenario definition."""
        if not self.initial_prompt and not self.conversation:
            raise ValueError("Scenario must have either initial_prompt or conversation")

        if self.initial_prompt and self.conversation:
            raise ValueError("Scenario cannot have both initial_prompt and conversation")

    def get_conversation(self) -> List[ConversationTurn]:
        """Get the conversation turns for this scenario.

        Returns:
            List of conversation turns
        """
        if self.conversation:
            return self.conversation

        # Convert simple prompt to single turn
        if self.initial_prompt:
            return [
                ConversationTurn(
                    speaker="user", message=self.initial_prompt, wait_for_completion=True
                )
            ]

        return []
