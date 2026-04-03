#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage:
  bash scripts/training/run_resume_safe_train.sh [train.py args...]

Delegates to the legacy top-level resume-safe TGNN wrapper:
  scripts/run_resume_safe_train.sh

Useful environment variables:
  PYTHON_BIN         Explicit Python interpreter
  CHECKPOINT         Resume-safe checkpoint path
  CHECKPOINT_EVERY   Save frequency in epochs

All additional CLI arguments are forwarded to scripts/training/train.py.
EOF
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$SCRIPT_DIR/run_resume_safe_train.sh" "$@"
