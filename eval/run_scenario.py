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
  python eval/run_scenario.py 1                    # Run by ID
  python eval/run_scenario.py 01_basic_init        # Run by name
  python eval/run_scenario.py 2 --no-cleanup       # Preserve workspace
  python eval/run_scenario.py --list               # List all scenarios
  python eval/run_scenario.py --all                # Run all scenarios

Scenario IDs:
  Use --list to see all scenarios with their IDs

Debugging:
  Use --no-cleanup to preserve the workspace after completion
        """,
    )

    parser.add_argument(
        "scenario", nargs="?", help="Scenario ID (1, 2, ...) or name (01_basic_init, ...)"
    )

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

    parser.add_argument(
        "--llm-provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic"],
        help="LLM provider for user agent responses (default: openai)",
    )

    args = parser.parse_args()

    scenarios_dir = eval_dir / "scenarios"

    # List scenarios
    if args.list:
        print("\nAvailable scenarios:")
        print("=" * 60)

        scenario_list = []  # (id, name, desc, type)
        seen_names = set()

        # Check scenarios.yaml
        scenarios_yaml = scenarios_dir / "scenarios.yaml"
        if scenarios_yaml.exists():
            import yaml

            with open(scenarios_yaml) as f:
                data = yaml.safe_load(f)
                if "scenarios" in data:
                    for scenario in data["scenarios"]:
                        name = scenario.get("name", "unnamed")
                        desc = scenario.get("description", "")
                        scenario_list.append((name, desc, "yaml"))
                        seen_names.add(name)

        # Collect individual scenario files (Python and YAML)
        scenario_files = []
        scenario_files.extend(scenarios_dir.glob("*.py"))
        scenario_files.extend(scenarios_dir.glob("*.yaml"))
        scenario_files.extend(scenarios_dir.glob("*.yml"))

        # Remove duplicates and private scenarios
        for scenario_file in sorted(scenario_files):
            if scenario_file.name.startswith("_"):
                continue
            scenario_name = scenario_file.stem
            if scenario_name in seen_names or scenario_name == "scenarios":
                continue
            seen_names.add(scenario_name)

            # Show file type
            ext = scenario_file.suffix
            type_label = "yaml" if ext in [".yaml", ".yml"] else "py"
            scenario_list.append((scenario_name, "", type_label))

        # Print with IDs
        for idx, (name, desc, type_label) in enumerate(scenario_list, start=1):
            if desc:
                print(f"  [{idx}] {name:<28} ({type_label}) - {desc}")
            else:
                print(f"  [{idx}] {name:<28} ({type_label})")

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

    # Resolve scenario name (could be numeric ID or name)
    scenario_name = args.scenario

    # Check if it's a numeric ID
    if scenario_name.isdigit():
        scenario_idx = int(scenario_name)

        # Build scenario list (same as --list)
        import yaml

        scenario_list = []
        seen_names = set()

        scenarios_yaml = scenarios_dir / "scenarios.yaml"
        if scenarios_yaml.exists():
            with open(scenarios_yaml) as f:
                data = yaml.safe_load(f)
                if "scenarios" in data:
                    for scenario in data["scenarios"]:
                        name = scenario.get("name", "unnamed")
                        scenario_list.append(name)
                        seen_names.add(name)

        scenario_files = []
        scenario_files.extend(scenarios_dir.glob("*.py"))
        scenario_files.extend(scenarios_dir.glob("*.yaml"))
        scenario_files.extend(scenarios_dir.glob("*.yml"))

        for scenario_file in sorted(scenario_files):
            if scenario_file.name.startswith("_"):
                continue
            name = scenario_file.stem
            if name in seen_names or name == "scenarios":
                continue
            seen_names.add(name)
            scenario_list.append(name)

        # Resolve ID to name
        if scenario_idx < 1 or scenario_idx > len(scenario_list):
            print(f"\n❌ Invalid scenario ID: {scenario_idx}")
            print(f"   Available IDs: 1-{len(scenario_list)}")
            print("\nRun with --list to see all scenarios")
            return 1

        scenario_name = scenario_list[scenario_idx - 1]
        print(f"Running scenario [{scenario_idx}]: {scenario_name}\n")

    try:
        result = run_scenario_by_name(
            scenario_name,
            scenarios_dir,
            max_tool_calls=args.max_tools,
            max_duration_seconds=args.max_duration,
            max_tokens=args.max_tokens,
            preserve_workspace=args.no_cleanup,
            llm_provider=args.llm_provider,
        )
        return 0 if result["passed"] else 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
