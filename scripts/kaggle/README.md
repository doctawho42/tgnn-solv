# Running the outstanding GPU arms on Kaggle

## What is outstanding, and why

Two training arms of §3.1 stand at **one seed** against five-seed comparators:

| arm | what it does | why it matters |
|---|---|---|
| `grounded_a_truetrain` | injects the reference σ-profile during **training**, so the crystal and correction branches co-adapt to it | the confound-free arm — it removes the distribution shift the evaluation-time substitution carries. The `+0.18` comes from here |
| `channel_swap` | the same injection under coordinate descent, which freezes Φ in phase 2 so only the activity branch is refit | isolates whether the σ→γ map is the ceiling independently of the crystal branch |

The referee report's **M3** is that a single-seed contrast of +0.18 is not an effect size when the
five-seed arms carry a between-seed s.d. of 0.06–0.11 and a per-seed range of 0.238. It is right,
and these runs are cheap. This directory queues them.

## The complication, found while packing

**The σ-stream the published five-seed family trained on was not retained.** The checkpoint
manifests record it by digest:

    notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv  955a1862…
    notebooks/data/processed_sigma_aux_stream_clean/sigma_val.csv    daf72c20…

Neither file exists on this machine. The `…_clean/` directory holds a *different* build (`bbe02152`,
1319 rows, **no validation split**), and `sigma_val.csv` is absent entirely; the files the runs
actually read lived on the compute host, whose project is no longer reachable. The bundler's digest
assertion caught this on its first run, before anything was uploaded.

Rebuilding with the recorded parameters (`--val-fraction 0.1 --split-seed 0`, scaffolds excluded
from test and val) reproduces:

* the **pool** exactly — the same 1319 molecules, σ-profiles bit-equal (`max|diff| = 0`);
* the **split sizes** exactly — 1187 / 132, the counts the manifests record;

but **not** the train/val *assignment*, which cannot be checked against a file that no longer
exists. `sigma_val` drives early stopping of the σ warm-up, so a different assignment moves where
the warm-up stops. `scripts/kaggle/check_stream_equivalence.py` is the artifact that establishes
all of this; its output is in `results/stream_equivalence.json` and is embedded in the bundle's
`MANIFEST.json`.

**This is a fourth defect on the deposited record**, beside the three the Data Availability
statement already discloses.

### What follows for the run design

`grounded_a` is queued **alongside** the two outstanding arms, at all five seeds, so the contrast
is *within* one stream and does not rest on the unverifiable assignment. That is **15 arms**, not
10 — about 2 h each on a T4, so ~30 GPU-hours, which is one Kaggle week at the 30 h quota.

The cheaper alternative is 10 arms (drop `grounded_a`) and compare against the published family
across the stream change. That is defensible only if the note above travels with every number.
Generate the notebook with `--arms grounded_a_truetrain channel_swap` to take it.

## Procedure

```bash
# 1. rebuild the stream and prove what the rebuild does and does not reproduce
python scripts/kaggle/check_stream_equivalence.py --json results/stream_equivalence.json

# 2. assemble the dataset (28 MB: code + data + digests)
python scripts/kaggle/build_kaggle_bundle.py --out /tmp/kaggle_tgnn_solv --force

# 3. generate the notebook into the same directory
python scripts/kaggle/make_notebook.py --out /tmp/kaggle_tgnn_solv/tgnn-solv-e5.ipynb
```

Then, on Kaggle:

1. **Upload the dataset with the CLI, not the browser.** The bundle is 484 files in 35 directories
   nested up to thirteen deep, and Kaggle's web uploader fails on it with `Failed to execute 'json'
   on 'Response': Unexpected end of JSON input` -- a client-side failure on file count, not on the
   28 MB. The CLI sends one archive per directory and Kaggle extracts it server-side, so the paths
   the notebook expects survive:

   ```
   cat > <bundle>/dataset-metadata.json <<'EOF'
   {"title": "tgnn-solv-e5", "id": "<user>/tgnn-solv-e5", "licenses": [{"name": "CC0-1.0"}]}
   EOF
   kaggle datasets create -p <bundle> -r zip --dir-mode zip
   ```

   Check it landed by size rather than by the file listing, which is paginated and will show only
   `code/` on its first page: `totalBytes` from the dataset view should match the bundle's own.
   Keep the notebook OUT of the bundle directory -- it is imported into Code, not the dataset.
2. **Code → New Notebook**, import `tgnn-solv-e5.ipynb`, attach the dataset.
3. Settings: **Accelerator = GPU**, **Internet = ON** (pip needs it), Persistence = Variables and Files.
4. Run. It stops starting new arms at 11 h, leaving an hour to write.
5. **Save `/kaggle/working/out` as a Dataset version** named `tgnn-solv-e5-out`.
6. Next session: attach *both* datasets and run the same notebook. Finished arms are skipped,
   partial ones resume from their checkpoint.

The runner is **seed-major**: all arms of one seed finish before the next seed starts, so an
interrupted run leaves complete seeds rather than a ragged matrix. Five arms at seed 42 is a
result; one arm at each of five seeds is not.

## Bringing it home

```bash
python scripts/kaggle/ingest_kaggle_outputs.py --from ~/Downloads/out --dry-run
python scripts/kaggle/ingest_kaggle_outputs.py --from ~/Downloads/out
```

It refuses to copy anything unless **every** predictions file is complete and **every** checkpoint
manifest names the same split digests the published family used. It *reports* the σ-stream digest
rather than asserting it — that one will not match, by construction, and the mismatch must travel
with the numbers rather than be silently absorbed.

## Not queued here, and why

* **The hyperparameter-matched control (M4).** DirectGNN and the physics arm were tuned separately,
  and a matched control means a matched *search budget*, not a shared schedule — roughly 20 trials
  × 2 arms, which is beyond a Kaggle quota. A shared-schedule control is cheap and answers a
  narrower question; it is a design decision, not an oversight.
* **The typed σ-head for the 2010/dsp closure.** The deployed head emits an untyped 51-bin profile
  and that kernel reads a typed 153-grid, so this needs new architecture and not just GPU time.
* **The substituted arm on the UD ∩ BigSolDB set (437 rows).** That one is CPU-sized and every
  input is already on disk; it does not belong on Kaggle.
