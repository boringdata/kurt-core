#!/usr/bin/env python3
"""Tests for the comparison report generation."""

import json

import pytest

from eval.framework.analysis.compare import (
    collect_question_runs,
    compute_summary,
    extract_score,
    extract_usage,
    generate_report,
)


class TestCollectQuestionRuns:
    """Test the collect_question_runs function."""

    def test_collects_question_entries_from_json(self, tmp_path):
        """Test that question entries are correctly extracted from JSON files."""
        # Create a sample JSON file with the expected structure
        json_data = {
            "scenario": "test_scenario",
            "workspace": {
                "command_outputs": [
                    {
                        "command": "load_data",
                        "stdout": "Data loaded",
                    },
                    {
                        "command": "kurt answer ...",
                        "answer": "Some answer",
                    },
                    {
                        "command": "question:q1",
                        "llm_judge": {
                            "overall_score": 0.75,
                            "component_scores": {
                                "accuracy": 0.8,
                                "completeness": 0.7,
                                "relevance": 0.75,
                                "clarity": 0.75,
                            },
                            "feedback": "Good answer",
                        },
                        "usage": {
                            "duration_seconds": 1.5,
                            "total_tokens": 100,
                        },
                        "answer": "The answer to question 1",
                    },
                ],
            },
        }

        # Write to a file
        json_file = tmp_path / "q1_20251205_120000.json"
        with open(json_file, "w") as f:
            json.dump(json_data, f)

        # Collect question runs
        results = collect_question_runs(tmp_path)

        # Verify the results
        assert "q1" in results
        assert results["q1"]["command"] == "question:q1"
        assert results["q1"]["llm_judge"]["overall_score"] == 0.75
        assert results["q1"]["usage"]["duration_seconds"] == 1.5
        assert results["q1"]["answer"] == "The answer to question 1"

    def test_handles_missing_question_entry(self, tmp_path):
        """Test that files without the question entry are skipped."""
        json_data = {
            "scenario": "test_scenario",
            "workspace": {
                "command_outputs": [
                    {
                        "command": "load_data",
                        "stdout": "Data loaded",
                    },
                ],
            },
        }

        json_file = tmp_path / "q1_20251205_120000.json"
        with open(json_file, "w") as f:
            json.dump(json_data, f)

        results = collect_question_runs(tmp_path)

        # Should be empty since no question:q1 command found
        assert len(results) == 0

    def test_uses_newest_file_for_duplicate_questions(self, tmp_path):
        """Test that the newest file is used when multiple files exist for the same question."""
        # Create older file
        old_data = {
            "workspace": {
                "command_outputs": [
                    {
                        "command": "question:q1",
                        "llm_judge": {"overall_score": 0.5},
                    }
                ]
            }
        }
        old_file = tmp_path / "q1_20251205_110000.json"
        with open(old_file, "w") as f:
            json.dump(old_data, f)

        # Create newer file
        new_data = {
            "workspace": {
                "command_outputs": [
                    {
                        "command": "question:q1",
                        "llm_judge": {"overall_score": 0.8},
                    }
                ]
            }
        }
        new_file = tmp_path / "q1_20251205_120000.json"
        with open(new_file, "w") as f:
            json.dump(new_data, f)

        # Touch files to set modification times
        import time

        old_file.touch()
        time.sleep(0.01)  # Ensure different timestamps
        new_file.touch()

        results = collect_question_runs(tmp_path)

        # Should use the newer file
        assert results["q1"]["llm_judge"]["overall_score"] == 0.8


class TestExtractFunctions:
    """Test the extract_score and extract_usage functions."""

    def test_extract_score_from_valid_entry(self):
        """Test extracting score from a valid entry."""
        entry = {
            "llm_judge": {
                "overall_score": 0.85,
                "component_scores": {},
            }
        }
        score = extract_score(entry)
        assert score == 0.85

    def test_extract_score_from_invalid_entry(self):
        """Test extracting score from entries without valid scores."""
        assert extract_score(None) is None
        assert extract_score({}) is None
        assert extract_score({"llm_judge": None}) is None
        assert extract_score({"llm_judge": {}}) is None
        assert extract_score({"llm_judge": {"overall_score": "not a number"}}) is None

    def test_extract_usage_with_correct_key(self):
        """Test extracting usage data with the correct 'usage' key."""
        entry = {
            "usage": {
                "duration_seconds": 2.5,
                "total_tokens": 150,
            }
        }
        usage = extract_usage(entry)
        assert usage is not None
        assert usage["duration_seconds"] == 2.5
        assert usage["total_tokens"] == 150

    def test_extract_usage_from_invalid_entry(self):
        """Test that extract_usage handles missing or invalid data."""
        assert extract_usage(None) is None
        assert extract_usage({}) is None
        assert extract_usage({"usage": None}) is None
        assert extract_usage({"usage": "not a dict"}) is None

    def test_extract_usage_ignores_old_token_usage_key(self):
        """Test that the old 'token_usage' key is no longer used."""
        entry = {
            "token_usage": {  # Old key that should be ignored
                "duration_seconds": 2.5,
                "total_tokens": 150,
            }
        }
        usage = extract_usage(entry)
        assert usage is None  # Should not extract from old key


class TestComputeSummary:
    """Test the compute_summary function."""

    def test_compute_summary_with_valid_entries(self):
        """Test computing summary statistics from valid entries."""
        entries = {
            "q1": {
                "llm_judge": {"overall_score": 0.8},
                "usage": {"total_tokens": 100, "duration_seconds": 1.0},
            },
            "q2": {
                "llm_judge": {"overall_score": 0.6},
                "usage": {"total_tokens": 200, "duration_seconds": 2.0},
            },
        }

        summary = compute_summary(entries)

        assert summary["num_questions"] == 2
        assert summary["average_score"] == 0.7  # (0.8 + 0.6) / 2
        assert summary["tokens_total"] == 300  # 100 + 200
        assert summary["duration_total"] == 3.0  # 1.0 + 2.0

    def test_compute_summary_with_missing_data(self):
        """Test computing summary when some data is missing."""
        entries = {
            "q1": {
                "llm_judge": {"overall_score": 0.8},
                # No usage data
            },
            "q2": {
                # No judge data
                "usage": {"total_tokens": 200, "duration_seconds": 2.0},
            },
        }

        summary = compute_summary(entries)

        assert summary["num_questions"] == 2
        assert summary["average_score"] == 0.8  # Only one score available
        assert summary["tokens_total"] == 200
        assert summary["duration_total"] == 2.0


class TestGenerateReport:
    """Test the generate_report function."""

    def test_generate_csv_report(self, tmp_path):
        """Test that CSV report is generated correctly."""
        # Create test data
        with_entries = {
            "q1": {
                "question_id": "q1",
                "llm_judge": {
                    "overall_score": 0.75,
                    "component_scores": {
                        "accuracy": 0.8,
                        "completeness": 0.7,
                        "relevance": 0.75,
                        "clarity": 0.75,
                    },
                    "feedback": "Good answer with room for improvement",
                },
                "usage": {
                    "duration_seconds": 1.5,
                    "total_tokens": 100,
                },
                "answer": "Answer for with_kg scenario",
                "_source_file": str(tmp_path / "with_kg" / "q1.json"),
            }
        }

        without_entries = {
            "q1": {
                "question_id": "q1",
                "llm_judge": {
                    "overall_score": 0.5,
                    "component_scores": {
                        "accuracy": 0.5,
                        "completeness": 0.5,
                        "relevance": 0.5,
                        "clarity": 0.5,
                    },
                    "feedback": "Basic answer",
                },
                "usage": {
                    "duration_seconds": 1.0,
                    "total_tokens": 80,
                },
                "answer": "Answer for without_kg scenario",
                "_source_file": str(tmp_path / "without_kg" / "q1.json"),
            }
        }

        questions = [
            {
                "id": "q1",
                "question": "What is the test question?",
                "expected_answer": "This is the expected answer for testing purposes.",
            }
        ]

        output_path = tmp_path / "report.csv"

        # Generate the report
        csv_path = generate_report(
            with_entries,
            without_entries,
            questions,
            output_path,
            github_repo="https://github.com/test/repo",
            github_branch="main",
            scenario_names=("with_kg_scenario", "without_kg_scenario"),
        )

        # Verify CSV was created
        assert csv_path.exists()
        assert csv_path.name == "scenario_comparison.csv"

        # Read and verify CSV content
        import csv

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f, delimiter="|")
            rows = list(reader)

        # Should have 2 rows (one for each scenario)
        assert len(rows) == 2

        # Check with_kg row
        with_kg_row = [r for r in rows if r["Scenario"] == "with_kg_scenario"][0]
        assert with_kg_row["Judge Overall Score"] == "0.75"
        assert with_kg_row["Judge Accuracy"] == "0.8"
        assert with_kg_row["Tokens Used"] == "100"
        assert with_kg_row["Duration (seconds)"] == "1.5"
        assert (
            with_kg_row["Reference Answer"] == "This is the expected answer for testing purposes."
        )

        # Check without_kg row
        without_kg_row = [r for r in rows if r["Scenario"] == "without_kg_scenario"][0]
        assert without_kg_row["Judge Overall Score"] == "0.5"
        assert without_kg_row["Judge Accuracy"] == "0.5"
        assert without_kg_row["Tokens Used"] == "80"
        assert without_kg_row["Duration (seconds)"] == "1.0"
        assert (
            without_kg_row["Reference Answer"]
            == "This is the expected answer for testing purposes."
        )

    def test_generate_report_with_empty_entries(self, tmp_path):
        """Test report generation with empty question entries."""
        with_entries = {}
        without_entries = {}
        questions = []

        output_path = tmp_path / "report.csv"

        csv_path = generate_report(
            with_entries,
            without_entries,
            questions,
            output_path,
            scenario_names=("scenario1", "scenario2"),
        )

        # CSV should still be created but empty
        assert csv_path.exists()

        # Read CSV and check it only has headers
        import csv

        with open(csv_path, "r") as f:
            reader = csv.reader(f, delimiter="|")
            rows = list(reader)

        # Should have header row only
        assert len(rows) == 1
        assert rows[0][0] == "Question #"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
