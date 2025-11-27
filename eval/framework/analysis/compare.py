#!/usr/bin/env python3
"""Compare WITH KG vs WITHOUT KG approaches using per-question artifacts."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def collect_question_runs(results_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load the newest per-question JSON for each question id."""
    if not results_dir.exists():
        return {}

    latest: Dict[str, Dict[str, Any]] = {}

    for path in results_dir.glob("q*_*.json"):
        if not path.is_file():
            continue

        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue

        # Extract question_id from filename (e.g., "q1" from "q1_20251127_135755.json")
        # Since the JSON doesn't contain question_id, we parse it from the filename
        filename = path.stem  # e.g., "q1_20251127_135755"
        parts = filename.split("_")
        if parts and parts[0].startswith("q"):
            question_id = parts[0]  # e.g., "q1"
        else:
            continue

        # Add the question_id to the data
        data["question_id"] = question_id

        existing = latest.get(question_id)
        timestamp = path.stat().st_mtime
        if not existing or timestamp > existing["_timestamp"]:
            data["_source_file"] = str(path)
            data["_timestamp"] = timestamp
            latest[question_id] = data

    return latest


def load_questions(path: Path) -> List[Dict]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("questions", [])


def extract_score(entry: Optional[Dict[str, Any]]) -> Optional[float]:
    if not entry:
        return None
    judge = entry.get("llm_judge")
    if isinstance(judge, dict):
        score = judge.get("overall_score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def extract_usage(entry: Optional[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not entry:
        return None
    usage = entry.get("token_usage")
    if isinstance(usage, dict):
        return usage
    return None


def compute_summary(entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    scores = []
    tokens_total = 0.0
    duration_total = 0.0
    cached = 0

    for entry in entries.values():
        score = extract_score(entry)
        if score is not None:
            scores.append(score)

        usage = extract_usage(entry) or {}
        tokens = usage.get("total_tokens")
        if isinstance(tokens, (int, float)):
            tokens_total += float(tokens)
        duration = usage.get("duration_seconds")
        if isinstance(duration, (int, float)):
            duration_total += float(duration)

        if entry.get("cached_response"):
            cached += 1

    avg_score = sum(scores) / len(scores) if scores else 0.0
    return {
        "average_score": avg_score,
        "num_questions": len(entries),
        "tokens_total": tokens_total,
        "duration_total": duration_total,
        "cached_responses": cached,
        "passed": avg_score >= 0.7 if entries else False,
    }


# Removed format_summary_row as we no longer need a separate summary table


def generate_report(
    with_entries: Dict[str, Dict[str, Any]],
    without_entries: Dict[str, Dict[str, Any]],
    questions: List[Dict],
    output: Path,
):
    with_summary = compute_summary(with_entries)
    without_summary = compute_summary(without_entries)

    report_lines: List[str] = []
    report_lines.append("# GraphRAG vs Vector-only Comparison\n")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(
        f"Questions compared: {with_summary.get('num_questions', 0)} (with KG) / "
        f"{without_summary.get('num_questions', 0)} (without KG)\n"
    )

    report_lines.append("## Results Comparison\n")
    report_lines.append(
        "| # | With KG Score | With KG Time (s) | With KG Tokens | Without KG Score | Without KG Time (s) | Without KG Tokens | Δ Score |"
    )
    report_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    combined_rows: List[Dict[str, Any]] = []

    for idx, question in enumerate(questions, start=1):
        text = question.get("question", f"Question {idx}")
        question_id = question.get("id") or f"q{idx}"
        with_entry = with_entries.get(question_id)
        without_entry = without_entries.get(question_id)

        with_score = extract_score(with_entry)
        without_score = extract_score(without_entry)
        delta = None
        if with_score is not None and without_score is not None:
            delta = with_score - without_score

        # Extract usage data for with_kg
        with_usage = extract_usage(with_entry) or {}
        with_time = with_usage.get("duration_seconds")
        with_tokens = with_usage.get("total_tokens")
        with_time_str = f"{with_time:.1f}" if isinstance(with_time, (int, float)) else "N/A"
        with_tokens_str = (
            f"{int(with_tokens):,}" if isinstance(with_tokens, (int, float)) else "N/A"
        )

        # Extract usage data for without_kg
        without_usage = extract_usage(without_entry) or {}
        without_time = without_usage.get("duration_seconds")
        without_tokens = without_usage.get("total_tokens")
        without_time_str = (
            f"{without_time:.1f}" if isinstance(without_time, (int, float)) else "N/A"
        )
        without_tokens_str = (
            f"{int(without_tokens):,}" if isinstance(without_tokens, (int, float)) else "N/A"
        )

        delta_str = f"{delta:+.2f}" if delta is not None else "N/A"
        with_score_str = f"{with_score:.2f}" if with_score is not None else "N/A"
        without_score_str = f"{without_score:.2f}" if without_score is not None else "N/A"

        report_lines.append(
            f"| {idx} | "
            f"{with_score_str} | "
            f"{with_time_str} | "
            f"{with_tokens_str} | "
            f"{without_score_str} | "
            f"{without_time_str} | "
            f"{without_tokens_str} | "
            f"{delta_str} |"
        )

        combined_rows.append(
            {
                "question": text,
                "question_id": question_id,
                "with_kg": {
                    "score": with_score,
                    "usage": extract_usage(with_entry),
                    "cached": with_entry.get("cached_response") if with_entry else None,
                    "feedback": (with_entry or {}).get("llm_judge", {}).get("feedback")
                    if with_entry
                    else None,
                    "source": (with_entry or {}).get("_source_file"),
                },
                "without_kg": {
                    "score": without_score,
                    "usage": extract_usage(without_entry),
                    "cached": without_entry.get("cached_response") if without_entry else None,
                    "feedback": (without_entry or {}).get("llm_judge", {}).get("feedback")
                    if without_entry
                    else None,
                    "source": (without_entry or {}).get("_source_file"),
                },
                "delta": delta,
            }
        )

    # Add summary row with averages/totals
    report_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    report_lines.append(
        f"| **Avg/Total** | "
        f"**{with_summary.get('average_score', 0.0):.2f}** | "
        f"**{with_summary.get('duration_total', 0.0):.1f}** | "
        f"**{int(with_summary.get('tokens_total', 0)):,}** | "
        f"**{without_summary.get('average_score', 0.0):.2f}** | "
        f"**{without_summary.get('duration_total', 0.0):.1f}** | "
        f"**{int(without_summary.get('tokens_total', 0)):,}** | "
        f"**{(with_summary.get('average_score', 0.0) - without_summary.get('average_score', 0.0)):+.2f}** |"
    )

    report_lines.append("")
    report_lines.append("## Feedback Highlights\n")
    for idx, row in enumerate(combined_rows, start=1):
        report_lines.append(f"### Question {idx}: {row['question']}")
        with_feedback = row["with_kg"].get("feedback")
        without_feedback = row["without_kg"].get("feedback")
        if with_feedback:
            report_lines.append("**With KG:**")
            report_lines.append(with_feedback)
            report_lines.append("")
        if without_feedback:
            report_lines.append("**Without KG:**")
            report_lines.append(without_feedback)
            report_lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(report_lines), encoding="utf-8")

    payload = {
        "with_kg": {"questions": with_entries, "summary": with_summary},
        "without_kg": {"questions": without_entries, "summary": without_summary},
        "per_question": combined_rows,
        "generated_at": datetime.now().isoformat(),
    }
    output.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_report_from_dirs(
    with_dir: Path | str,
    without_dir: Path | str,
    questions_file: Path | str,
    output_file: Path | str,
) -> Path:
    with_path = Path(with_dir)
    without_path = Path(without_dir)
    questions_path = Path(questions_file)
    output_path = Path(output_file)

    questions = load_questions(questions_path)
    with_entries = collect_question_runs(with_path)
    without_entries = collect_question_runs(without_path)

    if not with_entries or not without_entries:
        raise ValueError(
            "Missing per-question results. Run the scenarios before generating the report."
        )

    generate_report(with_entries, without_entries, questions, output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Compare GraphRAG vs vector-only evaluations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--with-kg-dir",
        required=True,
        help="Results directory for the WITH KG scenario (e.g., eval/results/answer_motherduck_with_kg)",
    )
    parser.add_argument(
        "--without-kg-dir",
        required=True,
        help="Results directory for the WITHOUT KG scenario",
    )
    parser.add_argument(
        "--questions-file",
        default="eval/scenarios/questions_motherduck.yaml",
        help="YAML file containing the questions (used for ordering)",
    )
    parser.add_argument(
        "--output",
        default="eval/results/comparison_report.md",
        help="Output markdown file",
    )

    args = parser.parse_args()

    try:
        output_path = generate_report_from_dirs(
            args.with_kg_dir, args.without_kg_dir, args.questions_file, args.output
        )
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Comparison report written to {output_path}")
    print(f"💾 JSON summary written to {output_path.with_suffix('.json')}")


if __name__ == "__main__":
    main()
