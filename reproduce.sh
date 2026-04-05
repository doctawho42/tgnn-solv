#!/bin/bash
set -euo pipefail

if ! command -v python >/dev/null 2>&1; then
  echo "ERROR: Python not found in PATH" >&2
  exit 1
fi

exec python scripts/experiments/reproduce_paper.py --profile article "$@"
