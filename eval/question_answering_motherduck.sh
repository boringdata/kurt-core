#!/bin/bash
# MotherDuck Question Answering Evaluation
#
# Compare GraphRAG (WITH KG) vs Vector-Only (WITHOUT KG) approaches
# using LLM-as-judge evaluation

set -e  # Exit on error

# Configuration
NUM_QUESTIONS=${1:-2}  # Default to 2 questions, or pass as first argument
PARALLEL=${2:-2}       # Number of parallel workers
MAX_DURATION=300       # 5 minutes per question

echo "════════════════════════════════════════════════════════════════"
echo "MotherDuck Question Answering Evaluation"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Configuration:"
echo "  Questions to run:  $NUM_QUESTIONS"
echo "  Parallel workers:  $PARALLEL"
echo "  Max duration:      ${MAX_DURATION}s per question"
echo ""
echo "This will:"
echo "  1. Run WITHOUT KG scenarios (Vector-only approach)"
echo "  2. Run WITH KG scenarios (GraphRAG approach)"
echo "  3. Compare both with LLM-as-judge"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Clean up previous results
echo "🧹 Cleaning up previous results..."
rm -f /tmp/answer_without_kg_*.md
rm -f /tmp/answer_with_kg_*.md
rm -f eval/results/comparison_report.md
rm -f eval/results/comparison_report.json
echo "✓ Cleanup complete"
echo ""

# Step 1: Run WITHOUT KG scenarios
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1: Running WITHOUT KG scenarios (Vector-only)"
echo "════════════════════════════════════════════════════════════════"
echo ""

KURT_TELEMETRY_DISABLED=1 uv run python -m eval run-file \
  eval/scenarios/scenarios_answer_motherduck_without_kg.yaml \
  --parallel $PARALLEL \
  --max-duration $MAX_DURATION

echo ""
echo "✓ WITHOUT KG scenarios complete"
echo ""

# Verify WITHOUT KG outputs
WITHOUT_KG_COUNT=$(ls /tmp/answer_without_kg_*.md 2>/dev/null | wc -l | tr -d ' ')
echo "Generated $WITHOUT_KG_COUNT WITHOUT KG answer files"

if [ "$WITHOUT_KG_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No WITHOUT KG answer files were created"
    exit 1
fi
echo ""

# Step 2: Run WITH KG scenarios
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2: Running WITH KG scenarios (GraphRAG)"
echo "════════════════════════════════════════════════════════════════"
echo ""

KURT_TELEMETRY_DISABLED=1 uv run python -m eval run-file \
  eval/scenarios/scenarios_answer_motherduck_with_kg.yaml \
  --parallel $PARALLEL \
  --max-duration $MAX_DURATION

echo ""
echo "✓ WITH KG scenarios complete"
echo ""

# Verify WITH KG outputs
WITH_KG_COUNT=$(ls /tmp/answer_with_kg_*.md 2>/dev/null | wc -l | tr -d ' ')
echo "Generated $WITH_KG_COUNT WITH KG answer files"

if [ "$WITH_KG_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No WITH KG answer files were created"
    exit 1
fi

if [ "$WITHOUT_KG_COUNT" -ne "$WITH_KG_COUNT" ]; then
    echo "⚠️  WARNING: Mismatch in answer counts (WITHOUT KG: $WITHOUT_KG_COUNT, WITH KG: $WITH_KG_COUNT)"
fi
echo ""

# Step 3: Compare both approaches
echo "════════════════════════════════════════════════════════════════"
echo "STEP 3: Comparing approaches with LLM-as-judge"
echo "════════════════════════════════════════════════════════════════"
echo ""

KURT_TELEMETRY_DISABLED=1 uv run python eval/mock/generators/compare_approaches.py \
  --with-kg-files "/tmp/answer_with_kg_*.md" \
  --without-kg-files "/tmp/answer_without_kg_*.md" \
  --questions-file eval/scenarios/questions_motherduck.yaml \
  --output eval/results/comparison_report.md

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ EVALUATION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Results available at:"
echo "  📊 Comparison report: eval/results/comparison_report.md"
echo "  📊 JSON results:      eval/results/comparison_report.json"
echo ""
echo "Answer files:"
echo "  📝 WITHOUT KG:        /tmp/answer_without_kg_*.md ($WITHOUT_KG_COUNT files)"
echo "  📝 WITH KG:           /tmp/answer_with_kg_*.md ($WITH_KG_COUNT files)"
echo ""
