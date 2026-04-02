#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$(realpath "$0")")/../.."

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required for this smoke gate."
  exit 2
fi

uv run ruff check .
uv run pytest -q src/kurt/config/tests
