#!/usr/bin/env bash
# Reproduce SecOps-2k end to end: generate, validate, Drain, golden, test.
set -euo pipefail
cd "$(dirname "$0")"

uv sync --extra dev
uv run python scripts/generate.py
uv run python scripts/validate.py
uv run python scripts/score_baseline.py
uv run python scripts/verify_golden.py
uv run pytest -q
echo "reproduce OK — see results/baseline.md"
