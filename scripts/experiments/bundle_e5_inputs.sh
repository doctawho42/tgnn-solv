#!/usr/bin/env bash
# Bundle the (untracked, ~62 MB) run_e5 inputs into a single tarball for upload to a
# GPU env (Colab Drive / HF dataset / scp). Run from the repo root.
#   bash scripts/experiments/bundle_e5_inputs.sh            # -> e5_inputs.tgz
#   OUT=/path/e5_inputs.tgz bash scripts/experiments/bundle_e5_inputs.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT="${OUT:-e5_inputs.tgz}"
paths=(
  notebooks/data/processed                      # corrected split (train/val/test)
  notebooks/data/processed_sigma_aux_stream     # sigma aux stream (+ sigma_val if built)
  results/sigma_profile_artifact                # VT-2005 oracle artifact
)
for p in "${paths[@]}"; do
  [ -e "$p" ] || { echo "missing input: $p" >&2; exit 1; }
done
tar czf "${OUT}" "${paths[@]}"
echo "wrote ${OUT} ($(du -h "${OUT}" | cut -f1)); on the GPU box: tar xzf ${OUT} at the repo root"
