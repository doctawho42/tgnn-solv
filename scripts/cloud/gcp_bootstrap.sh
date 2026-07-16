#!/usr/bin/env bash
# Run ON the GCP GPU VM to execute the 3-seed compensating-surrogate run.
# Prereq: the data tarball is already at ~/tgnn_data.tgz (see gcp_surrogate_seeds.md, Step 0/2).
# Usage:  bash gcp_bootstrap.sh            # 40 warmup / 120 SLE epochs per seed (default)
#         WARM=40 SLE=120 bash gcp_bootstrap.sh
set -euo pipefail

BRANCH=sigma-grounded-cosmosac
REPO=https://github.com/doctawho42/tgnn-solv.git
WARM=${WARM:-40}
SLE=${SLE:-120}

# 1. code -----------------------------------------------------------------
[ -d tgnn-solv ] || git clone --branch "$BRANCH" "$REPO"
cd tgnn-solv

# 2. data (gitignored splits + aux streams; sigma_profiles.csv/matched_pairs.csv come from git)
if [ -f "$HOME/tgnn_data.tgz" ]; then
  tar xzf "$HOME/tgnn_data.tgz"
  echo "[bootstrap] data unpacked:"; du -sh notebooks/data/processed* 2>/dev/null || true
else
  echo "[bootstrap] ERROR: $HOME/tgnn_data.tgz not found -- upload it first (runbook Step 2)"; exit 1
fi

# 3. install + verify CUDA ------------------------------------------------
# Current Ubuntu DLVM images ship torch+CUDA system-wide (python3) but have NO `python`
# symlink (kaggle_run.py's subprocess calls "python"), are PEP-668 externally-managed,
# and do not include scikit-learn (used by the analysis scripts).
command -v python >/dev/null 2>&1 || sudo ln -sf /usr/bin/python3 /usr/local/bin/python
pip install -q --break-system-packages -e . scikit-learn scipy
KMP_DUPLICATE_LIB_OK=TRUE python - <<'PY'
import torch, torch_geometric, rdkit, sklearn  # noqa: F401
assert torch.cuda.is_available(), "CUDA not available -- wrong VM image or torch is the CPU build (see runbook)"
print("[bootstrap] CUDA OK:", torch.cuda.get_device_name(0), "| torch", torch.__version__)
PY

# 4. run: 3-seed surrogate isolation -> mean+/-sd of 33/45/53/73%/3.3x -----
KMP_DUPLICATE_LIB_OK=TRUE python scripts/cloud/kaggle_run.py \
    --do surrogate_seeds --out results/sur --device cuda --warm "$WARM" --sle "$SLE"

# 5. show + pack results --------------------------------------------------
echo "===== surrogate_seeds.json ====="
cat results/sur/surrogate_seeds/surrogate_seeds.json
tar czf "$HOME/surrogate_results.tgz" -C results/sur surrogate_seeds
echo "[bootstrap] DONE -> ~/surrogate_results.tgz  (download it, then DELETE the VM)"
