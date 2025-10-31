#!/usr/bin/env python3
"""Entry point for running evaluation scenarios.

Usage:
    python eval/run_scenario.py 01_basic_init
    python eval/run_scenario.py 02_add_url
    python eval/run_scenario.py --all
"""

import argparse
import sys
from pathlib import Path

# Add framework to path
eval_dir = Path(__file__).parent
sys.path.insert(0, str(eval_dir))

from framework.runner import run_scenario_by_name  # noqa: E402


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Kurt evaluation scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python eval/run_scenario.py 01_basic_init
  python eval/run_scenario.py 02_status_check --no-cleanup
  python eval/run_scenario.py --all

Available scenarios:
  01_basic_init              - Initialize a new Kurt project
  02_status_check            - Test kurt status command
  03_interactive_project     - Multi-turn project creation

Debugging:
  Use --no-cleanup to preserve the workspace after completion
        """,
    )

    parser.add_argument("scenario", nargs="?", help="Scenario name to run (without .py extension)")

    parser.add_argument("--all", action="store_true", help="Run all scenarios")

    parser.add_argument("--list", action="store_true", help="List available scenarios")

    parser.add_argument(
        "--max-tools",
        type=int,
        default=50,
        help="Maximum number of tool calls per scenario (default: 50)",
    )

    parser.add_argument(
        "--max-duration",
        type=int,
        default=300,
        help="Maximum scenario duration in seconds (default: 300)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100000,
        help="Maximum tokens per scenario (default: 100000)",
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Preserve workspace after scenario completes (do not clean up)",
    )

    args = parser.parse_args()

    scenarios_dir = eval_dir / "scenarios"

    # List scenarios
    if args.list:
        print("\nAvailable scenarios:")
        print("=" * 60)
        for scenario_file in sorted(scenarios_dir.glob("*.py")):
            if scenario_file.name.startswith("_"):
                continue
            scenario_name = scenario_file.stem
            print(f"  {scenario_name}")
        print()
        return 0

    # Run all scenarios
    if args.all:
        scenario_files = sorted(scenarios_dir.glob("*.py"))
        scenario_files = [f for f in scenario_files if not f.name.startswith("_")]

        print(f"\n🚀 Running {len(scenario_files)} scenarios...\n")

        results = []
        for scenario_file in scenario_files:
            scenario_name = scenario_file.stem
            try:
                result = run_scenario_by_name(
                    scenario_name,
                    scenarios_dir,
                    max_tool_calls=args.max_tools,
                    max_duration_seconds=args.max_duration,
                    max_tokens=args.max_tokens,
                    preserve_workspace=args.no_cleanup,
                )
                results.append(result)
            except Exception as e:
                print(f"❌ Failed to run {scenario_name}: {e}")
                results.append({"scenario": scenario_name, "passed": False, "error": str(e)})

        # Print summary
        print("\n" + "=" * 60)
        print("📊 Summary")
        print("=" * 60)

        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)

        for result in results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['scenario']}")
            if not result["passed"] and result.get("error"):
                print(f"   Error: {result['error']}")

        print(f"\n{passed_count}/{total_count} scenarios passed")

        return 0 if passed_count == total_count else 1

    # Run single scenario
    if not args.scenario:
        parser.print_help()
        return 1

    try:
        result = run_scenario_by_name(
            args.scenario,
            scenarios_dir,
            max_tool_calls=args.max_tools,
            max_duration_seconds=args.max_duration,
            max_tokens=args.max_tokens,
            preserve_workspace=args.no_cleanup,
        )
        return 0 if result["passed"] else 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
