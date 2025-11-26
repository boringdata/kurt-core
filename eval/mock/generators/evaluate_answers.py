#!/usr/bin/env python3
"""Evaluate answers written to markdown files by Claude Code.

This script:
1. Reads markdown answer files
2. Extracts answer content (excluding sources section)
3. Runs LLM judge evaluation against expected answers
4. Outputs metrics in JSON format for scenario results

Usage:
    python evaluate_answers.py --answer-files /tmp/answer_1.md /tmp/answer_2.md \
                                --questions-file scenarios/questions_motherduck.yaml \
                                --output-dir eval/results/answer_motherduck_without_kg
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import dspy
import yaml

# Add src to path to import kurt modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from kurt.config import load_config


class JudgeSignature(dspy.Signature):
    """Evaluate answer quality on multiple dimensions.

    Given a question, expected answer, and actual answer, score the quality
    on accuracy, completeness, relevance, and clarity.
    """

    question = dspy.InputField(desc="The question being answered")
    expected_answer = dspy.InputField(desc="The expected/reference answer")
    actual_answer = dspy.InputField(desc="The answer to evaluate")
    accuracy_score = dspy.OutputField(desc="Accuracy score (0.0-1.0)")
    completeness_score = dspy.OutputField(desc="Completeness score (0.0-1.0)")
    relevance_score = dspy.OutputField(desc="Relevance score (0.0-1.0)")
    clarity_score = dspy.OutputField(desc="Clarity score (0.0-1.0)")
    feedback = dspy.OutputField(desc="Brief explanation of the scores")


def extract_answer_from_markdown(md_file: Path) -> str:
    """Extract the answer content from a markdown file.

    The markdown file should have this structure:
    # Answer

    [Answer content]

    ## Sources

    [Sources list]

    ## Metadata (optional)

    [Metadata]

    This function extracts only the answer content, excluding the sources and metadata sections.

    Args:
        md_file: Path to markdown file

    Returns:
        Answer content as string
    """
    if not md_file.exists():
        raise FileNotFoundError(f"Answer file not found: {md_file}")

    content = md_file.read_text(encoding="utf-8")

    # Split by ## Sources or ## Metadata to exclude those sections
    answer_part = content
    for marker in ["## Sources", "## Metadata"]:
        if marker in answer_part:
            answer_part = answer_part.split(marker)[0]

    # Remove the "# Answer" header
    if "# Answer" in answer_part:
        answer_part = answer_part.split("# Answer", 1)[1]

    return answer_part.strip()


def evaluate_answer(
    question: str, expected_answer: str, actual_answer: str, llm_model: str
) -> dict[str, Any]:
    """Evaluate an answer using LLM judge.

    Args:
        question: The question being answered
        expected_answer: The expected/reference answer
        actual_answer: The answer to evaluate
        llm_model: LLM model to use for judging

    Returns:
        Dict with scores and feedback
    """
    # Configure DSPy with judge model
    lm = dspy.LM(model=llm_model)
    dspy.configure(lm=lm)

    # Run judge evaluation
    judge = dspy.ChainOfThought(JudgeSignature)

    try:
        result = judge(
            question=question,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
        )

        # Parse scores
        def parse_score(score_str: str) -> float:
            """Parse score string to float, clamped to [0, 1]."""
            try:
                score = float(score_str)
                return max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                return 0.5  # Default if parsing fails

        scores = {
            "accuracy": parse_score(result.accuracy_score),
            "completeness": parse_score(result.completeness_score),
            "relevance": parse_score(result.relevance_score),
            "clarity": parse_score(result.clarity_score),
            "feedback": str(result.feedback),
        }

        # Calculate weighted overall score
        # Weights: accuracy (0.4), completeness (0.3), relevance (0.2), clarity (0.1)
        scores["overall"] = (
            scores["accuracy"] * 0.4
            + scores["completeness"] * 0.3
            + scores["relevance"] * 0.2
            + scores["clarity"] * 0.1
        )

        return scores

    except Exception as e:
        print(f"Error during LLM judge evaluation: {e}", file=sys.stderr)
        return {
            "accuracy": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
            "clarity": 0.0,
            "overall": 0.0,
            "feedback": f"Evaluation failed: {e}",
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate answers from Claude Code using LLM judge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--answer-files",
        nargs="+",
        required=True,
        help="Markdown files containing answers",
    )
    parser.add_argument(
        "--questions-file",
        required=True,
        help="YAML file containing questions and expected answers",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write evaluation results",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model for judging (default: from config ANSWER_LLM_MODEL)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    llm_model = args.llm_model or config.ANSWER_LLM_MODEL

    print(f"Using LLM model for judging: {llm_model}")

    # Load questions file
    questions_file = Path(args.questions_file)
    if not questions_file.exists():
        print(f"Error: Questions file not found: {questions_file}", file=sys.stderr)
        sys.exit(1)

    with open(questions_file, "r") as f:
        questions_data = yaml.safe_load(f)

    questions = questions_data.get("questions", [])

    if len(args.answer_files) != len(questions):
        print(
            f"Error: Number of answer files ({len(args.answer_files)}) "
            f"does not match number of questions ({len(questions)})",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Evaluate each answer
    results = []
    for i, (answer_file_path, question_data) in enumerate(
        zip(args.answer_files, questions), start=1
    ):
        answer_file = Path(answer_file_path)
        question = question_data["question"]
        expected_answer = question_data["expected_answer"]

        print(f"\n{'='*80}")
        print(f"Evaluating Question {i}: {question}")
        print(f"{'='*80}")

        try:
            # Extract answer from markdown
            actual_answer = extract_answer_from_markdown(answer_file)
            print(f"\nExtracted answer ({len(actual_answer)} chars):")
            print(f"  {actual_answer[:200]}...")

            # Evaluate answer
            print(f"\nRunning LLM judge evaluation...")
            scores = evaluate_answer(question, expected_answer, actual_answer, llm_model)

            result = {
                "question_number": i,
                "question": question,
                "answer_file": str(answer_file),
                "actual_answer": actual_answer,
                "scores": scores,
            }

            results.append(result)

            # Print scores
            print(f"\n✓ Evaluation complete:")
            print(f"  Accuracy:     {scores['accuracy']:.2f}")
            print(f"  Completeness: {scores['completeness']:.2f}")
            print(f"  Relevance:    {scores['relevance']:.2f}")
            print(f"  Clarity:      {scores['clarity']:.2f}")
            print(f"  Overall:      {scores['overall']:.2f}")
            print(f"\nFeedback: {scores['feedback']}")

        except FileNotFoundError as e:
            print(f"\n✗ Error: {e}", file=sys.stderr)
            result = {
                "question_number": i,
                "question": question,
                "answer_file": str(answer_file),
                "error": str(e),
                "scores": {
                    "accuracy": 0.0,
                    "completeness": 0.0,
                    "relevance": 0.0,
                    "clarity": 0.0,
                    "overall": 0.0,
                    "feedback": f"File not found: {answer_file}",
                },
            }
            results.append(result)
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
            result = {
                "question_number": i,
                "question": question,
                "answer_file": str(answer_file),
                "error": str(e),
                "scores": {
                    "accuracy": 0.0,
                    "completeness": 0.0,
                    "relevance": 0.0,
                    "clarity": 0.0,
                    "overall": 0.0,
                    "feedback": f"Evaluation error: {e}",
                },
            }
            results.append(result)

    # Calculate aggregate metrics
    total_questions = len(results)
    total_overall = sum(r["scores"]["overall"] for r in results)
    average_overall = total_overall / total_questions if total_questions > 0 else 0.0

    aggregate = {
        "total_questions": total_questions,
        "average_overall_score": average_overall,
        "average_accuracy": sum(r["scores"]["accuracy"] for r in results) / total_questions,
        "average_completeness": sum(r["scores"]["completeness"] for r in results) / total_questions,
        "average_relevance": sum(r["scores"]["relevance"] for r in results) / total_questions,
        "average_clarity": sum(r["scores"]["clarity"] for r in results) / total_questions,
    }

    # Write results to JSON
    output_file = output_dir / "evaluation_results.json"
    output_data = {
        "llm_model": llm_model,
        "aggregate_metrics": aggregate,
        "question_results": results,
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"EVALUATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total questions:    {total_questions}")
    print(f"Average overall:    {average_overall:.2f}")
    print(f"Average accuracy:   {aggregate['average_accuracy']:.2f}")
    print(f"Average completeness: {aggregate['average_completeness']:.2f}")
    print(f"Average relevance:  {aggregate['average_relevance']:.2f}")
    print(f"Average clarity:    {aggregate['average_clarity']:.2f}")
    print(f"\nResults written to: {output_file}")


if __name__ == "__main__":
    main()
