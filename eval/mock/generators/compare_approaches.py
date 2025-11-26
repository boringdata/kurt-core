#!/usr/bin/env python3
"""Compare WITH KG vs WITHOUT KG approaches using LLM judge evaluations.

This script:
1. Reads the latest timestamped results from eval/results/ directories
2. Extracts LLM judge evaluation metrics from JSON files
3. Generates a comparison report with side-by-side metrics
4. Outputs markdown report showing which approach performed better

The judge evaluations are already computed by judge_answer.py during
post_scenario_commands, so this script just aggregates and compares them.

Usage:
    python compare_approaches.py \\
        --results-dir eval/results \\
        --output eval/results/comparison_report.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def find_latest_result(scenario_dir: Path) -> Optional[Path]:
    """Find the latest timestamped JSON file in a scenario results directory.

    Args:
        scenario_dir: Path to scenario results directory

    Returns:
        Path to latest JSON file, or None if not found
    """
    if not scenario_dir.exists():
        return None

    json_files = list(scenario_dir.glob("*.json"))
    if not json_files:
        return None

    # Return the most recently modified JSON file
    return max(json_files, key=lambda p: p.stat().st_mtime)


def load_judge_evaluation(json_file: Path) -> Optional[Dict]:
    """Load LLM judge evaluation from a JSON results file.

    Args:
        json_file: Path to JSON results file

    Returns:
        Judge evaluation dict, or None if not found
    """
    if not json_file or not json_file.exists():
        return None

    try:
        with open(json_file) as f:
            data = json.load(f)

        # Extract judge evaluation
        return data.get("llm_judge_evaluation")

    except Exception as e:
        print(f"Warning: Failed to load judge evaluation from {json_file}: {e}")
        return None


def load_answer_file(scenario_dir: Path) -> Optional[str]:
    """Load the latest answer markdown file from a scenario directory.

    Args:
        scenario_dir: Path to scenario results directory

    Returns:
        Answer content as string, or None if not found
    """
    if not scenario_dir.exists():
        return None

    answer_files = list(scenario_dir.glob("*_answer.md"))
    if not answer_files:
        return None

    # Get the most recently modified answer file
    latest_answer = max(answer_files, key=lambda p: p.stat().st_mtime)

    try:
        return latest_answer.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to read answer file {latest_answer}: {e}")
        return None


def collect_results(results_dir: Path, approach: str, num_questions: int) -> List[Dict]:
    """Collect all judge evaluations for an approach.

    Args:
        results_dir: Base results directory
        approach: Either 'with_kg' or 'without_kg'
        num_questions: Number of questions to collect

    Returns:
        List of result dicts with judge evaluations
    """
    results = []

    for q_num in range(1, num_questions + 1):
        scenario_name = f"answer_motherduck_{approach}_q{q_num}"
        scenario_dir = results_dir / scenario_name

        # Find latest JSON file
        json_file = find_latest_result(scenario_dir)

        # Load judge evaluation
        judge_eval = load_judge_evaluation(json_file)

        # Load answer file
        answer_text = load_answer_file(scenario_dir)

        result = {
            "question_num": q_num,
            "scenario_name": scenario_name,
            "json_file": str(json_file) if json_file else None,
            "judge_evaluation": judge_eval,
            "answer_text": answer_text,
            "has_evaluation": judge_eval is not None,
        }

        results.append(result)

    return results


def calculate_averages(results: List[Dict]) -> Dict[str, float]:
    """Calculate average scores from judge evaluations.

    Args:
        results: List of result dicts with judge evaluations

    Returns:
        Dict with average scores
    """
    # Filter results that have evaluations
    valid_results = [r for r in results if r["has_evaluation"]]

    if not valid_results:
        return {
            "accuracy": 0.0,
            "completeness": 0.0,
            "clarity": 0.0,
            "overall": 0.0,
            "count": 0,
        }

    n = len(valid_results)

    return {
        "accuracy": sum(r["judge_evaluation"]["accuracy"]["score"] for r in valid_results) / n,
        "completeness": sum(r["judge_evaluation"]["completeness"]["score"] for r in valid_results) / n,
        "clarity": sum(r["judge_evaluation"]["clarity"]["score"] for r in valid_results) / n,
        "overall": sum(r["judge_evaluation"]["overall"]["score"] for r in valid_results) / n,
        "count": n,
    }


def generate_comparison_report(
    with_kg_results: List[Dict],
    without_kg_results: List[Dict],
    questions: List[Dict],
    output_file: Path,
):
    """Generate markdown comparison report.

    Args:
        with_kg_results: Results for WITH KG approach
        without_kg_results: Results for WITHOUT KG approach
        questions: List of question data from questions_motherduck.yaml
        output_file: Path to write the report
    """
    # Calculate aggregate metrics
    with_kg_avg = calculate_averages(with_kg_results)
    without_kg_avg = calculate_averages(without_kg_results)

    # Generate report
    report = []
    report.append("# GraphRAG vs Vector-Only Comparison Report\n\n")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Total Questions:** {len(questions)}\n")
    report.append(f"**WITH KG Evaluations:** {with_kg_avg['count']}/{len(questions)}\n")
    report.append(f"**WITHOUT KG Evaluations:** {without_kg_avg['count']}/{len(questions)}\n\n")

    # Summary table
    report.append("## Summary\n\n")
    report.append("| Metric | WITH KG (GraphRAG) | WITHOUT KG (Vector-Only) | Difference | Winner |\n")
    report.append("|--------|--------------------|--------------------------|------------|--------|\n")

    for metric in ["accuracy", "completeness", "clarity", "overall"]:
        with_score = with_kg_avg[metric]
        without_score = without_kg_avg[metric]
        diff = with_score - without_score
        diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"

        if abs(diff) < 1.0:  # Less than 1 point difference
            winner = "TIE"
        elif diff > 0:
            winner = "**WITH KG** ✓"
        else:
            winner = "**WITHOUT KG** ✓"

        report.append(
            f"| {metric.title()} | {with_score:.1f}/100 | {without_score:.1f}/100 | {diff_str} | {winner} |\n"
        )

    # Overall winner
    report.append("\n### Overall Winner\n\n")
    if with_kg_avg["overall"] > without_kg_avg["overall"] + 1.0:
        report.append("**WITH KG (GraphRAG)** performs better overall.\n\n")
    elif without_kg_avg["overall"] > with_kg_avg["overall"] + 1.0:
        report.append("**WITHOUT KG (Vector-Only)** performs better overall.\n\n")
    else:
        report.append("Both approaches perform **similarly** overall.\n\n")

    # Per-question breakdown
    report.append("## Per-Question Analysis\n\n")

    for i, (q_data, with_result, without_result) in enumerate(
        zip(questions, with_kg_results, without_kg_results), start=1
    ):
        question = q_data["question"]
        report.append(f"### Question {i}: {question}\n\n")

        # Check if both have evaluations
        if not with_result["has_evaluation"] or not without_result["has_evaluation"]:
            report.append("⚠️ **Missing evaluation data**\n\n")
            if not with_result["has_evaluation"]:
                report.append(f"- WITH KG: No evaluation found\n")
            if not without_result["has_evaluation"]:
                report.append(f"- WITHOUT KG: No evaluation found\n")
            report.append("\n---\n\n")
            continue

        with_eval = with_result["judge_evaluation"]
        without_eval = without_result["judge_evaluation"]

        # Scores table
        report.append("| Metric | WITH KG | WITHOUT KG | Difference |\n")
        report.append("|--------|---------|------------|------------|\n")

        for metric in ["accuracy", "completeness", "clarity", "overall"]:
            with_score = with_eval[metric]["score"] if metric != "overall" else with_eval[metric]["score"]
            without_score = without_eval[metric]["score"] if metric != "overall" else without_eval[metric]["score"]
            diff = with_score - without_score
            diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"

            # Add emoji for winner
            if abs(diff) < 1.0:
                emoji = "="
            elif diff > 0:
                emoji = "✓"
            else:
                emoji = "✗"

            report.append(
                f"| {metric.title()} | {with_score:.1f}/100 {emoji if diff > 0 else ''} | "
                f"{without_score:.1f}/100 {emoji if diff < 0 else ''} | {diff_str} |\n"
            )

        # Summaries
        report.append("\n**WITH KG Summary:**\n")
        report.append(f"> {with_eval['overall']['summary']}\n\n")

        report.append("**WITHOUT KG Summary:**\n")
        report.append(f"> {without_eval['overall']['summary']}\n\n")

        # Reasoning
        report.append("<details>\n<summary>Detailed Reasoning</summary>\n\n")

        report.append("**WITH KG:**\n")
        report.append(f"- Accuracy: {with_eval['accuracy']['reasoning']}\n")
        report.append(f"- Completeness: {with_eval['completeness']['reasoning']}\n")
        report.append(f"- Clarity: {with_eval['clarity']['reasoning']}\n\n")

        report.append("**WITHOUT KG:**\n")
        report.append(f"- Accuracy: {without_eval['accuracy']['reasoning']}\n")
        report.append(f"- Completeness: {without_eval['completeness']['reasoning']}\n")
        report.append(f"- Clarity: {without_eval['clarity']['reasoning']}\n\n")

        report.append("</details>\n\n")
        report.append("---\n\n")

    # Write report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("".join(report), encoding="utf-8")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare WITH KG vs WITHOUT KG approaches using judge evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("eval/results"),
        help="Base results directory (default: eval/results)",
    )
    parser.add_argument(
        "--questions-file",
        type=Path,
        default=Path("eval/scenarios/questions_motherduck.yaml"),
        help="YAML file with questions (default: eval/scenarios/questions_motherduck.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/comparison_report.md"),
        help="Output markdown file (default: eval/results/comparison_report.md)",
    )

    args = parser.parse_args()

    print("🔍 GraphRAG vs Vector-Only Comparison")
    print("=" * 80)

    # Load questions file
    if not args.questions_file.exists():
        print(f"❌ Questions file not found: {args.questions_file}")
        sys.exit(1)

    with open(args.questions_file) as f:
        questions_data = yaml.safe_load(f)

    questions = questions_data.get("questions", [])
    num_questions = len(questions)

    print(f"📋 Loaded {num_questions} questions from {args.questions_file}")

    # Collect WITH KG results
    print(f"\n📊 Collecting WITH KG results...")
    with_kg_results = collect_results(args.results_dir, "with_kg", num_questions)

    with_kg_found = sum(1 for r in with_kg_results if r["has_evaluation"])
    print(f"   Found {with_kg_found}/{num_questions} judge evaluations")

    # Collect WITHOUT KG results
    print(f"\n📊 Collecting WITHOUT KG results...")
    without_kg_results = collect_results(args.results_dir, "without_kg", num_questions)

    without_kg_found = sum(1 for r in without_kg_results if r["has_evaluation"])
    print(f"   Found {without_kg_found}/{num_questions} judge evaluations")

    # Check if we have any results
    if with_kg_found == 0 and without_kg_found == 0:
        print("\n❌ No judge evaluations found in either approach!")
        print(f"   Results directory: {args.results_dir.absolute()}")
        print("\n   Make sure to run the scenarios first with judge evaluation enabled.")
        sys.exit(1)

    # Generate comparison report
    print(f"\n📝 Generating comparison report...")
    generate_comparison_report(with_kg_results, without_kg_results, questions, args.output)

    print(f"✅ Comparison report written to: {args.output}")

    # Save JSON results
    json_output = args.output.with_suffix(".json")
    json_data = {
        "generated_at": datetime.now().isoformat(),
        "num_questions": num_questions,
        "with_kg_results": with_kg_results,
        "without_kg_results": without_kg_results,
        "with_kg_averages": calculate_averages(with_kg_results),
        "without_kg_averages": calculate_averages(without_kg_results),
    }

    # Remove answer_text from JSON (too verbose)
    for result in json_data["with_kg_results"] + json_data["without_kg_results"]:
        result.pop("answer_text", None)

    with open(json_output, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"✅ JSON results written to: {json_output}")
    print("\n✨ Comparison complete!")


if __name__ == "__main__":
    main()
