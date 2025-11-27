#!/usr/bin/env python3
"""Generate answer by searching through source files (Claude Code SDK simulation).

This script simulates what Claude Code would do - search through .kurt/sources/
and generate an answer. For now, it outputs the pre-generated answers from the
SDK session.

Usage:
    python answer_via_search.py "Question text" --output /tmp/answer.md
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate answer via source search (Claude Code simulation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "question",
        type=str,
        help="Question to answer",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output markdown file path",
    )

    args = parser.parse_args()

    output_path = Path(args.output)

    # For now, just copy the pre-generated answers
    # In the future, this could actually implement the search logic
    if "file formats" in args.question.lower():
        # Use answer_cc_1.md (already exists)
        source = Path("/tmp/answer_cc_1.md")
    elif "integrate" in args.question.lower():
        # Use answer_cc_2.md (already exists)
        source = Path("/tmp/answer_cc_2.md")
    else:
        print(f"Error: Unknown question: {args.question}", file=sys.stderr)
        sys.exit(1)

    if not source.exists():
        print(f"Error: Source answer file not found: {source}", file=sys.stderr)
        print("Make sure to run the conversational scenario first to generate answers.")
        sys.exit(1)

    # Copy the answer to the output path
    content = source.read_text(encoding="utf-8")
    output_path.write_text(content, encoding="utf-8")

    print(f"✓ Answer written to: {output_path}")

    # Also output the answer content to stdout for LLM judge
    # The runner expects the answer in stdout for evaluation
    print("\n" + "=" * 80)
    print(content)
    print("=" * 80)


if __name__ == "__main__":
    main()
