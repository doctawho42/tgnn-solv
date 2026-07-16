# GCP runbook — 3-seed compensating-surrogate run

Turns the paper's single-run surrogate numbers (33 / 45 / 53% / top-2 73% / 3.3×) into **mean ± sd**
across 3 seeds — the load-bearing upgrade now that the mechanism is a headline.

- Compute: ~3 seeds × (40 warmup + 120 SLE epochs). On a **T4** ≈ 6–12 h total; on an **L4/A100** less.
- Cost on T4 on-demand ≈ **$5–10** (well inside the $300 credit).

---

## ⚠️ Two GCP gotchas to clear FIRST
1. **GPU quota is 0 by default.** Console → *IAM & Admin → Quotas* → filter **"GPUs (all regions)"** →
   select → *Edit* → request **1** (approval is often minutes, sometimes a day).
2. **Free-trial accounts cannot use GPUs.** You must **upgrade to a paid account** (Billing → *Upgrade*).
   This still spends the **$300 credit** — you just won't be charged beyond it. Without upgrading, VM
   creation fails with a GPU-not-allowed error no matter the quota.

Prereqs: `gcloud` CLI installed and `gcloud init` done; a project selected (`gcloud config set project <ID>`).

---

## Step 0 (local) — pack the data the clone won't bring
Only the gitignored splits + aux streams need uploading (~63 MB); `sigma_profiles.csv` and
`matched_pairs.csv` are in git.

```bash
cd ~/PycharmProjects/tgnn-solv
tar czf /tmp/tgnn_data.tgz \
    notebooks/data/processed \
    notebooks/data/processed_sigma_aux_stream \
    notebooks/data/processed_crystal_aux_stream
```

## Step 1 (local) — create the GPU VM
CUDA-12.1 Deep-Learning image (driver preinstalled); `pip install -e .` adds torch+deps on top.

```bash
gcloud compute instances create tgnn-sur \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --image-family=common-cu121-debian-11 \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=80GB
# (if that image family errors, list options:
#  gcloud compute images list --project deeplearning-platform-release --filter="family~cu12")
# Cheaper alternative: add  --provisioning-model=SPOT  (~60% off; re-run a seed if preempted).
# Faster alternative:  --machine-type=g2-standard-8 --accelerator=type=nvidia-l4,count=1
```

## Step 2 (local) — upload data + the bootstrap script
```bash
gcloud compute scp /tmp/tgnn_data.tgz            tgnn-sur:~/tgnn_data.tgz     --zone=us-central1-a
gcloud compute scp scripts/cloud/gcp_bootstrap.sh tgnn-sur:~/gcp_bootstrap.sh --zone=us-central1-a
```

## Step 3 (VM) — SSH in and run
```bash
gcloud compute ssh tgnn-sur --zone=us-central1-a
# then, on the VM:
tmux new -s sur          # so the run survives an SSH drop
bash ~/gcp_bootstrap.sh  # clone -> unpack data -> pip install -> verify CUDA -> 3 seeds -> pack
# detach with Ctrl-b d ; re-attach later with: tmux attach -t sur
```
The bootstrap prints the aggregate (`mean ± sd`) at the end and writes `~/surrogate_results.tgz`.
If `pip install -e .` leaves a CPU torch, the CUDA check will fail loudly — reinstall with
`pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121` and re-run.

## Step 4 (local) — pull the results back
```bash
gcloud compute scp tgnn-sur:~/surrogate_results.tgz /tmp/surrogate_results.tgz --zone=us-central1-a
tar xzf /tmp/surrogate_results.tgz -C ~/PycharmProjects/tgnn-solv/results/sur
cat ~/PycharmProjects/tgnn-solv/results/sur/surrogate_seeds/surrogate_seeds.json
```

## Step 5 (local) — ⚠️ DELETE the VM (stops all billing)
```bash
gcloud compute instances delete tgnn-sur --zone=us-central1-a --quiet
```

---

## What you get
`surrogate_seeds.json` → `aggregate` with `mean`/`sd`/`n` for each of:
`grounded_vs_true` (~0.33), `sle_vs_grounded` (~0.45), `sle_vs_true` (~0.53), `top2_evr` (~0.73),
`transfer_ratio` (~3.3). Drop the mean ± sd into `sections/compensation-surrogate.tex` and the abstract,
replacing the "single converged-run illustration; magnitudes provisional" hedge with the spread.

If a seed comes back wildly different from the committed single run, that's real signal (the magnitude
is genuinely seed-sensitive) — tell me and we keep the demoted framing rather than over-claim.
