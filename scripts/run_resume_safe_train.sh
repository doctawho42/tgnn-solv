#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

CHECKPOINT="${CHECKPOINT:-checkpoints/cloud_tgnn_solv.pt}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-5}"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_EXEC="${PYTHON_BIN}"
elif [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
  PYTHON_EXEC="${CONDA_PREFIX}/bin/python"
else
  PYTHON_EXEC="$(command -v python)"
fi

RESUME_ARGS=()
if [[ -f "${CHECKPOINT}" ]]; then
  echo "Resuming from ${CHECKPOINT}"
  RESUME_ARGS=(--resume "${CHECKPOINT}")
else
  echo "Starting a fresh run; checkpoint will be written to ${CHECKPOINT}"
fi

exec "${PYTHON_EXEC}" scripts/train.py \
  --checkpoint "${CHECKPOINT}" \
  --checkpoint-every "${CHECKPOINT_EVERY}" \
  "${RESUME_ARGS[@]}" \
  "$@"
