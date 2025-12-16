"""Simplified scenario runner - no backward compatibility needed.

Key simplifications:
1. No conversational vs non-conversational distinction
2. All scenarios are just lists of prompts to execute
3. Unified execution through SDK
4. Simple output format
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .env_config import get_api_key


class SimpleRunner:
    """Simplified scenario runner that treats everything uniformly."""

    def __init__(self, scenario_config: Dict[str, Any], verbose: bool = True):
        """Initialize runner with scenario configuration.

        Args:
            scenario_config: Scenario configuration dict
            verbose: Whether to print output
        """
        self.config = scenario_config
        self.verbose = verbose
        self.results = []
        self.start_time = time.time()

    async def run(self) -> Dict[str, Any]:
        """Run the scenario.

        Returns:
            Results dictionary with outputs and metrics
        """
        # Get prompts to execute (everything is just a prompt)
        prompts = self._get_prompts()

        if not prompts:
            return {"error": "No prompts to execute", "results": []}

        self._log(f"\n🚀 Executing {len(prompts)} prompts")

        # Execute each prompt
        for i, prompt in enumerate(prompts, 1):
            self._log(f"\n{'='*60}")
            self._log(f"Prompt {i}/{len(prompts)}")
            self._log(f"{'='*60}")

            result = await self._execute_prompt(prompt, i)
            self.results.append(result)

            # Optional: Score with LLM judge
            if self.config.get("judge_enabled"):
                score = self._judge_result(prompt, result)
                result["judge_score"] = score

        # Calculate final metrics
        duration = time.time() - self.start_time
        total_tokens = sum(r.get("tokens", 0) for r in self.results)

        return {
            "scenario": self.config.get("name", "unnamed"),
            "results": self.results,
            "metrics": {
                "duration_seconds": duration,
                "total_tokens": total_tokens,
                "prompt_count": len(prompts),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def _get_prompts(self) -> List[str]:
        """Extract prompts from configuration.

        Handles various config formats but treats them all the same.
        """
        prompts = []

        # Direct prompt
        if "prompt" in self.config:
            prompts.append(self.config["prompt"])

        # List of prompts
        if "prompts" in self.config:
            prompts.extend(self.config["prompts"])

        # Questions (legacy format)
        if "questions" in self.config:
            for q in self.config["questions"]:
                if isinstance(q, str):
                    prompts.append(q)
                elif isinstance(q, dict):
                    prompts.append(q.get("question", q.get("prompt", str(q))))

        # Load from file if specified
        if "prompts_file" in self.config:
            prompts.extend(self._load_prompts_from_file(self.config["prompts_file"]))

        return prompts

    def _load_prompts_from_file(self, filepath: str) -> List[str]:
        """Load prompts from a file."""
        path = Path(filepath)
        if not path.exists():
            self._log(f"Warning: Prompts file not found: {filepath}")
            return []

        with open(path) as f:
            import yaml

            data = yaml.safe_load(f)

            # Handle various file formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("prompts", data.get("questions", []))

        return []

    async def _execute_prompt(self, prompt: str, index: int) -> Dict[str, Any]:
        """Execute a single prompt using the SDK.

        Everything goes through the SDK - no special cases.
        """
        self._log(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        try:
            # Import SDK (simplified from original)
            from anthropic import AsyncAnthropic

            # Get API key
            api_key = get_api_key("anthropic")
            client = AsyncAnthropic(api_key=api_key)

            # Simple execution - no complex hooks or tracking
            start = time.time()
            response = await client.messages.create(
                model="claude-3-5-sonnet-latest",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            duration = time.time() - start

            # Extract response
            answer = response.content[0].text if response.content else ""
            tokens = response.usage.total_tokens if hasattr(response, "usage") else 0

            self._log(f"✅ Response received ({tokens} tokens, {duration:.2f}s)")

            return {
                "prompt": prompt,
                "response": answer,
                "tokens": tokens,
                "duration": duration,
                "index": index,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self._log(f"❌ Error: {e}")
            return {
                "prompt": prompt,
                "error": str(e),
                "index": index,
                "timestamp": datetime.now().isoformat(),
            }

    def _judge_result(self, prompt: str, result: Dict[str, Any]) -> Optional[float]:
        """Score a result using LLM judge (simplified)."""
        if "error" in result or "response" not in result:
            return None

        try:
            # Simplified judging - just ask for a score
            judge_prompt = f"""
            Question: {prompt}
            Answer: {result['response']}

            Rate this answer from 0 to 1 based on accuracy, completeness, and clarity.
            Respond with just a number between 0 and 1.
            """

            # Use sync client for simplicity
            from anthropic import Anthropic

            client = Anthropic(api_key=get_api_key("anthropic"))

            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=10,
            )

            # Parse score
            score_text = response.content[0].text.strip()
            score = float(score_text)
            self._log(f"   🧠 Judge score: {score:.2f}")
            return score

        except Exception as e:
            self._log(f"   ⚠️  Judge error: {e}")
            return None

    def save_results(self, output_dir: Optional[Path] = None):
        """Save results to disk (simplified format)."""
        if not output_dir:
            output_dir = Path("eval/results")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_name = self.config.get("name", "scenario")

        # Single JSON file with everything
        output_file = output_dir / f"{scenario_name}_{timestamp}.json"

        results = {
            "scenario": scenario_name,
            "config": self.config,
            "results": self.results,
            "timestamp": timestamp,
            "metrics": {
                "total_prompts": len(self.results),
                "successful": sum(1 for r in self.results if "response" in r),
                "failed": sum(1 for r in self.results if "error" in r),
                "total_tokens": sum(r.get("tokens", 0) for r in self.results),
                "total_duration": sum(r.get("duration", 0) for r in self.results),
                "average_score": self._calculate_average_score(),
            },
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        self._log(f"\n💾 Results saved to {output_file}")

        # Optional: Save readable summary
        summary_file = output_dir / f"{scenario_name}_{timestamp}_summary.md"
        self._save_summary(summary_file, results)

    def _save_summary(self, filepath: Path, results: Dict[str, Any]):
        """Save human-readable summary."""
        with open(filepath, "w") as f:
            f.write(f"# Scenario: {results['scenario']}\n\n")
            f.write(f"Timestamp: {results['timestamp']}\n\n")

            f.write("## Metrics\n\n")
            for key, value in results["metrics"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n## Results\n\n")
            for r in results["results"]:
                f.write(f"### Prompt {r.get('index', '?')}\n\n")
                f.write(f"**Prompt**: {r.get('prompt', 'N/A')[:200]}...\n\n")

                if "response" in r:
                    f.write(f"**Response**: {r['response'][:500]}...\n\n")
                elif "error" in r:
                    f.write(f"**Error**: {r['error']}\n\n")

                if "judge_score" in r:
                    f.write(f"**Score**: {r['judge_score']:.2f}\n\n")

                f.write("---\n\n")

    def _calculate_average_score(self) -> Optional[float]:
        """Calculate average judge score if available."""
        scores = [r.get("judge_score") for r in self.results if "judge_score" in r]
        if scores:
            return sum(scores) / len(scores)
        return None

    def _log(self, message: str):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message)


# Simplified execution function
async def run_scenario(config: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
    """Run a scenario with the given configuration.

    Args:
        config: Scenario configuration
        verbose: Whether to print output

    Returns:
        Results dictionary
    """
    runner = SimpleRunner(config, verbose)
    results = await runner.run()
    runner.save_results()
    return results


# Example usage
if __name__ == "__main__":
    # Example configuration - everything is just prompts
    example_config = {
        "name": "test_scenario",
        "prompts": [
            "What is Python?",
            "Explain async/await in Python",
            "Write a hello world program",
        ],
        "judge_enabled": True,
    }

    # Run it
    asyncio.run(run_scenario(example_config))
