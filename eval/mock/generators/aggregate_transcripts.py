#!/usr/bin/env python3
"""Aggregate multiple conversational scenario transcripts into one master file.

This script:
1. Finds the latest transcript for each conversational scenario
2. Reads the answer files
3. Merges in LLM judge scores from evaluation_results.json
4. Combines everything into one aggregated markdown file

Usage:
    python aggregate_transcripts.py --scenario-prefix answer_motherduck_conversational_q --num-questions 10 --output full_transcript.md
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional


def find_latest_transcript(results_dir: Path, scenario_name: str) -> Optional[Path]:
    """Find the latest transcript markdown file for a scenario.

    Args:
        results_dir: Base results directory (eval/results/)
        scenario_name: Name of the scenario (e.g., answer_motherduck_conversational_q1)

    Returns:
        Path to the latest transcript markdown file, or None if not found
    """
    scenario_dir = results_dir / scenario_name

    if not scenario_dir.exists():
        return None

    # Find all markdown files (timestamped)
    md_files = sorted(scenario_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    return md_files[0] if md_files else None


def load_llm_judge_scores(evaluation_json: Path) -> Dict[str, Dict]:
    """Load LLM judge scores from evaluation_results.json.

    Args:
        evaluation_json: Path to evaluation_results.json

    Returns:
        Dictionary mapping question text to scores
    """
    if not evaluation_json.exists():
        return {}

    with open(evaluation_json) as f:
        data = json.load(f)

    scores_by_question = {}
    for result in data.get("question_results", []):
        question = result.get("question", "")
        scores = result.get("scores", {})
        scores_by_question[question] = scores

    return scores_by_question


def aggregate_transcripts(
    scenario_prefix: str,
    num_questions: int,
    output_file: Path,
    questions_file: Path,
    results_dir: Path = Path("eval/results"),
) -> None:
    """Aggregate all conversational transcripts into one master file.

    Args:
        scenario_prefix: Prefix for scenario names (e.g., "answer_motherduck_conversational_q")
        num_questions: Number of questions (scenarios)
        output_file: Output file path for aggregated transcript
        questions_file: Path to questions YAML file
        results_dir: Base results directory
    """
    # Load questions from YAML
    import yaml

    with open(questions_file) as f:
        questions_data = yaml.safe_load(f)

    questions = questions_data.get("questions", [])

    # Load LLM judge scores
    evaluation_dir = output_file.parent
    evaluation_json = evaluation_dir / "evaluation_results.json"
    scores_by_question = load_llm_judge_scores(evaluation_json)

    # Build aggregated content
    content = ["# Aggregated Transcript: MotherDuck Questions (Conversational Mode)\n\n"]
    content.append("**Status**: ✅ PASSED\n\n")
    content.append("---\n\n")

    for i in range(1, num_questions + 1):
        scenario_name = f"{scenario_prefix}{i}"
        question_data = questions[i - 1] if i <= len(questions) else {}
        question_text = question_data.get("question", f"Question {i}")

        content.append(f"## Question {i}\n\n")
        content.append(f"{question_text}\n\n")

        # Find and include the transcript
        transcript_path = find_latest_transcript(results_dir, scenario_name)
        if transcript_path:
            content.append("### Transcript\n\n")
            with open(transcript_path) as f:
                transcript_content = f.read()
            content.append(transcript_content)
            content.append("\n\n")
        else:
            content.append("⚠️  Transcript not found\n\n")

        # Include the answer
        answer_file = Path(f"/tmp/answer_conversational_{i}.md")
        if answer_file.exists():
            content.append("### Answer\n\n")
            with open(answer_file) as f:
                answer_content = f.read()
            content.append(answer_content)
            content.append("\n\n")
        else:
            content.append("⚠️  Answer file not found\n\n")

        # Include LLM judge scores
        if question_text in scores_by_question:
            scores = scores_by_question[question_text]
            content.append("### LLM Judge Evaluation\n\n")
            content.append(f"**Overall Score**: {scores.get('overall', 0):.2f}\n\n")
            content.append("**Component Scores**:\n")
            for component in ["accuracy", "completeness", "relevance", "clarity"]:
                if component in scores:
                    content.append(f"  - {component.capitalize()}: {scores[component]:.2f}\n")
            content.append("\n")
            feedback = scores.get("feedback", "")
            content.append(f"**Feedback**: {feedback}\n\n")
        else:
            content.append("⚠️  LLM judge scores not found\n\n")

        content.append("---\n\n")

    # Write aggregated file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write("".join(content))

    print(f"✓ Aggregated transcript written to: {output_file}")
    print(f"  - Combined {num_questions} questions")
    print(f"  - Included transcripts, answers, and LLM judge scores")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Aggregate conversational scenario transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenario-prefix",
        required=True,
        help="Prefix for scenario names (e.g., answer_motherduck_conversational_q)",
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        required=True,
        help="Number of questions to aggregate",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path for aggregated transcript",
    )
    parser.add_argument(
        "--questions-file",
        default="eval/scenarios/questions_motherduck.yaml",
        help="Path to questions YAML file (default: eval/scenarios/questions_motherduck.yaml)",
    )
    parser.add_argument(
        "--results-dir",
        default="eval/results",
        help="Base results directory (default: eval/results)",
    )

    args = parser.parse_args()

    aggregate_transcripts(
        scenario_prefix=args.scenario_prefix,
        num_questions=args.num_questions,
        output_file=Path(args.output),
        questions_file=Path(args.questions_file),
        results_dir=Path(args.results_dir),
    )


if __name__ == "__main__":
    main()
