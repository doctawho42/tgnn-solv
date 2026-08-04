#!/usr/bin/env bash
# Run ON the GCP GPU VM: the leak-free grounded/ungrounded contrast that closes editorial gate A1.
#
# The published +0.198 gain was measured with a sigma-stream whose scaffold guard had been pointed at
# a debug split from another project directory, so 87 held-out solutes reached the stream by
# canonical SMILES and 54 by Murcko scaffold. The stream is rebuilt here with the guard on the real
# val/test files and a post-build assertion that the intersection is empty by both keys; the build
# hash travels in the summary. This script re-runs the two arms the leak touched.
#
# Prereqs on the VM: ~/tgnn_a1_data.tgz uploaded (carries processed/ and the CLEAN stream).
# Usage:  bash gcp_a1_leakfree.sh              # 5 seeds, both arms
#         SEEDS="42 43 44" bash gcp_a1_leakfree.sh
set -euo pipefail

BRANCH=${BRANCH:-sigma-grounded-cosmosac}
REPO=${REPO:-https://github.com/doctawho42/tgnn-solv.git}
SEEDS=${SEEDS:-42 43 44 45 46}
ARMS=${ARMS:-ungrounded grounded_a}

[ -d tgnn-solv ] || git clone --branch "$BRANCH" "$REPO"
cd tgnn-solv

if [ -f "$HOME/tgnn_a1_data.tgz" ]; then
  tar xzf "$HOME/tgnn_a1_data.tgz"
  echo "[a1] data unpacked:"; du -sh notebooks/data/processed* 2>/dev/null || true
else
  echo "[a1] ERROR: $HOME/tgnn_a1_data.tgz not found"; exit 1
fi

# Certify the stream ON THE VM before spending a GPU-hour on it. The same assertion the builder
# carries, re-run here, because the whole point of the gate is that the guard was trusted once and
# should not be trusted again without a check at the point of use.
python - <<'PYCERT'
import json, sys, pandas as pd
sys.path.insert(0, "src")
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
from tgnn_solv.data.utils import scaffold_key

stream = pd.read_csv("notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv")
held = pd.concat([pd.read_csv("notebooks/data/processed/val.csv"),
                  pd.read_csv("notebooks/data/processed/test.csv")])
canon = lambda s: (Chem.MolToSmiles(Chem.MolFromSmiles(s)) if Chem.MolFromSmiles(s) else s)
held_smiles = {canon(str(s)) for s in held.solute_smiles.dropna().unique()}
held_scaffolds = {scaffold_key(str(s)) for s in held.solute_smiles.dropna().unique()}
leak_s = {canon(str(s)) for s in stream.solute_smiles} & held_smiles
leak_k = {scaffold_key(str(s)) for s in stream.solute_smiles} & held_scaffolds
summary = json.load(open("notebooks/data/processed_sigma_aux_stream_clean/summary.json"))
print(f"[a1] stream rows={len(stream)} sha256={summary['build_sha256'][:16]}")
print(f"[a1] leak by SMILES={len(leak_s)} by scaffold={len(leak_k)}")
if leak_s or leak_k:
    raise SystemExit("[a1] ABORT: the stream on this VM is not leak-free")
print("[a1] stream certified leak-free")
PYCERT

pip install -e . >/dev/null 2>&1 || pip install -e .

SEEDS="$SEEDS" ARMS="$ARMS" \
SIGMA_DIR=notebooks/data/processed_sigma_aux_stream_clean \
OUT_DIR=results/e5_sigma_grounding_leakfree \
CKPT_DIR=checkpoints/e5_leakfree \
DEVICE=cuda NUM_WORKERS=8 CHECKPOINT_EVERY=5 \
PY=$(which python) \
bash scripts/experiments/run_e5_sigma_grounding.sh

echo "[a1] done. Results in results/e5_sigma_grounding_leakfree/"
