# Gate A1, the leak-free re-run

## SUPERSEDED, 2026-08-10 03:20: all ten arm-runs restarted from scratch

Everything below describes the runs that landed at seeds 42–44 and were training at 45–46. They are
**not the measurement of record any more**, and they never satisfied the protocol printed in §2.2.

The provenance certificate — run for the first time on 2026-08-10, because the script that runs it
did not exist on the VM — failed all six manifests of seeds 42–44:

- the grounded arms carry the stream hash but **not the in-run leak check**: their manifests predate
  `train.py`'s point-of-use certification block;
- the ungrounded arms do not **assert** the absence of a σ stream, and §2.2 requires absence to be
  asserted rather than inferred.

The cause is one fact with three faces: the VM's tree stood at `bed7ba9`, the last pushed commit, and
the certification block was written after it. The gate driver that runs the check was not there
either, which is why the relaunch called the training driver directly and skipped it. Seeds 45/46,
restarted on the current code at 03:07, did get the block — but at phase-2 epoch 34 of 70, so
GPU-hours preceded the check for them too.

**The stream is clean either way.** External certification, twice, against the same file by hash:
0 leaks by canonical SMILES and 0 by Bemis–Murcko scaffold, `sha256 955a1862`, against 5101 held-out
SMILES and 2702 held-out scaffolds. The in-run block then found something the external check had
missed entirely: there are **two** streams, not one — `sigma_val`, 132 rows, `sha256 daf72c20`, also
0/0. The external check looked at `sigma_train` alone because that is the file I remembered. A
point-of-use check tests what the run opens; an external one tests what the checker recalls.

**What replaced it.** All ten arm-runs (seeds 42–46 × two arms) restarted from scratch at 03:20 under
the branch as pushed, with the certification running before the first GPU-hour: 10/10 logs carry the
4b block, 0/10 are resumptions. The prior results, checkpoints and logs are kept at
`results/e5_sigma_grounding_leakfree_precert`, `checkpoints/e5_leakfree_precert` and `~/a1_precert/`
so the two triples can be compared — but the new one is the measurement of record, and the choice
between them is not available after the fact.

Expect the new per-seed values to differ: a run from scratch follows a different RNG trajectory from
one resumed at epoch 30. The sign and the order of the gain are what the three landed seeds make
likely, not the digits.

---


**Status: INCOMPLETE against the protocol printed in §2.2.** That paragraph commits to five seeds,
42 through 46, and states its decision rule over *five* per-seed gains. Seeds 45 and 46 were
launched 2026-08-10 00:23 and are running; nothing here may be read as the pre-declared result until
they land. What follows is what three seeds say.

## Stream certification

| | |
|---|---|
| stream | `notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv` |
| sha256 | `955a1862ba2f5d31…` |
| rows / unique molecules | 1187 / 1185 |
| held out (val + test) | 5101 canonical SMILES, 2702 Bemis–Murcko scaffolds |
| **leak by SMILES** | **0** |
| **leak by scaffold** | **0** |

**When it was run matters and is disclosed here rather than glossed.** The check lives in
`scripts/cloud/gcp_a1_leakfree.sh`, which is meant to run it *before* spending a GPU-hour. The
relaunch after the 2026-08-08 driver failure called `run_e5_sigma_grounding.sh` directly and so
skipped it, and the certification above was therefore run **after** seeds 42–44 had finished. It
passes, and the stream is the same file by hash — but the guarantee the gate was designed to give,
that no GPU time is spent on an uncertified stream, was not given for those three seeds. The 45/46
launch runs it first.

## Three-seed contrast

Both arms, same schedule, intersection-locked to the same n = 5608 labelled test rows.

| arm | MAE | R² | per-seed MAE |
|---|---|---|---|
| ungrounded | 2.1241 ± 0.0441 | +0.124 ± 0.035 | 2.0816 / 2.1060 / 2.1849 |
| grounded_a | **1.8908 ± 0.0052** | +0.307 ± 0.019 | 1.8961 / 1.8926 / 1.8838 |

Per-seed gain **0.2333 ± 0.0493** (0.1855 / 0.2134 / 0.3011), one sign at all three seeds, and the
two arms do not overlap per seed: the worst grounded run (1.8961) beats the best ungrounded one
(2.0816).

Against the published, leak-uncertified 2.043 ± 0.040 → 1.846 ± 0.053, gain 0.198: the leak-free
gain is **larger**, same sign, same non-overlap. On these three seeds the leak was not producing the
gain.

## A correction to this file's own first version

The three ± above were first recorded as 0.0540 / 0.0063 / 0.0603. Those are **sample** standard
deviations; every ± that spans seeds in this paper is a **population** one, stated at
`sections/SI.tex` and again in Table S3's caption, and a sample figure is larger by exactly
√(3/2) = 1.2247. The means, the signs and the per-seed non-overlap are unaffected. The wrong figures
also stand in the commit message of `4d52fc4`, which is not rewritten; this note is the correction of
record. They are the numbers an executor would have typed into five displays, and the discharge
sheet's own final check would not have caught them — it greps *retired* values, not new ones.

## Two things in these files that must not be read as findings

**`comparison.json` in each seed directory carries ONE arm, not two.** The arms ran as separate
processes and each called the aggregator on completion, so the later one overwrote the file with
only itself. The cross-arm numbers above come from `comparison_both_arms.json`, recomputed from the
six prediction CSVs. Do not quote `comparison.json`.

**`rescue` is vacuous in these files.** The criterion compares each arm's R² against the
`--direct-label` arm's, and this run has no `directgnn` arm; the recomputation passed
`--direct-label ungrounded`, so `rescue: true` says only that each arm's R² is at least the
ungrounded arm's — trivially true of the ungrounded arm itself. The criterion is not evaluated here.
(`run_e5_comparison.py` now writes `null` plus a reason where a criterion cannot be evaluated; the
copy on the VM was patched mid-gate, so the per-arm `comparison.json` files written earlier still
say `false` where they mean "not tested".)

**`n_acyclic` is 0 and the `acyclic` stratum is empty**, here and in the published run: all 2634
unique test solutes bear a ring. The ring/acyclic split prints as though it were informative and is
not. No claim in the manuscript reads off it.
