# P3 run_e5 — Colab / Studio Lab GPU Runbook

Turnkey steps to run the decisive lever-C comparison on a free/preemptible GPU.
`run_e5` is **preemption-safe**: re-running resumes (finished arms skipped, partial
training continued) as long as `CKPT_DIR`/`OUT_DIR` live on persistent storage (Drive).

**Compute:** ~5 heavy trainings × N seeds (oracle is eval-only). 1-seed pilot ≈ **7 GPU-h**
on a T4; full 3-seed ≈ **20–30 GPU-h**. Do the pilot first.

---

## Step 0 — one-time, on your Mac: bundle the inputs (~62 MB, not in git)

```bash
cd ~/PycharmProjects/tgnn-solv
bash scripts/experiments/bundle_e5_inputs.sh          # -> e5_inputs.tgz
```

Upload `e5_inputs.tgz` to your Google Drive (e.g. `MyDrive/tgnn-solv/e5_inputs.tgz`).
This carries the corrected split, the σ aux stream, and the VT-2005 oracle artifact.

---

## Step 1 — Colab: GPU runtime + persistent Drive

In Colab: **Runtime → Change runtime type → T4 GPU**. Then:

```python
# cell 1 — mount Drive (persistent across reconnects)
from google.colab import drive
drive.mount('/content/drive')
PERSIST = '/content/drive/MyDrive/tgnn-solv'   # checkpoints + results survive preemption
import os; os.makedirs(PERSIST, exist_ok=True)
```

## Step 2 — clone the branch + install

```bash
# cell 2
%cd /content
!git clone --branch sigma-grounded-cosmosac https://github.com/doctawho42/tgnn-solv.git tgnn-solv
%cd /content/tgnn-solv
!pip -q install -e .
# If torch_geometric / rdkit aren't pulled in by the editable install, add them explicitly:
#   !pip -q install torch_geometric rdkit
```

> The branch is already on GitHub (`origin/sigma-grounded-cosmosac`). If the repo is
> private, add a token to the URL: `https://<USER>:<TOKEN>@github.com/doctawho42/tgnn-solv.git`.
> The data is NOT in git — it comes from the bundle in Step 3.

## Step 3 — restore the data bundle into the repo

```bash
# cell 3
%cd /content/tgnn-solv
!tar xzf /content/drive/MyDrive/tgnn-solv/e5_inputs.tgz   # -> notebooks/data/... + results/sigma_profile_artifact
!ls notebooks/data/processed notebooks/data/processed_sigma_aux_stream results/sigma_profile_artifact
```

## Step 4 — the 1-seed PILOT (validate + calibrate)

Point `CKPT_DIR`/`OUT_DIR` at Drive so a disconnect resumes instead of restarting.

```bash
# cell 4 — pilot: 1 seed, all 6 arms, real GPU
%cd /content/tgnn-solv
!PY=python DEVICE=cuda SEEDS=42 \
  CKPT_DIR=/content/drive/MyDrive/tgnn-solv/ckpt_e5 \
  OUT_DIR=/content/drive/MyDrive/tgnn-solv/results_e5 \
  bash scripts/experiments/run_e5_sigma_grounding.sh
```

If Colab disconnects mid-run, just **re-run cell 4** — completed arms are skipped and a
partial arm resumes from its last `--checkpoint-every` checkpoint.

## Step 5 — read the pilot verdict + calibrate `--lngamma-band`

```python
# cell 5
import json
c = json.load(open('/content/drive/MyDrive/tgnn-solv/results_e5/seed_42/comparison.json'))
print('n_locked:', c['n_locked'])
for arm, m in c['per_arm'].items():
    print(f"  {arm:12s} R2={m['r2']:.3f}  MAE={m['mae']:.3f}  std(lng)={m['lngamma_std']}")
print('criteria:', json.dumps(c['criteria'], indent=2))
ung = c['per_arm']['ungrounded']['lngamma_std']
print(f"\nungrounded std(lng) = {ung}; suggested --lngamma-band ~ [{0.6*ung:.2f}, {1.6*ung:.2f}]")
```

The pilot's `--lngamma-band` used the default `[1.0, 2.0]`, so its `keeps_constraint`
flags are NOT authoritative. Use the printed ungrounded std(lnγ) to set a real band:
the band should bracket the ungrounded value (which genuinely narrowed activity) — a
grounded arm "keeps the constraint" if its std stays in a similar window (not collapsed
to ~0, not blown up). Sanity-check the pilot R²/MAE look like real numbers (not MAE 3+ /
R²~0, which would mean the run didn't actually use the GPU or didn't converge).

**Reading the oracle ceiling correctly (important).** `run_e5` uses
`--sigma-oracle-side both`, whose mask is an **OR**: a row gets the solute oracle where
the solute has a VT-2005 entry (~5% of rows) OR the solvent oracle where the solvent
matches (~99%). So `sigma_oracle_applied` ≈ 99% and `per_arm.oracle` measures a mostly
*solvent-grounded* ceiling — NOT strict "both profiles perfect". For the strict lever-C
ceiling (both solute+solvent perfect) the relevant rows are the ~5% where the solute
ALSO matches; for a clean *solute-only* ceiling re-export an arm with
`--sigma-oracle-side solute` and read its masked subset. In all cases the oracle ceiling
is NOT `per_arm.oracle` in comparison.json (diluted ≈ grounded_a) — read the masked-subset
block of the oracle arm's summary json:

```python
# cell 5b — true oracle ceiling on the ~5% covered rows
s = json.load(open('/content/drive/MyDrive/tgnn-solv/results_e5/seed_42/oracle_predictions.summary.json'))
print('oracle masked-subset (the lever-C ceiling):', {k: s.get(k) for k in ('n_oracle','sigma_oracle')})
```

## Step 6 — the full 3-seed matrix (after the pilot looks sane)

```bash
# cell 6 — full run with the calibrated band
%cd /content/tgnn-solv
!PY=python DEVICE=cuda SEEDS="42 43 44" \
  CKPT_DIR=/content/drive/MyDrive/tgnn-solv/ckpt_e5 \
  OUT_DIR=/content/drive/MyDrive/tgnn-solv/results_e5 \
  bash scripts/experiments/run_e5_sigma_grounding.sh
# then aggregate the three seeds' comparison.json (rescue/keeps as paired-seed effect with dispersion)
```

(seed 42 is already done from the pilot — it will be skipped; only 43/44 train.)

---

## Verdict reading (pre-registered)

- **rescue** = grounded cosmo_sac R² ≥ matched **DirectGNN-h64** R² on the `n_locked`
  intersection (NRTL ≈ 0.32 is a weaker milestone). Report as a **paired-seed** effect
  with dispersion across the 3 seeds — not a single point.
- **keeps-constraint** = std(lnγ) within the calibrated `--lngamma-band`.
- **n_supervised** (`n_locked`) is first-class — confirm it's stable across arms/seeds.
- **stratify** rescue by `ring_bearing` vs `acyclic` (in `comparison.json["stratified"]`);
  the test set is ~100% ring-bearing, so the ring-bearing row is the one that matters.
- A **null** stays partly ambiguous between {lever C not viable, σ-coverage too small,
  encoder ceiling R²~0.45} — the falsifier is pre-registered as "at this scale".

## Troubleshooting

- **MAE 3+ / R² ~ 0 on cosmo arms:** the run is on CPU or didn't converge — confirm the GPU
  runtime and that `DEVICE=cuda`.
- **`missing VT-2005 oracle artifact`:** the bundle didn't include `results/sigma_profile_artifact/` — re-run Step 0/3.
- **Disconnect:** just re-run the run_e5 cell; it resumes from Drive.
