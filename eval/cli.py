#!/usr/bin/env python3
"""Kurt Evaluation CLI - Run evaluation scenarios for Kurt agent behavior."""

import sys
from pathlib import Path

import click

# Add eval and project root to path
eval_dir = Path(__file__).parent.resolve()
project_root = eval_dir.parent
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(project_root))

# Import from framework (works for both direct execution and module import)
try:
    from .framework.config import get_config  # Module import
    from .framework.runner import run_scenario_by_name  # Module import
except ImportError:
    from framework.config import get_config  # Direct execution
    from framework.runner import run_scenario_by_name  # Direct execution


@click.group()
def main():
    """Kurt Evaluation Framework - Test agent behavior with automated scenarios."""
    pass


@main.command()
@click.argument("scenario", type=str)
@click.option("--no-cleanup", is_flag=True, help="Preserve workspace after completion")
@click.option(
    "--max-tool-calls",
    type=int,
    default=None,
    help="Maximum tool calls allowed (default: from config)",
)
@click.option(
    "--max-duration",
    type=int,
    default=None,
    help="Maximum duration in seconds (default: from config)",
)
@click.option(
    "--max-tokens", type=int, default=None, help="Maximum tokens to use (default: from config)"
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider for user agent",
)
def run(scenario, no_cleanup, max_tool_calls, max_duration, max_tokens, llm_provider):
    """Run a single evaluation scenario.

    SCENARIO can be:
    - Scenario number (e.g., "3")
    - Scenario ID (e.g., "03_interactive_project")
    - Scenario name (e.g., "03_project_no_sources")

    Examples:
      kurt-eval run 3
      kurt-eval run 03_interactive_project
      kurt-eval run 3 --no-cleanup
      kurt-eval run 3 --llm-provider anthropic
    """
    config = get_config()
    scenarios_dir = eval_dir / config.scenarios_dir

    # Convert scenario number to ID if needed
    if scenario.isdigit():
        # Pad to 2 digits
        scenario_id = f"{int(scenario):02d}"
        # Find matching scenario in scenarios.yaml
        scenarios_yaml = scenarios_dir / config.scenarios_file.split("/")[-1]
        if scenarios_yaml.exists():
            import yaml

            with open(scenarios_yaml) as f:
                data = yaml.safe_load(f)
                for s in data.get("scenarios", []):
                    if s["name"].startswith(scenario_id):
                        scenario = s["name"]
                        break

    click.echo(f"Running scenario [{scenario}]: {scenario}\n")

    try:
        results = run_scenario_by_name(
            scenario_name=scenario,
            scenarios_dir=scenarios_dir,
            max_tool_calls=max_tool_calls,
            max_duration_seconds=max_duration,
            max_tokens=max_tokens,
            preserve_workspace=no_cleanup,
            llm_provider=llm_provider,
        )

        if results["passed"]:
            click.secho("\n✅ Scenario PASSED", fg="green", bold=True)
            sys.exit(0)
        else:
            click.secho(
                f"\n❌ Scenario FAILED: {results.get('error', 'Unknown error')}",
                fg="red",
                bold=True,
            )
            sys.exit(1)

    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red", bold=True)
        sys.exit(1)


@main.command()
@click.option("--filter", type=str, help="Filter scenarios by name pattern")
def list(filter):
    """List all available evaluation scenarios."""
    scenarios_yaml = eval_dir / "scenarios" / "scenarios.yaml"

    if not scenarios_yaml.exists():
        click.secho("❌ No scenarios.yaml found", fg="red")
        sys.exit(1)

    import yaml

    with open(scenarios_yaml) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])

    if filter:
        scenarios = [
            s
            for s in scenarios
            if filter.lower() in s["name"].lower()
            or filter.lower() in s.get("description", "").lower()
        ]

    click.echo(f"\n📋 Available Scenarios ({len(scenarios)}):\n")

    for i, scenario in enumerate(scenarios, 1):
        name = scenario["name"]
        desc = scenario.get("description", "No description")

        # Extract scenario number from name (e.g., "03" from "03_interactive_project")
        scenario_num = name.split("_")[0] if "_" in name else str(i)

        click.echo(f"  {scenario_num}. {click.style(name, fg='cyan', bold=True)}")
        click.echo(f"     {desc}")

        if "notes" in scenario:
            notes = scenario["notes"].strip().split("\n")[0]  # First line only
            click.echo(f"     {click.style(notes, dim=True)}")

        click.echo()


@main.command()
@click.option("--filter", type=str, help="Filter scenarios by name pattern")
@click.option("--stop-on-failure", is_flag=True, help="Stop running on first failure")
@click.option(
    "--max-tool-calls",
    type=int,
    default=None,
    help="Maximum tool calls allowed (default: from config)",
)
@click.option(
    "--max-duration",
    type=int,
    default=None,
    help="Maximum duration in seconds (default: from config)",
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider for user agent",
)
def run_all(filter, stop_on_failure, max_tool_calls, max_duration, llm_provider):
    """Run all evaluation scenarios."""
    config = get_config()
    scenarios_dir = eval_dir / config.scenarios_dir
    scenarios_yaml = scenarios_dir / config.scenarios_file.split("/")[-1]

    if not scenarios_yaml.exists():
        click.secho("❌ No scenarios.yaml found", fg="red")
        sys.exit(1)

    import yaml

    with open(scenarios_yaml) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])

    if filter:
        scenarios = [s for s in scenarios if filter.lower() in s["name"].lower()]

    click.echo(f"\n🚀 Running {len(scenarios)} scenarios...\n")

    passed = 0
    failed = 0
    failed_scenarios = []

    for scenario in scenarios:
        name = scenario["name"]
        click.echo(f"{'━'*70}")
        click.echo(f"Running: {name}")
        click.echo(f"{'━'*70}\n")

        try:
            results = run_scenario_by_name(
                scenario_name=name,
                scenarios_dir=scenarios_dir,
                max_tool_calls=max_tool_calls,
                max_duration_seconds=max_duration,
                max_tokens=100000,
                preserve_workspace=False,
                llm_provider=llm_provider,
            )

            if results["passed"]:
                passed += 1
                click.secho(f"✅ {name} PASSED\n", fg="green")
            else:
                failed += 1
                failed_scenarios.append(name)
                click.secho(
                    f"❌ {name} FAILED: {results.get('error', 'Unknown error')}\n", fg="red"
                )

                if stop_on_failure:
                    break

        except Exception as e:
            failed += 1
            failed_scenarios.append(name)
            click.secho(f"❌ {name} ERROR: {e}\n", fg="red")

            if stop_on_failure:
                break

    # Summary
    click.echo(f"\n{'='*70}")
    click.echo("📊 Summary:")
    click.echo(f"{'='*70}")
    click.secho(f"  ✅ Passed: {passed}", fg="green")
    click.secho(f"  ❌ Failed: {failed}", fg="red" if failed > 0 else "white")
    click.echo(f"  📝 Total:  {passed + failed}")

    if failed_scenarios:
        click.echo("\nFailed scenarios:")
        for name in failed_scenarios:
            click.secho(f"  - {name}", fg="red")

    sys.exit(0 if failed == 0 else 1)


@main.group()
def training():
    """Manage training data for DSPy optimization."""
    pass


@training.command("stats")
@click.argument("scenario", type=str, required=False)
def training_stats(scenario):
    """Show training data statistics.

    If SCENARIO is provided, shows stats for that scenario.
    Otherwise, shows stats for all scenarios.

    Examples:
      kurt-eval training stats
      kurt-eval training stats 03_project_no_sources
    """
    from framework.training_data import TrainingDataCollector

    training_dir = eval_dir / "training_data"
    collector = TrainingDataCollector(training_dir)

    if scenario:
        # Show stats for specific scenario
        stats = collector.get_dataset_stats(scenario)

        if stats["total"] == 0:
            click.secho(f"❌ No training data found for {scenario}", fg="red")
            sys.exit(1)

        click.echo(f"\n📊 Training Data Stats: {click.style(scenario, fg='cyan', bold=True)}\n")
        click.echo(f"  Total examples:     {stats['total']}")
        click.secho(f"  ✅ Passed:          {stats['passed']}", fg="green")
        click.secho(
            f"  ❌ Failed:          {stats['failed']}", fg="red" if stats["failed"] > 0 else "white"
        )
        click.echo(f"  Pass rate:          {stats['pass_rate']:.1%}")
        click.echo(f"  Avg tool calls:     {stats['avg_tool_calls']:.1f}")
        click.echo(f"  Avg duration:       {stats['avg_duration_seconds']:.1f}s")

        if stats["failure_types"]:
            click.echo("\n  Failure types:")
            for failure_type, count in stats["failure_types"].items():
                click.secho(f"    - {failure_type}: {count}", fg="yellow")

        click.echo(f"\n  First example:      {stats['first_example']}")
        click.echo(f"  Last example:       {stats['last_example']}")
    else:
        # Show stats for all scenarios
        scenarios = collector.list_scenarios()

        if not scenarios:
            click.secho("❌ No training data found", fg="red")
            sys.exit(1)

        click.echo(f"\n📊 Training Data Overview ({len(scenarios)} scenarios)\n")

        for scenario_name in sorted(scenarios):
            stats = collector.get_dataset_stats(scenario_name)
            pass_rate_color = (
                "green"
                if stats["pass_rate"] >= 0.8
                else "yellow"
                if stats["pass_rate"] >= 0.5
                else "red"
            )
            pass_rate_str = f"{stats['pass_rate']:.1%}"

            click.echo(f"  {click.style(scenario_name, fg='cyan')}")
            click.echo(
                f"    Examples: {stats['total']} | Pass rate: {click.style(pass_rate_str, fg=pass_rate_color)}"
            )


@training.command("export")
@click.argument("scenario", type=str)
@click.option(
    "--output", type=click.Path(), help="Output file path (default: copies the existing .jsonl)"
)
@click.option("--filter-passed/--no-filter", default=True, help="Only include successful examples")
@click.option("--limit", type=int, help="Maximum number of examples to export")
@click.option(
    "--format", type=click.Choice(["jsonl", "json"]), default="jsonl", help="Output format"
)
def training_export(scenario, output, filter_passed, limit, format):
    """Export training data (already in DSPy format).

    Training data is stored natively in DSPy format, so this command
    filters and copies the dataset.

    Examples:
      kurt-eval training export 03_project_no_sources
      kurt-eval training export 03_project_no_sources --limit 50
      kurt-eval training export 03_project_no_sources --output my_dataset.jsonl
      kurt-eval training export 03_project_no_sources --format json
    """
    import json

    from framework.training_data import TrainingDataCollector

    training_dir = eval_dir / "training_data"
    collector = TrainingDataCollector(training_dir)

    # Load DSPy examples (already in DSPy format!)
    dspy_examples = collector.load_dspy_dataset(
        scenario_name=scenario,
        filter_passed=filter_passed,
        limit=limit,
    )

    if not dspy_examples:
        click.secho(f"❌ No training data found for {scenario}", fg="red")
        sys.exit(1)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        ext = "json" if format == "json" else "jsonl"
        output_path = training_dir / f"{scenario}_export.{ext}"

    # Save in requested format
    if format == "jsonl":
        # JSONL format (one JSON per line) - standard for DSPy
        with open(output_path, "w") as f:
            for ex in dspy_examples:
                json.dump(ex.toDict(), f)
                f.write("\n")
    else:
        # JSON array format
        with open(output_path, "w") as f:
            json.dump([ex.toDict() for ex in dspy_examples], f, indent=2)

    click.secho(f"✅ Exported {len(dspy_examples)} DSPy examples to {output_path}", fg="green")
    click.echo(f"   Format: {format.upper()}")

    # Show sample
    if dspy_examples:
        click.echo("\nSample example:")
        sample = dspy_examples[0].toDict()
        click.echo(f"  Prompt: {sample['prompt'][:100]}...")
        click.echo(f"  Outcome: {'✅ Success' if sample['outcome']['success'] else '❌ Failed'}")
        click.echo("\n💡 Ready to use with DSPy optimizers (MIPROv2, SIMBA, GEPA)")


@training.command("view")
@click.argument("scenario", type=str)
@click.option("--index", type=int, default=0, help="Example index to view (default: 0 = latest)")
@click.option("--filter-passed/--filter-failed", default=None, help="Filter by success/failure")
def training_view(scenario, index, filter_passed):
    """View a specific training example.

    Examples:
      kurt-eval training view 03_project_no_sources
      kurt-eval training view 03_project_no_sources --index 5
      kurt-eval training view 03_project_no_sources --filter-failed
    """
    from framework.training_data import TrainingDataCollector

    training_dir = eval_dir / "training_data"
    collector = TrainingDataCollector(training_dir)

    # Load examples
    examples = collector.load_dataset(
        scenario_name=scenario,
        filter_passed=filter_passed,
    )

    if not examples:
        click.secho(f"❌ No training data found for {scenario}", fg="red")
        sys.exit(1)

    if index >= len(examples):
        click.secho(f"❌ Index {index} out of range (only {len(examples)} examples)", fg="red")
        sys.exit(1)

    example = examples[index]

    # Display example
    status_color = "green" if example.passed else "red"
    status_icon = "✅" if example.passed else "❌"

    click.echo(f"\n{status_icon} Training Example #{index + 1}/{len(examples)}")
    click.echo(f"{'='*70}")
    click.secho(f"Status: {'PASSED' if example.passed else 'FAILED'}", fg=status_color, bold=True)
    click.echo(f"Timestamp: {example.timestamp}")
    click.echo(f"Duration: {example.timing.get('duration_seconds', 0):.1f}s")
    click.echo(f"Tool calls: {len(example.tool_calls)}")
    click.echo(f"Conversation turns: {len(example.conversation)}")

    click.echo("\n📝 Initial Prompt:")
    click.echo(f"  {example.initial_prompt}")

    click.echo("\n🔧 Tool Sequence:")
    for i, call in enumerate(example.tool_calls[:10], 1):  # Show first 10
        tool_name = call.get("tool", "unknown")
        click.echo(f"  {i}. {tool_name}")
    if len(example.tool_calls) > 10:
        click.echo(f"  ... and {len(example.tool_calls) - 10} more")

    click.echo("\n💬 Conversation Preview:")
    for turn in example.conversation[:5]:  # Show first 5 turns
        speaker = turn.get("speaker", "unknown")
        message = turn.get("message", "")[:100]
        speaker_color = "magenta" if speaker == "user" else "blue"
        click.secho(f"  {speaker.upper()}: {message}", fg=speaker_color)
    if len(example.conversation) > 5:
        click.echo(f"  ... {len(example.conversation) - 5} more turns")

    if not example.passed and example.error:
        click.echo("\n❌ Error:")
        click.secho(f"  {example.error}", fg="red")


if __name__ == "__main__":
    main()
