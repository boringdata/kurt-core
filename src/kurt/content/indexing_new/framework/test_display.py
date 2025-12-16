"""Test script for the live progress display."""

import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MockDSPyResult:
    """Mock DSPy result for testing."""

    payload: dict
    result: Any
    error: Optional[Exception]
    telemetry: dict


def test_live_progress():
    """Test the live progress display with mock data."""
    from kurt.content.indexing_new.framework.display import make_progress_callback

    print("Testing live progress display...")
    print()

    # Simulate 12 sections being processed with various outcomes
    total_items = 12
    callback = make_progress_callback("LLM extraction", show_items=True)

    test_cases = [
        # (title, has_error, is_skip, skip_reason)
        ("Introduction to Machine Learning Concepts", False, False, None),
        ("Data Preprocessing Techniques", False, False, None),
        ("Neural Network Architecture Overview", False, True, "content unchanged"),  # Skip
        ("Deep Learning Fundamentals and Applications", False, False, None),
        ("Computer Vision Applications", True, False, None),  # Error
        ("Natural Language Processing Basics", False, False, None),
        ("Reinforcement Learning Strategies", False, True, "already indexed"),  # Skip
        ("Model Evaluation Metrics", False, False, None),
        ("Hyperparameter Tuning Methods", False, False, None),
        ("Transfer Learning Approaches", True, False, None),  # Error
        ("Deployment Best Practices", False, False, None),
        ("Monitoring and Maintenance", False, False, None),
    ]

    # Emit start event (completed=0, result=None)
    callback(0, total_items, None)

    for i, (title, has_error, is_skip, skip_reason) in enumerate(test_cases):
        # Simulate processing time (varying between 0.3 and 1.5 seconds)
        delay = 0.3 + (i % 4) * 0.3
        time.sleep(delay)

        # Use same document ID for all sections (simulating one document with multiple sections)
        doc_id = "1b60ace4-1234-5678-9abc-def012345678"

        # Create mock result
        payload = {
            "document_id": doc_id,
            "document_title": title,
            "section_number": i + 1,  # Use section_number instead of section_id
        }
        if is_skip:
            payload["skip"] = True
            payload["skip_reason"] = skip_reason

        result = MockDSPyResult(
            payload=payload,
            result={"entities": [], "claims": []} if not has_error else None,
            error=Exception(f"LLM timeout after {delay:.1f}s") if has_error else None,
            telemetry={"execution_time": delay},
        )

        # Call the progress callback
        callback(i + 1, total_items, result)

    print()
    print("Test complete!")


def test_tracker_direct():
    """Test LiveProgressTracker directly with all log methods."""
    from kurt.content.indexing_new.framework.display import LiveProgressTracker

    print("Testing LiveProgressTracker directly...")
    print()

    with LiveProgressTracker("Direct test", total=6, max_log_lines=5) as tracker:
        # Test log_success
        time.sleep(0.5)
        tracker.log_success("abc12345", "First Document Title", elapsed=0.5, counter=(1, 6))
        tracker.update(1)

        # Test log_success with long title
        time.sleep(0.4)
        tracker.log_success(
            "def67890",
            "This is a very long document title that should be truncated properly",
            elapsed=0.4,
            counter=(2, 6),
        )
        tracker.update(2)

        # Test log_skip
        time.sleep(0.3)
        tracker.log_skip("ghi11111", "Skipped Document", reason="content unchanged", counter=(3, 6))
        tracker.update(3)

        # Test log_error
        time.sleep(0.3)
        tracker.log_error("jkl22222", "Connection timeout after 30s", counter=(4, 6))
        tracker.update(4)

        # Test log_info
        time.sleep(0.3)
        tracker.log_info("Retrying failed items...")
        tracker.update(5)

        # Final success
        time.sleep(0.4)
        tracker.log_success("mno33333", "Final Document", elapsed=0.4, counter=(6, 6))
        tracker.update(6)

    print()
    print("Direct test complete!")


def test_simple_progress():
    """Test the simple print_progress function."""
    from kurt.content.indexing_new.framework.display import print_progress

    print("Testing simple progress (only shows at completion)...")
    print()

    # This only prints at completion
    for i in range(5):
        print_progress(i + 1, 5, "Simple test: ")
        time.sleep(0.3)

    print()
    print("Test complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        test_simple_progress()
    elif len(sys.argv) > 1 and sys.argv[1] == "direct":
        test_tracker_direct()
    else:
        test_live_progress()
