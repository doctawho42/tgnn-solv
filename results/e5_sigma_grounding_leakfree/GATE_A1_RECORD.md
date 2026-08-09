# Gate A1, the leak-free re-run: interim record at three of five seeds

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
| ungrounded | 2.1241 ± 0.0540 | +0.124 ± 0.043 | 2.0816 / 2.1060 / 2.1849 |
| grounded_a | **1.8908 ± 0.0063** | +0.307 ± 0.023 | 1.8961 / 1.8926 / 1.8838 |

Per-seed gain **0.2333 ± 0.0603** (0.1855 / 0.2134 / 0.3011), one sign at all three seeds, and the
two arms do not overlap per seed: the worst grounded run (1.8961) beats the best ungrounded one
(2.0816).

Against the published, leak-uncertified 2.043 ± 0.040 → 1.846 ± 0.053, gain 0.198: the leak-free
gain is **larger**, same sign, same non-overlap. On these three seeds the leak was not producing the
gain.

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
