#!/bin/bash
# Run both MotherDuck evaluation scenarios for GraphRAG vs Manual Search comparison

set -e

echo "=================================="
echo "MotherDuck GraphRAG vs Manual Search Comparison"
echo "=================================="
echo ""

# Run GraphRAG scenario (with knowledge graph)
echo "➤ Running GraphRAG scenario (with knowledge graph)..."
echo "  This uses kurt answer command with full entity resolution"
echo ""
KURT_TELEMETRY_DISABLED=1 uv run python -m eval run answer_motherduck --max-duration 180
echo ""
echo "✓ GraphRAG scenario completed"
echo ""

# Run baseline scenario (without knowledge graph)
echo "➤ Running Baseline scenario (without knowledge graph)..."
echo "  This uses Claude Code SDK sessions to search sources directly"
echo ""
KURT_TELEMETRY_DISABLED=1 uv run python -m eval run answer_motherduck_without_kg --max-duration 180
echo ""
echo "✓ Baseline scenario completed"
echo ""

# Display results
echo "=================================="
echo "COMPARISON RESULTS"
echo "=================================="
echo ""

echo "GraphRAG Results:"
if [ -f "eval/results/answer_motherduck/evaluation_results.json" ]; then
  echo "  Location: eval/results/answer_motherduck/evaluation_results.json"
  # Extract overall score if jq is available
  if command -v jq &> /dev/null; then
    GRAPHRAG_SCORE=$(jq -r '.aggregate_metrics.average_overall_score' eval/results/answer_motherduck/evaluation_results.json 2>/dev/null || echo "N/A")
    echo "  Average Overall Score: $GRAPHRAG_SCORE"
  fi
else
  echo "  (No results file found)"
fi
echo ""

echo "Baseline Results:"
if [ -f "eval/results/answer_motherduck_without_kg/evaluation_results.json" ]; then
  echo "  Location: eval/results/answer_motherduck_without_kg/evaluation_results.json"
  # Extract overall score if jq is available
  if command -v jq &> /dev/null; then
    BASELINE_SCORE=$(jq -r '.aggregate_metrics.average_overall_score' eval/results/answer_motherduck_without_kg/evaluation_results.json 2>/dev/null || echo "N/A")
    echo "  Average Overall Score: $BASELINE_SCORE"
  fi
else
  echo "  (No results file found)"
fi
echo ""

echo "To view detailed results:"
echo "  cat eval/results/answer_motherduck/evaluation_results.json"
echo "  cat eval/results/answer_motherduck_without_kg/evaluation_results.json"
echo ""
