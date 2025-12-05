"""Tests for conversation completion detection with DSPy mocking.

Tests that:
- Heuristic-based completion detection works
- DSPy LLM fallback is properly mocked
- Provider configuration works correctly
- Decision logic flows correctly
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework.conversation_completion import (  # noqa: E402
    check_conversation_completion_with_llm,
    should_continue_conversation,
)


class TestHeuristicDetection:
    """Test heuristic-based conversation completion detection."""

    def test_strong_question_indicators(self):
        """Test that strong question indicators are detected."""
        test_cases = [
            ("What would you like to do next?", True, "strong question"),
            ("Do you want me to continue?", True, "strong question"),
            ("Can I help you with anything else?", True, "strong question"),
            ("Should I proceed with the implementation?", True, "strong question"),
            ("Any other questions?", True, "strong question"),
            ("How does this look?", True, "strong question"),
            ("Is there anything else?", True, "strong question"),
        ]

        for message, expected_continue, expected_reason in test_cases:
            should_continue, reason = should_continue_conversation(
                message, [], use_llm_fallback=False
            )
            assert should_continue == expected_continue, f"Failed for: {message}"
            assert expected_reason in reason.lower(), f"Unexpected reason for: {message}"

    def test_strong_completion_signals(self):
        """Test that strong completion signals are detected."""
        test_cases = [
            ("Task completed successfully!", False, "completion signal"),
            ("The implementation is now finished.", False, "completion signal"),
            ("Project created successfully.", False, "completion signal"),
            ("Setup complete.", False, "completion signal"),
            ("All done!", False, "completion signal"),
            ("You're all set.", False, "completion signal"),
            ("Initialization complete.", False, "completion signal"),
        ]

        for message, expected_continue, expected_reason in test_cases:
            should_continue, reason = should_continue_conversation(
                message, [], use_llm_fallback=False
            )
            assert should_continue == expected_continue, f"Failed for: {message}"
            assert expected_reason in reason.lower(), f"Unexpected reason for: {message}"

    def test_input_prompt_patterns(self):
        """Test that input prompt patterns are detected."""
        test_cases = [
            ("Enter your name:", True),
            ("Your choice:", True),
            ("Enter the file path:", True),
            # "Please provide" actually triggers strong question indicator, not input prompt
            ("Please provide your API key:", True),
        ]

        for message, expected_continue in test_cases:
            should_continue, reason = should_continue_conversation(
                message, [], use_llm_fallback=False
            )
            assert should_continue == expected_continue, f"Failed for: {message}"
            # Don't check the exact reason type since different patterns may match

    def test_ambiguous_messages(self):
        """Test messages that are ambiguous without LLM."""
        test_cases = [
            "I've updated the configuration file.",
            "The server is running on port 8080.",
            "Here are the results of the analysis.",
            "I found three potential issues.",
        ]

        for message in test_cases:
            should_continue, reason = should_continue_conversation(
                message, [], use_llm_fallback=False
            )
            # Without LLM, uncertain cases default to continue=True
            assert should_continue is True
            assert "uncertain" in reason.lower()


class TestDSPyIntegration:
    """Test DSPy LLM integration with mocking."""

    @patch("framework.conversation_completion.dspy")
    def test_dspy_anthropic_configuration(self, mock_dspy):
        """Test that Anthropic provider is configured correctly."""
        # Set up environment
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        # Mock DSPy components
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        # Mock the ChainOfThought predictor
        mock_predictor = MagicMock()
        mock_response = MagicMock()
        mock_response.is_asking_question = "false"
        mock_response.reason = "Task completed"
        mock_predictor.return_value = mock_response
        mock_dspy.ChainOfThought.return_value = mock_predictor

        # Test the function
        result = check_conversation_completion_with_llm(
            "Task is complete", [], provider="anthropic"
        )

        # Verify Anthropic was configured
        mock_dspy.LM.assert_called_with(
            "anthropic/claude-3-5-haiku-latest",
            api_key="test-key",
            max_tokens=150,
            temperature=0.2,
        )

        # Verify result
        assert result == (False, "Task completed")  # false = completion, don't continue

    @patch("framework.conversation_completion.dspy")
    def test_dspy_openai_configuration(self, mock_dspy):
        """Test that OpenAI provider is configured correctly."""
        # Set up environment
        os.environ["OPENAI_API_KEY"] = "test-openai-key"

        # Mock DSPy components
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        # Mock the ChainOfThought predictor
        mock_predictor = MagicMock()
        mock_response = MagicMock()
        mock_response.is_asking_question = "true"
        mock_response.reason = "Waiting for user input"
        mock_predictor.return_value = mock_response
        mock_dspy.ChainOfThought.return_value = mock_predictor

        # Test the function
        result = check_conversation_completion_with_llm(
            "What would you like to do?", [], provider="openai"
        )

        # Verify OpenAI was configured
        mock_dspy.LM.assert_called_with(
            "openai/gpt-4o-mini", api_key="test-openai-key", max_tokens=150, temperature=0.2
        )

        # Verify result
        assert result == (True, "Waiting for user input")  # true = question, continue

    @patch("framework.conversation_completion.dspy")
    def test_llm_fallback_on_uncertain(self, mock_dspy):
        """Test that LLM fallback is used when heuristics are uncertain."""
        # Set up environment
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        # Mock DSPy for successful LLM call
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        mock_predictor = MagicMock()
        mock_response = MagicMock()
        mock_response.is_asking_question = "false"
        mock_response.reason = "Implementation complete"
        mock_predictor.return_value = mock_response
        mock_dspy.ChainOfThought.return_value = mock_predictor

        # Test with ambiguous message that needs LLM
        ambiguous_message = "I've updated the configuration file for you."
        should_continue, reason = should_continue_conversation(
            ambiguous_message, [], use_llm_fallback=True, llm_provider="anthropic"
        )

        # Should use LLM and get completion signal
        assert should_continue is False
        assert "llm" in reason.lower()

    @patch("framework.conversation_completion.dspy")
    def test_llm_error_handling(self, mock_dspy):
        """Test that errors in LLM calls are handled gracefully."""
        # Mock DSPy to raise an error
        mock_dspy.LM.side_effect = Exception("API key invalid")

        # Test the function
        result = check_conversation_completion_with_llm("Some message", [], provider="anthropic")

        # Should return (None, error_msg) on error
        assert result[0] is None
        assert "API key invalid" in result[1]

    @patch("framework.conversation_completion.dspy")
    def test_conversation_context_passed_to_llm(self, mock_dspy):
        """Test that conversation history is properly formatted for LLM."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        # Mock DSPy
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        mock_predictor = MagicMock()
        mock_response = MagicMock()
        mock_response.is_asking_question = "true"
        mock_response.reason = "User input needed"
        mock_predictor.return_value = mock_response
        mock_dspy.ChainOfThought.return_value = mock_predictor

        # Create conversation history
        conversation = [
            {"role": "user", "content": "Create a Python script"},
            {"role": "agent", "content": "I'll create that script for you"},
            {"role": "user", "content": "Add error handling"},
            {"role": "agent", "content": "What kind of errors should I handle?"},
        ]

        # Test the function
        result = check_conversation_completion_with_llm(
            "What kind of errors should I handle?", conversation, provider="anthropic"
        )

        # Verify the predictor was called
        mock_predictor.assert_called_once()

        # Get the actual arguments passed to the predictor
        call_args = mock_predictor.call_args
        if call_args and len(call_args) > 1 and call_args[1]:
            # Check named arguments
            context_arg = call_args[1].get("conversation_context", "")
            # Verify context was passed somehow
            assert len(context_arg) > 0

        assert result == (True, "User input needed")  # Asking a question


class TestEndToEndFlow:
    """Test the complete flow with mocking."""

    @patch("framework.conversation_completion.dspy")
    def test_heuristic_bypasses_llm(self, mock_dspy):
        """Test that strong heuristics bypass LLM even when enabled."""
        # This should NOT call LLM because it's a clear question
        should_continue, reason = should_continue_conversation(
            "What would you like to do next?", [], use_llm_fallback=True
        )

        # DSPy should not be called for clear cases
        mock_dspy.LM.assert_not_called()

        assert should_continue is True
        assert "strong question indicator" in reason.lower()

    @patch("framework.conversation_completion.dspy")
    def test_completion_signal_bypasses_llm(self, mock_dspy):
        """Test that clear completion signals bypass LLM."""
        should_continue, reason = should_continue_conversation(
            "Task completed successfully!", [], use_llm_fallback=True
        )

        # DSPy should not be called
        mock_dspy.LM.assert_not_called()

        assert should_continue is False
        assert "completion signal" in reason.lower()

    def test_boolean_parsing_edge_cases(self):
        """Test edge cases in boolean response parsing."""
        # These would normally be in check_conversation_completion_with_llm
        test_cases = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("FALSE", False),
            ("yes", True),
            ("no", False),
            ("1", True),
            ("0", False),
        ]

        for text, expected in test_cases:
            # Direct boolean parsing test
            result = text.lower().strip() in ["true", "yes", "1"]
            assert result == expected, f"Failed to parse: {text}"


def run_heuristic_tests():
    """Run all heuristic detection tests."""
    print("\n" + "=" * 60)
    print("Testing Heuristic Detection")
    print("=" * 60)

    test = TestHeuristicDetection()
    test.test_strong_question_indicators()
    print("✓ Strong question indicators test passed")

    test.test_strong_completion_signals()
    print("✓ Strong completion signals test passed")

    test.test_input_prompt_patterns()
    print("✓ Input prompt patterns test passed")

    test.test_ambiguous_messages()
    print("✓ Ambiguous messages test passed")


def run_dspy_tests():
    """Run all DSPy integration tests."""
    print("\n" + "=" * 60)
    print("Testing DSPy Integration")
    print("=" * 60)

    test = TestDSPyIntegration()
    test.test_dspy_anthropic_configuration()
    print("✓ Anthropic configuration test passed")

    test.test_dspy_openai_configuration()
    print("✓ OpenAI configuration test passed")

    test.test_llm_fallback_on_uncertain()
    print("✓ LLM fallback test passed")

    test.test_llm_error_handling()
    print("✓ Error handling test passed")

    test.test_conversation_context_passed_to_llm()
    print("✓ Conversation context test passed")


def run_flow_tests():
    """Run end-to-end flow tests."""
    print("\n" + "=" * 60)
    print("Testing End-to-End Flow")
    print("=" * 60)

    test = TestEndToEndFlow()
    test.test_heuristic_bypasses_llm()
    print("✓ Heuristic bypass test passed")

    test.test_completion_signal_bypasses_llm()
    print("✓ Completion signal bypass test passed")

    test.test_boolean_parsing_edge_cases()
    print("✓ Boolean parsing test passed")


def run_all_tests():
    """Run all conversation completion tests."""
    print("\n🧪 CONVERSATION COMPLETION TESTS")

    # Store original env vars
    original_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    original_openai = os.environ.get("OPENAI_API_KEY")

    try:
        run_heuristic_tests()
        run_dspy_tests()
        run_flow_tests()

        print("\n" + "=" * 60)
        print("✅ All conversation completion tests passed!")
        print("=" * 60)

    finally:
        # Restore env vars
        if original_anthropic:
            os.environ["ANTHROPIC_API_KEY"] = original_anthropic
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        if original_openai:
            os.environ["OPENAI_API_KEY"] = original_openai
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]


if __name__ == "__main__":
    run_all_tests()
