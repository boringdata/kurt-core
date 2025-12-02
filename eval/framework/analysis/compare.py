#!/usr/bin/env python3
"""Compare WITH KG vs WITHOUT KG approaches using per-question artifacts."""

import argparse
import csv
import json
import re
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


def extract_sources_from_answer(answer_text: str, scenario_name: str = "") -> str:
    """Extract source information from answer markdown.

    For with_kg scenarios, returns the full Sources section including docs, entities, and KG info.
    For other scenarios, returns just the source file paths.
    """

    # Special handling for with_kg scenario - get full Sources section
    if "with_kg" in scenario_name and "## Sources" in answer_text:
        sources_section = answer_text.split("## Sources")[1]
        # Stop at the next major section (## Metadata or end)
        if "## Metadata" in sources_section:
            sources_section = sources_section.split("## Metadata")[0]

        # Clean up the formatting for CSV display
        # Remove extra newlines and format nicely
        lines = sources_section.strip().split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                # Replace markdown formatting for better CSV display
                line = line.replace("**", "")  # Remove bold
                line = line.replace("###", "[")  # Convert subsection headers
                if line.startswith("["):
                    line = line + "]"
                cleaned_lines.append(line)

        # Join with semicolon for CSV format (escape pipes for CSV)
        full_sources = "; ".join(cleaned_lines)
        # Escape pipe characters since we use pipe as delimiter
        full_sources = full_sources.replace("|", "\\|")
        return full_sources

    # Default behavior for other scenarios - extract individual sources
    sources = []

    # Look for the Sources section (both ## Sources and ### Documents Used)
    if "## Sources" in answer_text or "### Documents Used" in answer_text:
        # Try to find the sources section
        sources_section = ""

        # First try "### Documents Used" (with_kg format)
        if "### Documents Used" in answer_text:
            sources_section = answer_text.split("### Documents Used")[1]
            # Stop at the next section if any
            if "###" in sources_section:
                sources_section = sources_section.split("###")[0]
            elif "##" in sources_section:
                sources_section = sources_section.split("##")[0]
        # Then try "## Sources" (general format)
        elif "## Sources" in answer_text:
            sources_section = answer_text.split("## Sources")[1]
            # Stop at the next section if any
            if "## " in sources_section:
                sources_section = sources_section.split("## ")[0]

        # Extract sources from list items
        for line in sources_section.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                # Try to extract file paths first
                patterns = [
                    r"\.kurt/sources/[^\s\)]+",  # Direct path format
                    r"path:\s*\.kurt/sources/[^\s\)]+",  # Path in parentheses format
                ]

                found_path = False
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        path = match.group(0).replace("path:", "").strip()
                        if path not in sources:
                            sources.append(path)
                        found_path = True
                        break

                # If no path found, extract document name (for with_kg format)
                if not found_path:
                    # Format: "- Document Name (relevance: 0.95)"
                    # Remove leading dash and extract up to parenthesis
                    source = line.lstrip("- ").strip()
                    if "(relevance:" in source:
                        source = source.split("(relevance:")[0].strip()
                    if source and source not in sources and not source.startswith("#"):
                        sources.append(source)

    return "; ".join(sources) if sources else ""


def calculate_source_overlap(sources1_str: str, sources2_str: str) -> str:
    """Calculate overlap between two sets of sources."""

    # Extract document names from sources strings
    def extract_doc_names(sources_str):
        docs = set()
        if not sources_str:
            return docs

        # For with_kg format, extract from the full sources string
        if "[ Documents Used]" in sources_str:
            # Split by semicolon and look for document names
            parts = sources_str.split(";")
            for part in parts:
                part = part.strip()
                if ".md" in part and not part.startswith("["):
                    # Extract just the filename
                    if "/" in part:
                        doc_name = part.split("/")[-1].replace(".md", "").strip()
                    else:
                        doc_name = part.replace(".md", "").strip()
                    # Remove relevance scores if present
                    if "(relevance:" in doc_name:
                        doc_name = doc_name.split("(relevance:")[0].strip()
                    docs.add(doc_name)
        else:
            # For without_kg format, extract from semicolon-separated paths
            parts = sources_str.split(";")
            for part in parts:
                part = part.strip()
                if ".md" in part:
                    # Extract just the filename from the path
                    doc_name = part.split("/")[-1].replace(".md", "").strip()
                    docs.add(doc_name)

        return docs

    docs1 = extract_doc_names(sources1_str)
    docs2 = extract_doc_names(sources2_str)

    if not docs1 and not docs2:
        return "N/A"

    # Calculate overlap
    common = docs1 & docs2
    unique_to_1 = docs1 - docs2
    unique_to_2 = docs2 - docs1

    overlap_pct = (len(common) / max(len(docs1), len(docs2), 1)) * 100 if (docs1 or docs2) else 0

    return f"{overlap_pct:.0f}% ({len(common)} common, {len(unique_to_1)} unique to with_kg, {len(unique_to_2)} unique to without_kg)"


def generate_report(
    with_entries: Dict[str, Dict[str, Any]],
    without_entries: Dict[str, Dict[str, Any]],
    questions: List[Dict],
    output: Path,
):
    """Generate both markdown report and CSV with one line per scenario per question."""
    with_summary = compute_summary(with_entries)
    without_summary = compute_summary(without_entries)

    # Build CSV data with one line per scenario per question
    csv_rows = []

    for idx, question in enumerate(questions, start=1):
        question_text = question.get("question", f"Question {idx}")
        question_id = question.get("id") or f"q{idx}"

        # Process with_kg scenario
        with_entry = with_entries.get(question_id)
        if with_entry:
            # Read answer file if specified
            answer_text = with_entry.get("answer", "")
            answer_file = with_entry.get("answer_file", "")
            if answer_file:
                answer_path = Path(answer_file)
                if answer_path.exists():
                    with open(answer_path) as f:
                        answer_text = f.read()

            # Extract sources for with_kg
            sources = extract_sources_from_answer(answer_text, "answer_motherduck_with_kg")

            # Clean answer for CSV
            clean_answer = answer_text
            if "## Sources" in clean_answer:
                clean_answer = clean_answer.split("## Sources")[0]
            if "## Metadata" in clean_answer:
                clean_answer = clean_answer.split("## Metadata")[0]

            # Remove markdown formatting
            clean_answer = re.sub(r"^#\s*Answer\s*\n+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"^#+\s+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"\n#+\s+", " ", clean_answer)
            clean_answer = re.sub(r"\*\*(.*?)\*\*", r"\1", clean_answer)
            clean_answer = re.sub(r"\*(.*?)\*", r"\1", clean_answer)
            clean_answer = re.sub(r"```[\s\S]*?```", "", clean_answer)
            clean_answer = re.sub(r"`([^`]+)`", r"\1", clean_answer)
            clean_answer = re.sub(r"^\s*[-*+]\s+", "• ", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"^\s*\d+\.\s+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"\n\s*\n", " ", clean_answer)
            clean_answer = re.sub(r"\n", " ", clean_answer)
            clean_answer = re.sub(r"\s+", " ", clean_answer)
            clean_answer = clean_answer.strip()
            clean_answer = clean_answer.replace("|", "\\|")

            if len(clean_answer) > 500:
                clean_answer = clean_answer[:497] + "..."

            llm_judge = with_entry.get("llm_judge", {})
            token_usage = with_entry.get("token_usage", {})

            csv_rows.append(
                {
                    "question_num": idx,
                    "scenario": "answer_motherduck_with_kg",
                    "question": question_text,
                    "answer": clean_answer,
                    "answer_file": answer_file,
                    "sources": sources,
                    "judge_overall_score": str(llm_judge.get("overall_score", ""))
                    if llm_judge
                    else "",
                    "judge_accuracy": str(llm_judge.get("component_scores", {}).get("accuracy", ""))
                    if llm_judge
                    else "",
                    "judge_completeness": str(
                        llm_judge.get("component_scores", {}).get("completeness", "")
                    )
                    if llm_judge
                    else "",
                    "judge_relevance": str(
                        llm_judge.get("component_scores", {}).get("relevance", "")
                    )
                    if llm_judge
                    else "",
                    "judge_clarity": str(llm_judge.get("component_scores", {}).get("clarity", ""))
                    if llm_judge
                    else "",
                    "judge_feedback": llm_judge.get("feedback", "")
                    .replace("\n", " ")
                    .replace("|", "\\|")
                    if llm_judge
                    else "",
                    "tokens_used": str(token_usage.get("total_tokens", "")) if token_usage else "",
                    "duration_seconds": str(token_usage.get("duration_seconds", ""))
                    if token_usage
                    else "",
                }
            )

        # Process without_kg scenario
        without_entry = without_entries.get(question_id)
        if without_entry:
            # Read answer file if specified
            answer_text = without_entry.get("answer", "")
            answer_file = without_entry.get("answer_file", "")
            if answer_file:
                answer_path = Path(answer_file)
                if answer_path.exists():
                    with open(answer_path) as f:
                        answer_text = f.read()

            # Extract sources for without_kg
            sources = extract_sources_from_answer(answer_text, "answer_motherduck_without_kg")

            # Clean answer for CSV (same as above)
            clean_answer = answer_text
            if "## Sources" in clean_answer:
                clean_answer = clean_answer.split("## Sources")[0]
            if "## Metadata" in clean_answer:
                clean_answer = clean_answer.split("## Metadata")[0]

            clean_answer = re.sub(r"^#\s*Answer\s*\n+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"^#+\s+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"\n#+\s+", " ", clean_answer)
            clean_answer = re.sub(r"\*\*(.*?)\*\*", r"\1", clean_answer)
            clean_answer = re.sub(r"\*(.*?)\*", r"\1", clean_answer)
            clean_answer = re.sub(r"```[\s\S]*?```", "", clean_answer)
            clean_answer = re.sub(r"`([^`]+)`", r"\1", clean_answer)
            clean_answer = re.sub(r"^\s*[-*+]\s+", "• ", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"^\s*\d+\.\s+", "", clean_answer, flags=re.MULTILINE)
            clean_answer = re.sub(r"\n\s*\n", " ", clean_answer)
            clean_answer = re.sub(r"\n", " ", clean_answer)
            clean_answer = re.sub(r"\s+", " ", clean_answer)
            clean_answer = clean_answer.strip()
            clean_answer = clean_answer.replace("|", "\\|")

            if len(clean_answer) > 500:
                clean_answer = clean_answer[:497] + "..."

            llm_judge = without_entry.get("llm_judge", {})
            token_usage = without_entry.get("token_usage", {})

            csv_rows.append(
                {
                    "question_num": idx,
                    "scenario": "answer_motherduck_without_kg",
                    "question": question_text,
                    "answer": clean_answer,
                    "answer_file": answer_file,
                    "sources": sources,
                    "judge_overall_score": str(llm_judge.get("overall_score", ""))
                    if llm_judge
                    else "",
                    "judge_accuracy": str(llm_judge.get("component_scores", {}).get("accuracy", ""))
                    if llm_judge
                    else "",
                    "judge_completeness": str(
                        llm_judge.get("component_scores", {}).get("completeness", "")
                    )
                    if llm_judge
                    else "",
                    "judge_relevance": str(
                        llm_judge.get("component_scores", {}).get("relevance", "")
                    )
                    if llm_judge
                    else "",
                    "judge_clarity": str(llm_judge.get("component_scores", {}).get("clarity", ""))
                    if llm_judge
                    else "",
                    "judge_feedback": llm_judge.get("feedback", "")
                    .replace("\n", " ")
                    .replace("|", "\\|")
                    if llm_judge
                    else "",
                    "tokens_used": str(token_usage.get("total_tokens", "")) if token_usage else "",
                    "duration_seconds": str(token_usage.get("duration_seconds", ""))
                    if token_usage
                    else "",
                }
            )

    # Sort by question number, then by scenario name
    csv_rows.sort(key=lambda x: (x["question_num"], x["scenario"]))

    # Calculate source deltas
    source_deltas = {}
    for row in csv_rows:
        q_num = row["question_num"]
        scenario = row["scenario"]

        if q_num not in source_deltas:
            source_deltas[q_num] = {}

        source_deltas[q_num][scenario] = row["sources"]

    # Add delta information to results
    for row in csv_rows:
        q_num = row["question_num"]
        q_sources = source_deltas.get(q_num, {})

        with_kg_sources = q_sources.get("answer_motherduck_with_kg", "")
        without_kg_sources = q_sources.get("answer_motherduck_without_kg", "")

        if with_kg_sources and without_kg_sources:
            row["source_delta"] = calculate_source_overlap(with_kg_sources, without_kg_sources)
        else:
            row["source_delta"] = "N/A"

    # Write CSV with pipe delimiter
    csv_path = output.parent / "scenario_comparison.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")

        # Write header
        header = [
            "Question #",
            "Scenario",
            "Question Text",
            "Answer",
            "Answer File",
            "Sources",
            "Source Delta",
            "Judge Overall Score",
            "Judge Accuracy",
            "Judge Completeness",
            "Judge Relevance",
            "Judge Clarity",
            "Judge Feedback",
            "Tokens Used",
            "Duration (seconds)",
        ]
        writer.writerow(header)

        # Write data rows
        for row in csv_rows:
            csv_row = [
                str(row["question_num"]),
                row["scenario"],
                row["question"],
                row["answer"],
                row.get("answer_file", ""),
                row["sources"],
                row.get("source_delta", ""),
                row["judge_overall_score"],
                row["judge_accuracy"],
                row["judge_completeness"],
                row["judge_relevance"],
                row["judge_clarity"],
                row["judge_feedback"],
                row["tokens_used"],
                row["duration_seconds"],
            ]
            writer.writerow(csv_row)

    print(f"📊 CSV report written to {csv_path}")

    # Generate original markdown report
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
