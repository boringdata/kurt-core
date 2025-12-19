#!/bin/bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-dspy-training/kurt-training

# Extract URLs from training-urls.txt and format as comma-separated
URLS=$(grep -E "^https://" training-urls.txt | tr '\n' ',' | sed 's/,$//')

echo "Fetching 50 training URLs..."
echo "First few URLs: $(echo $URLS | cut -c1-100)..."

# Fetch with skip-index first (just download content, don't run LLM)
KURT_TELEMETRY_DISABLED=1 uv run kurt content fetch --urls "$URLS" --skip-index --yes --concurrency 3
