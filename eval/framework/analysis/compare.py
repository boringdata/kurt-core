#!/usr/bin/env python3
"""Generate CSV comparison reports for evaluation scenarios with LLM judge scores."""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ============================================================================
# Data Collection Functions
# ============================================================================


def collect_question_runs(results_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load the newest per-question JSON for each question id and extract the question entry.

    Args:
        results_dir: Directory containing evaluation result JSON files

    Returns:
        Dictionary mapping question IDs to their evaluation entries
    """
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
        filename = path.stem
        parts = filename.split("_")
        if not (parts and parts[0].startswith("q")):
            continue

        question_id = parts[0]

        # Find the command output entry with command "question:qN"
        question_entry = _extract_question_entry(data, question_id)

        if question_entry:
            # Add metadata
            question_entry["question_id"] = question_id
            question_entry["_source_file"] = str(path)
            question_entry["_timestamp"] = path.stat().st_mtime

            existing = latest.get(question_id)
            if not existing or question_entry["_timestamp"] > existing["_timestamp"]:
                latest[question_id] = question_entry

    return latest


def _extract_question_entry(data: Dict, question_id: str) -> Optional[Dict]:
    """Extract the question entry from the evaluation data."""
    if "workspace" not in data:
        return None

    command_outputs = data.get("workspace", {}).get("command_outputs", [])
    for entry in command_outputs:
        if entry.get("command") == f"question:{question_id}":
            return entry
    return None


def load_questions(path: Path) -> List[Dict]:
    """Load questions from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("questions", [])


# ============================================================================
# Data Extraction Functions
# ============================================================================


def extract_score(entry: Optional[Dict[str, Any]]) -> Optional[float]:
    """Extract LLM judge score from entry."""
    if not entry:
        return None
    judge = entry.get("llm_judge")
    if isinstance(judge, dict):
        score = judge.get("overall_score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def extract_usage(entry: Optional[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Extract usage statistics from entry."""
    if not entry:
        return None
    usage = entry.get("usage")
    if isinstance(usage, dict):
        return usage
    return None


def extract_judge_data(entry: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Extract all judge-related data from entry."""
    if not entry:
        return _empty_judge_data()

    judge = entry.get("llm_judge", {})
    if not judge:
        return _empty_judge_data()

    component_scores = judge.get("component_scores", {})

    return {
        "overall_score": str(judge.get("overall_score", "")),
        "accuracy": str(component_scores.get("accuracy", "")),
        "completeness": str(component_scores.get("completeness", "")),
        "relevance": str(component_scores.get("relevance", "")),
        "clarity": str(component_scores.get("clarity", "")),
        "feedback": _clean_for_csv(judge.get("feedback", "")),
    }


def _empty_judge_data() -> Dict[str, str]:
    """Return empty judge data structure."""
    return {
        "overall_score": "",
        "accuracy": "",
        "completeness": "",
        "relevance": "",
        "clarity": "",
        "feedback": "",
    }


# ============================================================================
# Text Processing Functions
# ============================================================================


def extract_answer_text(entry: Dict[str, Any]) -> str:
    """Extract answer text from entry, trying answer_file first, then stdout."""
    answer_text = ""
    answer_file = entry.get("answer_file", "")

    if answer_file:
        answer_path = Path(answer_file)
        if answer_path.exists():
            try:
                with open(answer_path) as f:
                    answer_text = f.read()
            except Exception:
                pass

    # Fall back to stdout if no answer from file
    if not answer_text:
        answer_text = entry.get("stdout", "")

    return answer_text


def clean_answer_text(answer_text: str) -> str:
    """Clean answer text for CSV format by removing markdown and formatting."""
    if not answer_text:
        return ""

    # Remove sources and metadata sections
    if "## Sources" in answer_text:
        answer_text = answer_text.split("## Sources")[0]
    if "## Metadata" in answer_text:
        answer_text = answer_text.split("## Metadata")[0]

    # Remove markdown formatting
    clean = answer_text
    clean = re.sub(r"^#\s*Answer\s*\n+", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"^#+\s+", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"\n#+\s+", " ", clean)
    clean = re.sub(r"\*\*(.*?)\*\*", r"\1", clean)
    clean = re.sub(r"\*(.*?)\*", r"\1", clean)
    clean = re.sub(r"```[\s\S]*?```", "", clean)
    clean = re.sub(r"`([^`]+)`", r"\1", clean)
    clean = re.sub(r"^\s*[-*+]\s+", "• ", clean, flags=re.MULTILINE)
    clean = re.sub(r"^\s*\d+\.\s+", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"\n\s*\n", " ", clean)
    clean = re.sub(r"\n", " ", clean)
    clean = re.sub(r"\s+", " ", clean)

    return _clean_for_csv(clean.strip())


def _clean_for_csv(text: str) -> str:
    """Escape text for CSV format with pipe delimiter."""
    return text.replace("|", "\\|").replace("\n", " ")


def extract_sources(answer_text: str, scenario_name: str = "") -> str:
    """Extract source information from answer text.

    For with_kg scenarios, returns the full Sources section.
    For other scenarios, returns just the source file paths.
    """
    if not answer_text:
        return ""

    # Special handling for with_kg scenario - get full Sources section
    if "with_kg" in scenario_name and "## Sources" in answer_text:
        return _extract_full_sources(answer_text)

    # Default behavior - extract individual source paths
    return _extract_source_paths(answer_text)


def _extract_full_sources(answer_text: str) -> str:
    """Extract full sources section for with_kg scenarios."""
    sources_section = answer_text.split("## Sources")[1]

    # Stop at the next major section
    if "## Metadata" in sources_section:
        sources_section = sources_section.split("## Metadata")[0]

    # Clean up formatting for CSV display
    lines = sources_section.strip().split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if line:
            # Remove markdown formatting
            line = line.replace("**", "")
            line = line.replace("###", "[")
            if line.startswith("["):
                line = line + "]"
            cleaned_lines.append(line)

    full_sources = "; ".join(cleaned_lines)
    return _clean_for_csv(full_sources)


def _extract_source_paths(answer_text: str) -> str:
    """Extract source file paths from answer text."""
    sources = []

    # Find the sources section
    sources_section = ""
    if "### Documents Used" in answer_text:
        sources_section = answer_text.split("### Documents Used")[1]
        if "###" in sources_section:
            sources_section = sources_section.split("###")[0]
    elif "## Sources" in answer_text:
        sources_section = answer_text.split("## Sources")[1]
        if "## " in sources_section:
            sources_section = sources_section.split("## ")[0]

    if not sources_section:
        return ""

    # Extract sources from list items
    for line in sources_section.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            # Try to extract file paths
            patterns = [
                r"\.kurt/sources/[^\s\)]+",
                r"path:\s*\.kurt/sources/[^\s\)]+",
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

            # If no path found, extract document name
            if not found_path:
                source = line.lstrip("- ").strip()
                if "(relevance:" in source:
                    source = source.split("(relevance:")[0].strip()
                if source and source not in sources and not source.startswith("#"):
                    sources.append(source)

    return "; ".join(sources)


# ============================================================================
# Report Generation Functions
# ============================================================================


def compute_summary(entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for a set of evaluation entries."""
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


def process_scenario_entry(
    entry: Optional[Dict[str, Any]],
    question: Dict,
    scenario_name: str,
    idx: int,
    github_repo: str,
    github_branch: str,
) -> Dict[str, Any]:
    """Process a single scenario entry and return formatted row data."""
    if not entry:
        return None

    # Extract answer text
    answer_text = extract_answer_text(entry)

    # Extract and clean various data
    clean_answer = clean_answer_text(answer_text)
    sources = extract_sources(answer_text, scenario_name)
    judge_data = extract_judge_data(entry)
    usage = extract_usage(entry) or {}

    # Create GitHub links
    source_file = entry.get("_source_file", "")
    github_link = create_github_link(source_file, github_repo, github_branch)
    scenario_def_path = f"eval/scenarios/{scenario_name}.yaml"
    scenario_def_link = create_github_link(scenario_def_path, github_repo, github_branch)

    # Get reference answer
    expected_answer = _clean_for_csv(question.get("expected_answer", "").strip())

    return {
        "question_num": idx,
        "scenario": scenario_name,
        "scenario_definition": scenario_def_link,
        "question": question.get("question", f"Question {idx}"),
        "answer": clean_answer,
        "expected_answer": expected_answer,
        "answer_file": entry.get("answer_file", ""),
        "github_link": github_link,
        "sources": sources,
        "judge_overall_score": judge_data["overall_score"],
        "judge_accuracy": judge_data["accuracy"],
        "judge_completeness": judge_data["completeness"],
        "judge_relevance": judge_data["relevance"],
        "judge_clarity": judge_data["clarity"],
        "judge_feedback": judge_data["feedback"],
        "tokens_used": str(usage.get("total_tokens", "")),
        "duration_seconds": str(usage.get("duration_seconds", "")),
    }


def create_github_link(
    file_path: str,
    repo: str = "https://github.com/anthropics/kurt-core",
    branch: str = "main",
) -> str:
    """Create a GitHub link to a file."""
    if not file_path or file_path == "N/A" or file_path.startswith("/tmp/"):
        return ""

    # Clean the path
    if file_path.startswith("/"):
        if "/kurt-core/" in file_path:
            file_path = file_path.split("/kurt-core/")[-1]
        else:
            return ""

    return f"{repo}/blob/{branch}/{file_path}"


def calculate_source_overlap(sources1: str, sources2: str) -> str:
    """Calculate overlap between two sets of sources."""
    docs1 = _extract_doc_names(sources1)
    docs2 = _extract_doc_names(sources2)

    if not docs1 and not docs2:
        return "N/A"

    common = docs1 & docs2
    unique_to_1 = docs1 - docs2
    unique_to_2 = docs2 - docs1

    overlap_pct = (len(common) / max(len(docs1), len(docs2), 1)) * 100 if (docs1 or docs2) else 0

    return (
        f"{overlap_pct:.0f}% ({len(common)} common, "
        f"{len(unique_to_1)} unique to with_kg, "
        f"{len(unique_to_2)} unique to without_kg)"
    )


def _extract_doc_names(sources_str: str) -> set:
    """Extract document names from sources string."""
    docs = set()
    if not sources_str:
        return docs

    # Handle different source formats
    if "[ Documents Used]" in sources_str:
        # with_kg format
        parts = sources_str.split(";")
        for part in parts:
            part = part.strip()
            if ".md" in part and not part.startswith("["):
                doc_name = _clean_doc_name(part)
                if doc_name:
                    docs.add(doc_name)
    else:
        # without_kg format
        parts = sources_str.split(";")
        for part in parts:
            part = part.strip()
            if ".md" in part:
                doc_name = _clean_doc_name(part)
                if doc_name:
                    docs.add(doc_name)

    return docs


def _clean_doc_name(path_or_name: str) -> str:
    """Clean and extract document name from path or name string."""
    if "/" in path_or_name:
        doc_name = path_or_name.split("/")[-1]
    else:
        doc_name = path_or_name

    doc_name = doc_name.replace(".md", "").strip()

    if "(relevance:" in doc_name:
        doc_name = doc_name.split("(relevance:")[0].strip()

    return doc_name


def write_csv_report(csv_path: Path, csv_rows: List[Dict[str, Any]]) -> None:
    """Write CSV report to file."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")

        # Write header - with GitHub links at the end
        header = [
            "Question #",
            "Scenario",
            "Question Text",
            "Answer",
            "Reference Answer",
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
            "Answer File",
            "Scenario Definition",
            "Result File",
        ]
        writer.writerow(header)

        # Write data rows - reordered to match header
        for row in csv_rows:
            csv_row = [
                str(row["question_num"]),
                row["scenario"],
                row["question"],
                row["answer"],
                row.get("expected_answer", ""),
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
                row.get("answer_file", ""),
                row.get("scenario_definition", ""),
                row.get("github_link", ""),
            ]
            writer.writerow(csv_row)


# ============================================================================
# Main Report Generation
# ============================================================================


def generate_report(
    with_entries: Dict[str, Dict[str, Any]],
    without_entries: Dict[str, Dict[str, Any]],
    questions: List[Dict],
    output: Path,
    github_repo: str = "https://github.com/anthropics/kurt-core",
    github_branch: str = "main",
    scenario_names: Tuple[str, str] = ("with_kg", "without_kg"),
) -> Path:
    """Generate CSV comparison report for two scenarios.

    Args:
        with_entries: Results for first scenario (typically with_kg)
        without_entries: Results for second scenario (typically without_kg)
        questions: List of questions with expected answers
        output: Output path for CSV report
        github_repo: GitHub repository URL for file links
        github_branch: GitHub branch for file links
        scenario_names: Tuple of scenario names

    Returns:
        Path to generated CSV file
    """
    # Build CSV data with one line per scenario per question
    csv_rows = []

    for idx, question in enumerate(questions, start=1):
        question_id = question.get("id") or f"q{idx}"

        # Process both scenarios
        for entries, scenario_name in [
            (with_entries, scenario_names[0]),
            (without_entries, scenario_names[1]),
        ]:
            entry = entries.get(question_id)
            if entry:
                row = process_scenario_entry(
                    entry, question, scenario_name, idx, github_repo, github_branch
                )
                if row:
                    csv_rows.append(row)

    # Sort by question number, then by scenario name
    csv_rows.sort(key=lambda x: (x["question_num"], x["scenario"]))

    # Calculate source deltas
    for q_num in set(row["question_num"] for row in csv_rows):
        q_rows = [r for r in csv_rows if r["question_num"] == q_num]
        if len(q_rows) == 2:
            sources1 = q_rows[0]["sources"]
            sources2 = q_rows[1]["sources"]
            delta = calculate_source_overlap(sources1, sources2)
            for row in q_rows:
                row["source_delta"] = delta
        else:
            for row in q_rows:
                row["source_delta"] = "N/A"

    # Write CSV report
    csv_path = output.parent / "scenario_comparison.csv"
    write_csv_report(csv_path, csv_rows)

    # Print summary
    with_summary = compute_summary(with_entries)
    without_summary = compute_summary(without_entries)

    print(f"✅ CSV report successfully generated: {csv_path}")
    print(f"📊 Report contains {len(csv_rows)} rows with judge scores and usage data")
    print(
        f"📈 Average scores: {scenario_names[0]}={with_summary['average_score']:.2f}, "
        f"{scenario_names[1]}={without_summary['average_score']:.2f}"
    )

    return csv_path


def generate_report_from_dirs(
    with_dir: Path | str,
    without_dir: Path | str,
    questions_file: Path | str,
    output_file: Path | str,
    github_repo: str = "https://github.com/anthropics/kurt-core",
    github_branch: str = "main",
) -> Path:
    """Generate report from result directories.

    Args:
        with_dir: Directory with first scenario results
        without_dir: Directory with second scenario results
        questions_file: Path to questions YAML file
        output_file: Path for output CSV file
        github_repo: GitHub repository URL
        github_branch: GitHub branch name

    Returns:
        Path to generated CSV file
    """
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

    # Extract scenario names from directory names
    scenario_names = (with_path.name, without_path.name)

    csv_path = generate_report(
        with_entries,
        without_entries,
        questions,
        output_path,
        github_repo,
        github_branch,
        scenario_names,
    )
    return csv_path


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    """Command-line interface for report generation."""
    parser = argparse.ArgumentParser(
        description="Generate CSV comparison report for evaluation scenarios",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--with-kg-dir",
        required=True,
        help="Results directory for the WITH KG scenario",
    )
    parser.add_argument(
        "--without-kg-dir",
        required=True,
        help="Results directory for the WITHOUT KG scenario",
    )
    parser.add_argument(
        "--questions-file",
        default="eval/scenarios/questions_motherduck.yaml",
        help="YAML file containing the questions and expected answers",
    )
    parser.add_argument(
        "--output",
        default="eval/results/scenario_comparison.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--github-repo",
        default="https://github.com/anthropics/kurt-core",
        help="GitHub repository URL for file links",
    )
    parser.add_argument(
        "--github-branch",
        default="main",
        help="GitHub branch for file links",
    )

    args = parser.parse_args()

    try:
        csv_path = generate_report_from_dirs(
            args.with_kg_dir,
            args.without_kg_dir,
            args.questions_file,
            args.output,
            args.github_repo,
            args.github_branch,
        )
        print(f"✅ Report successfully generated: {csv_path}")
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
