#!/bin/bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-dspy-training/kurt-training

# Extract URLs from replacement-urls.txt and format as comma-separated
URLS=$(grep -E "^https://" replacement-urls.txt | tr '\n' ',' | sed 's/,$//')

echo "Fetching 18 replacement URLs..."

# Fetch with skip-index first (just download content, don't run LLM)
KURT_TELEMETRY_DISABLED=1 uv run kurt content fetch --urls "$URLS" --skip-index --yes --concurrency 3
