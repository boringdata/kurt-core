#!/usr/bin/env python3
"""Test script for conversation completion detection.

Tests both tier 1 (heuristics) and tier 2 (LLM fallback) detection.
"""

import sys
from pathlib import Path

# Add eval framework to path
sys.path.insert(0, str(Path(__file__).parent))

from framework.conversation_completion import should_continue_conversation


def test_heuristics():
    """Test that heuristics catch obvious cases without LLM."""
    print("=" * 70)
    print("TIER 1: HEURISTIC TESTS (no LLM calls)")
    print("=" * 70)

    test_cases = [
        # Completion signals (should NOT continue)
        ("Project created successfully!", [], False, "completion signal"),
        ("All done! Your project is ready to go.", [], False, "completion signal"),
        ("Setup complete. You're all set!", [], False, "completion signal"),
        # Strong questions (should continue)
        ("What would you like to name your project?", [], True, "question mark"),
        ("Would you like to add sources?", [], True, "would you like"),
        ("Do you want to proceed?", [], True, "do you want"),
        ("Please provide your project name.", [], True, "please provide"),
        # Input prompts with [Press Enter] pattern
        ("**Documentation site:**\n[Press Enter to skip]", [], True, "[press enter] pattern"),
        ("Project name:\n[Enter to skip]", [], True, "[enter to] pattern"),
        ("Additional details:\nPress Enter to continue", [], True, "press enter to pattern"),
        # Mixed signals - question should override completion signal
        (
            "Profile creation complete!\n\nWould you like to continue?",
            [],
            True,
            "question overrides completion",
        ),
        (
            "✅ Successfully created project!\n\nWhat would you like to do next?",
            [],
            True,
            "question after completion",
        ),
        # Uncertain cases will need LLM
    ]

    passed = 0
    failed = 0

    for message, history, expected_continue, test_name in test_cases:
        try:
            should_continue, reason = should_continue_conversation(
                message,
                history,
                use_llm_fallback=False,  # Test heuristics only
            )

            status = "✅" if should_continue == expected_continue else "❌"
            if should_continue == expected_continue:
                passed += 1
            else:
                failed += 1

            print(f"\n{status} {test_name}")
            print(f"   Message: {message[:60]}...")
            print(f"   Expected: {'CONTINUE' if expected_continue else 'STOP'}")
            print(f"   Got: {'CONTINUE' if should_continue else 'STOP'}")
            print(f"   Reason: {reason}")

        except Exception as e:
            print(f"\n❌ {test_name} - ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"HEURISTIC TESTS: {passed} passed, {failed} failed")
    print(f"{'=' * 70}\n")

    return failed == 0


def test_llm_fallback():
    """Test LLM fallback for uncertain cases."""
    print("=" * 70)
    print("TIER 2: LLM FALLBACK TESTS")
    print("=" * 70)

    # Uncertain cases where heuristics aren't sure
    test_cases = [
        # Input prompts without question marks
        (
            "Your project name:",
            [
                {"speaker": "agent", "message": "Let me help you create a project."},
                {"speaker": "user", "message": "Yes please"},
            ],
            True,
            "input prompt without question mark",
        ),
        (
            "**Project name:** (kebab-case)\nYour project name:",
            [
                {"speaker": "agent", "message": "I'll guide you through project creation."},
            ],
            True,
            "formatted input prompt",
        ),
        # Summary without questions
        (
            "I've created your project with the following structure:\n"
            "- projects/test-blog/\n"
            "- projects/test-blog/project.md\n"
            "- projects/test-blog/sources/",
            [
                {"speaker": "user", "message": "Create a blog project called test-blog"},
                {"speaker": "agent", "message": "Creating your project..."},
            ],
            False,
            "completion summary",
        ),
        # Statement after completion
        (
            "Your project is now set up in projects/test-blog/",
            [
                {"speaker": "user", "message": "test-blog"},
                {"speaker": "agent", "message": "Creating directories..."},
            ],
            False,
            "informational statement",
        ),
    ]

    passed = 0
    failed = 0

    for message, history, expected_continue, test_name in test_cases:
        try:
            should_continue, reason = should_continue_conversation(
                message,
                history,
                use_llm_fallback=True,  # Enable LLM
            )

            status = "✅" if should_continue == expected_continue else "❌"
            if should_continue == expected_continue:
                passed += 1
            else:
                failed += 1

            print(f"\n{status} {test_name}")
            print(f"   Message: {message[:60]}...")
            print(f"   Expected: {'CONTINUE' if expected_continue else 'STOP'}")
            print(f"   Got: {'CONTINUE' if should_continue else 'STOP'}")
            print(f"   Reason: {reason}")

        except Exception as e:
            print(f"\n❌ {test_name} - ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"LLM FALLBACK TESTS: {passed} passed, {failed} failed")
    print(f"{'=' * 70}\n")

    return failed == 0


def main():
    """Run all tests."""
    print("\n🧪 Testing Conversation Completion Detection\n")

    # Test heuristics first (fast, no API calls)
    heuristics_passed = test_heuristics()

    # Ask before running LLM tests (requires API key)
    print("\n" + "=" * 70)
    print("LLM fallback tests require OpenAI API key in eval/.env")
    response = input("Run LLM tests? (y/n): ").strip().lower()

    if response == "y":
        llm_passed = test_llm_fallback()
    else:
        print("Skipping LLM tests.")
        llm_passed = True

    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Heuristics: {'✅ PASSED' if heuristics_passed else '❌ FAILED'}")
    print(f"LLM Fallback: {'✅ PASSED' if llm_passed else '❌ FAILED (or skipped)'}")

    if heuristics_passed and llm_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
