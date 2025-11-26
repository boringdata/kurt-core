#!/usr/bin/env python3
"""LLM judge for evaluating generated answers against canonical answers.

This script:
1. Reads a generated answer file (markdown)
2. Loads the canonical answer from questions_motherduck.yaml
3. Uses gpt-4o to evaluate answer quality
4. Writes/updates evaluation metrics to the scenario's JSON results file
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import dspy
import yaml
from dotenv import load_dotenv

# Load environment variables from eval/.env
eval_dir = Path(__file__).parent.parent.parent.absolute()
env_file = eval_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}")


class AnswerJudge(dspy.Signature):
    """Evaluate a generated answer against a canonical/expected answer.

    Rate the generated answer on:
    - Accuracy: Does it provide correct information?
    - Completeness: Does it cover all key points from the canonical answer?
    - Clarity: Is it well-structured and easy to understand?

    Provide scores (0-100) and brief reasoning for each dimension.
    """

    question = dspy.InputField(desc="The original question")
    canonical_answer = dspy.InputField(desc="The expected/reference answer")
    generated_answer = dspy.InputField(desc="The answer to evaluate")

    accuracy_score = dspy.OutputField(desc="Accuracy score (0-100): correctness of information")
    accuracy_reasoning = dspy.OutputField(desc="Brief explanation of accuracy score")

    completeness_score = dspy.OutputField(desc="Completeness score (0-100): coverage of key points")
    completeness_reasoning = dspy.OutputField(desc="Brief explanation of completeness score")

    clarity_score = dspy.OutputField(desc="Clarity score (0-100): structure and readability")
    clarity_reasoning = dspy.OutputField(desc="Brief explanation of clarity score")

    overall_score = dspy.OutputField(desc="Overall score (0-100): weighted average")
    summary = dspy.OutputField(desc="One-sentence summary of the evaluation")


def load_canonical_answer(question_num: int) -> tuple[str, str]:
    """Load question and canonical answer from questions file.

    Args:
        question_num: Question number (1-10)

    Returns:
        Tuple of (question, canonical_answer)
    """
    questions_file = Path("eval/scenarios/questions_motherduck.yaml")

    if not questions_file.exists():
        raise FileNotFoundError(f"Questions file not found: {questions_file}")

    with open(questions_file) as f:
        data = yaml.safe_load(f)

    questions = data.get("questions", [])

    if question_num < 1 or question_num > len(questions):
        raise ValueError(f"Invalid question number: {question_num} (must be 1-{len(questions)})")

    q_data = questions[question_num - 1]
    return q_data["question"], q_data["expected_answer"]


def read_generated_answer(answer_file: Path) -> str:
    """Read generated answer from markdown file.

    Args:
        answer_file: Path to answer markdown file

    Returns:
        Answer text (excluding metadata sections)
    """
    if not answer_file.exists():
        raise FileNotFoundError(f"Answer file not found: {answer_file}")

    with open(answer_file) as f:
        content = f.read()

    # Extract main answer (before ## Sources or ## Metadata)
    lines = content.split('\n')
    answer_lines = []
    in_answer = False

    for line in lines:
        if line.startswith('# Answer'):
            in_answer = True
            continue
        elif line.startswith('## '):
            # Stop at Sources, Metadata, etc.
            break
        elif in_answer:
            answer_lines.append(line)

    answer = '\n'.join(answer_lines).strip()
    return answer


def find_matching_results_json(answer_file: Path, results_dir: Path) -> Path:
    """Find the JSON file closest in time to the answer file.

    Since the answer file is copied with $(date) which may differ by 1-2 seconds
    from the scenario JSON file, we find the JSON file with the closest timestamp.

    Args:
        answer_file: Path to answer markdown file
        results_dir: Path to scenario results directory

    Returns:
        Path to matching JSON file
    """
    # Find all JSON files (excluding _answer.json if any)
    json_files = [f for f in results_dir.glob("*.json") if not f.name.endswith("_answer.json")]

    if not json_files:
        raise FileNotFoundError(f"No JSON results files found in {results_dir}")

    # Get answer file modification time
    answer_mtime = answer_file.stat().st_mtime

    # Find JSON file with closest modification time
    closest_json = min(json_files, key=lambda f: abs(f.stat().st_mtime - answer_mtime))

    return closest_json


def evaluate_answer(
    question: str,
    canonical_answer: str,
    generated_answer: str,
    lm: dspy.LM
) -> dict:
    """Evaluate generated answer using LLM judge.

    Args:
        question: The original question
        canonical_answer: Expected answer
        generated_answer: Answer to evaluate
        lm: DSPy language model

    Returns:
        Dictionary with evaluation metrics
    """
    # Configure DSPy to use the LM
    dspy.configure(lm=lm)

    # Create judge module
    judge = dspy.Predict(AnswerJudge)

    # Run evaluation
    result = judge(
        question=question,
        canonical_answer=canonical_answer,
        generated_answer=generated_answer
    )

    # Extract scores
    evaluation = {
        "accuracy": {
            "score": int(result.accuracy_score),
            "reasoning": result.accuracy_reasoning
        },
        "completeness": {
            "score": int(result.completeness_score),
            "reasoning": result.completeness_reasoning
        },
        "clarity": {
            "score": int(result.clarity_score),
            "reasoning": result.clarity_reasoning
        },
        "overall": {
            "score": int(result.overall_score),
            "summary": result.summary
        },
        "timestamp": datetime.now().isoformat()
    }

    return evaluation


def find_latest_answer_file(results_dir: Path) -> Path:
    """Find the latest _answer.md file in the results directory.

    Args:
        results_dir: Path to scenario results directory

    Returns:
        Path to latest answer file
    """
    if not results_dir.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    answer_files = list(results_dir.glob("*_answer.md"))

    if not answer_files:
        raise FileNotFoundError(f"No answer files found in {results_dir}")

    # Return the most recently modified answer file
    return max(answer_files, key=lambda p: p.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(description="Evaluate answer with LLM judge")
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Path to scenario results directory (e.g., eval/results/answer_motherduck_with_kg_q1)"
    )
    parser.add_argument(
        "--question-num",
        type=int,
        required=True,
        help="Question number (1-10)"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        required=True,
        help="File prefix/timestamp (e.g., 20251126_210220)"
    )

    args = parser.parse_args()

    # Derive scenario name from results directory path
    scenario_name = args.results_dir.name

    print(f"🔍 Evaluating answer for: {scenario_name}")
    print(f"   Question: #{args.question_num}")
    print(f"   Results directory: {args.results_dir}")
    print(f"   Prefix: {args.prefix}")

    # Construct file paths using prefix
    answer_file = args.results_dir / f"{args.prefix}_answer.md"

    if not answer_file.exists():
        print(f"❌ Answer file not found: {answer_file}")
        sys.exit(1)

    print(f"   Answer file: {answer_file}")

    # Load canonical answer
    try:
        question, canonical_answer = load_canonical_answer(args.question_num)
        print(f"   Question: {question}")
    except Exception as e:
        print(f"❌ Failed to load canonical answer: {e}")
        sys.exit(1)

    # Read generated answer
    try:
        generated_answer = read_generated_answer(answer_file)
        print(f"   Generated answer length: {len(generated_answer)} chars")
    except Exception as e:
        print(f"❌ Failed to read answer file: {e}")
        sys.exit(1)

    # Initialize LLM (gpt-4o)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    lm = dspy.LM('openai/gpt-4o', api_key=api_key)

    # Evaluate answer
    print("🤖 Running LLM judge evaluation...")
    try:
        evaluation = evaluate_answer(
            question=question,
            canonical_answer=canonical_answer,
            generated_answer=generated_answer,
            lm=lm
        )
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

    # Print results
    print("\n📊 Evaluation Results:")
    print(f"   Accuracy:     {evaluation['accuracy']['score']}/100")
    print(f"   Completeness: {evaluation['completeness']['score']}/100")
    print(f"   Clarity:      {evaluation['clarity']['score']}/100")
    print(f"   Overall:      {evaluation['overall']['score']}/100")
    print(f"   Summary:      {evaluation['overall']['summary']}")

    # Find matching results JSON file (closest timestamp to answer file)
    try:
        results_json = find_matching_results_json(answer_file, args.results_dir)
        print(f"\n💾 Writing to: {results_json}")
    except Exception as e:
        print(f"❌ Failed to find matching results JSON file: {e}")
        sys.exit(1)

    # Load existing data if file exists
    if results_json.exists():
        with open(results_json) as f:
            data = json.load(f)
    else:
        data = {}

    # Add evaluation to results
    data["llm_judge_evaluation"] = evaluation

    # Write updated results
    with open(results_json, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Evaluation complete!")


if __name__ == "__main__":
    main()
