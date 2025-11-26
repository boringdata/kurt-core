#!/bin/bash
# Run conversational MotherDuck scenarios and aggregate results
#
# NOTE: This script is now replaced by the CLI command:
#   KURT_TELEMETRY_DISABLED=1 uv run python -m eval run-file \
#     scenarios_answer_motherduck_conversational.yaml \
#     --prefix answer_motherduck_conversational_q \
#     --parallel 4 \
#     --max-duration 300
#
# The CLI command runs scenarios in parallel for better performance.
# This script is kept for reference but sequential execution is slower.

set -e  # Exit on error

# Number of questions to run (default: 2 for testing, change to 10 for full run)
NUM_QUESTIONS=${1:-2}
PARALLEL=${2:-4}

echo "════════════════════════════════════════════════════════════════"
echo "DEPRECATED: Use the CLI command instead for parallel execution:"
echo ""
echo "  KURT_TELEMETRY_DISABLED=1 uv run python -m eval run-file \\"
echo "    scenarios_answer_motherduck_conversational.yaml \\"
echo "    --prefix answer_motherduck_conversational_q \\"
echo "    --parallel ${PARALLEL} \\"
echo "    --max-duration 300"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Option 1: Use new CLI command (recommended)
if command -v uv &> /dev/null; then
    echo "Using new parallel CLI command..."

    # Build the scenario filter dynamically based on NUM_QUESTIONS
    # For now, we just use the prefix filter and run all that match
    KURT_TELEMETRY_DISABLED=1 uv run python -m eval run-file \
        eval/scenarios/scenarios_answer_motherduck_conversational.yaml \
        --prefix answer_motherduck_conversational_q \
        --parallel ${PARALLEL} \
        --max-duration 300

    echo ""
    echo "✅ Complete! Results available at:"
    echo "   - Individual transcripts: eval/results/answer_motherduck_conversational_q*/*.md"
    echo "   - Aggregated transcript: eval/results/answer_motherduck_conversational_aggregate/full_transcript.md"
    echo "   - LLM judge scores: eval/results/answer_motherduck_conversational_aggregate/evaluation_results.json"

else
    echo "ERROR: uv command not found. Please install uv first."
    exit 1
fi
