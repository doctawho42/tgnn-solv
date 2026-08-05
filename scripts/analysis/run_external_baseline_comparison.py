#!/usr/bin/env python3
r"""Assemble the external-baseline comparison: this work's absolute solubility
accuracy set against published solid-solubility models, on comparable tasks where
they are comparable and marked where they are not.

WHY THIS EXISTS
---------------
The article reports the physics arm and its control as a difference (+0.14 MAE).
It never states what those models are worth in absolute terms against the
published state of the art, so a reader cannot judge whether the closure error the
paper decomposes belongs to a competent solubility model or to a weak one.  This
script builds one table with three tiers, each labelled with what it can and
cannot be compared to.

  TIER 1  this work, scaffold split (solute_scaffold, held-out Bemis-Murcko
          scaffolds of the BigSolDB-derived corpus), three seeds, from the
          committed per-row predictions in results/e5_sigma_grounding/seed_*/.
          Reported in ln x2 (the native target) and in log10 S (mol/L) through
          tgnn_solv.external_benchmarking.logS_from_ln_x2 -- the same converter the
          deposited external-baseline runs used, so the unit matches the published
          literature even though the split does not.

  TIER 2  FastSolv and SolProp as re-run in this work on this corpus, read from the
          committed benchmark bundles in results/external_baselines/.  These are on
          a BY-SOLUTE split (test_solute.csv), not the scaffold split, so they bound
          the task's difficulty on this corpus and do not rank against Tier 1.

  TIER 3  the same two model families AS PUBLISHED, on their own test sets and in
          their own units.  Different corpora, different splits, log10 S in mol/L.
          Quoted verbatim with citation; comparable to nothing else in the table
          except in order of magnitude.

Also emitted: a predict-the-mean reference on this work's own test rows, so the
ln x2 numbers have an assumption-free scale, and the two inter-laboratory noise
estimates (this work's and FastSolv's) which are computed on different bases and
must not be pooled.

THE COMPARISON THIS TABLE MUST NOT FLATTER
------------------------------------------
On the scaffold split the physics arm trails its own direct control (1.85 vs 1.70
MAE in ln x2).  That ordering is in the table and is not annotated away.

Nor may the exclusions differ by arm.  The log10 S column runs on the rows whose
TRUE value converts -- the solvent has a molarity -- which is the same 5440 rows
for every arm and seed, and predictions are clipped at x2 = 0.999999 before
conversion so that an arm which saturates keeps its row with a large finite error.
An earlier version of this script converted predictions unclipped and let _metrics
drop the resulting +inf rows; that dropped 12-195 rows per arm per seed, all of
them each arm's worst predictions, and none at all from the DirectGNN control,
which never saturates.  It lowered the sigma-oracle arm by 0.21 log10 S, the
COSMO-SAC-grounded arm by 0.31, the NRTL arm by 0.48, and the control by nothing;
`defect_unclipped_arm_dependent' in the emitted summary carries all four.  Both n
values are now printed for every row.

Three further things this table must not do.  It must not print a bare mean under
a header promising a spread, so every tier-1 cell carries the population s.d. over
seeds and every one of them is a mean of per-seed metrics, never a pooled figure.
It must not hide that the log10 S column is a function of the clip constant, so
`clip_sensitivity' sweeps x2 over 1-1e-3 .. 1-1e-10 and records which readings
survive the sweep and which do not.  And it must not leave the assumption-free
reference out of the column the paper uses to place itself, so the predict-the-mean
row is now scored in log10 S on the same 5440 rows -- where it beats all three
physics arms.

REPRODUCE
---------
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/run_external_baseline_comparison.py

Writes results/external_baseline_comparison/{summary.json, table_rows.csv,
table_article.tex, parity_rows_seed42.csv}.  Edits no .tex in paper/.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from tgnn_solv.external_benchmarking import (  # noqa: E402
    MAX_FINITE_LN_X2_FOR_LOGS,
    clip_ln_x2_for_logS,
    logS_from_ln_x2,
)

E5 = REPO / "results/e5_sigma_grounding"
EXT = REPO / "results/external_baselines"
OUT = REPO / "results/external_baseline_comparison"
SEEDS = (42, 43, 44)

# Arms drawn into the article table, with the label the paper uses for each.
ARMS = {
    "grounded_a": "TGNN, COSMO-SAC closure, sigma head supervised (physics arm)",
    "nrtl": "TGNN, NRTL closure (physics arm)",
    "directgnn": "DirectGNN (same encoder, no closure) -- the control",
    "oracle": "TGNN, COSMO-SAC with the reference sigma substituted at evaluation",
}
# The order block 1 is printed in: the control first, then the two physics arms it
# leads, then the oracle swap.  This is the order the article's table prints, and it
# lives here so that the article's copy is a transcription and not a re-ordering.
ARTICLE_ROW_ORDER = ("directgnn", "nrtl", "grounded_a", "oracle")

# The saturation clip actually used (the repo's standing constant), and the span the
# sensitivity sweeps it over: three decades tighter and four looser.  1 - 1e-3 is about
# as tight as a mole fraction can be clipped and still be a mole fraction; past 1 - 1e-10
# the conversion is running out of double precision in ln x2.
MAX_X2_USED = 1.0 - 1e-6
CLIP_SWEEP = (1.0 - 1e-3, 1.0 - 1e-4, 1.0 - 1e-5, MAX_X2_USED,
              1.0 - 1e-7, 1.0 - 1e-8, 1.0 - 1e-10)

# --------------------------------------------------------------------------- #
# TIER 3: published numbers, quoted.  Every value here is a literature quantity;
# nothing in this block is computed by this repository.
# --------------------------------------------------------------------------- #
PUBLISHED = [
    {
        "model": "fastsolv (solution-FASTPROP ensemble)",
        "source": "Attia, Burns, Doyle & Green, Nat. Commun. 2025, 16, 7497",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "osanloo2024",
        "bibcmd": r"\cite{osanloo2024}",
        "test_set": "SolProp test set (solutes disjoint from the training corpus)",
        "task": "new-solute extrapolation, variable T",
        "metric_space": "log10 S (mol/L)",
        "rmse": 0.83, "mae": None, "extra": "%logS+-1 = 78.1%",
    },
    {
        "model": "solution-CHEMPROP (companion model)",
        "source": "Attia, Burns, Doyle & Green, Nat. Commun. 2025, 16, 7497",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "osanloo2024",
        "bibcmd": r"\cite{osanloo2024}",
        "test_set": "SolProp test set",
        "task": "new-solute extrapolation, variable T",
        "metric_space": "log10 S (mol/L)",
        "rmse": 0.83, "mae": None, "extra": "%logS+-1 = 76.1%",
    },
    {
        "model": "SolProp (Vermeire et al. thermodynamic cycle)",
        "source": "as evaluated in Attia et al. 2025; model from Vermeire, Chung & Green, J. Am. Chem. Soc. 2022, 144, 10785",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "vermeire2022solprop",
        "bibcmd": r"\cite{vermeire2022solprop}, scored in \cite{osanloo2024}",
        "test_set": "SolProp test set",
        "task": "new-solute extrapolation, variable T",
        "metric_space": "log10 S (mol/L)",
        "rmse": 1.43, "mae": None, "extra": "%logS+-1 = 66.9%",
    },
    {
        "model": "fastsolv (solution-FASTPROP ensemble)",
        "source": "Attia, Burns, Doyle & Green, Nat. Commun. 2025, 16, 7497",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "osanloo2024",
        "bibcmd": r"\cite{osanloo2024}",
        "test_set": "Leeds set (Boobier et al.), near room temperature",
        "task": "new-solute extrapolation, the more stringent of the two",
        "metric_space": "log10 S (mol/L)",
        "rmse": 0.95, "mae": None, "extra": "%logS+-1 = 73.8%",
    },
    {
        "model": "solution-CHEMPROP (companion model)",
        "source": "Attia, Burns, Doyle & Green, Nat. Commun. 2025, 16, 7497",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "osanloo2024",
        "bibcmd": r"\cite{osanloo2024}",
        "test_set": "Leeds set",
        "task": "new-solute extrapolation",
        "metric_space": "log10 S (mol/L)",
        "rmse": 0.99, "mae": None, "extra": "%logS+-1 = 70.9%",
    },
    {
        "model": "SolProp (Vermeire et al. thermodynamic cycle)",
        "source": "as evaluated in Attia et al. 2025",
        "doi": "10.1038/s41467-025-62717-7",
        "bibkey": "vermeire2022solprop",
        "bibcmd": r"\cite{vermeire2022solprop}, scored in \cite{osanloo2024}",
        "test_set": "Leeds set",
        "task": "new-solute extrapolation",
        "metric_space": "log10 S (mol/L)",
        "rmse": 2.16, "mae": None, "extra": "%logS+-1 = 41.2%",
    },
]

NOISE = {
    "this_work": {
        "statistic": "mean absolute inter-source disagreement on repeated (solute, solvent, T)",
        "value_ln_x2": [0.15, 0.31],
        "detail": "0.15 for pairs backed by two sources (n=3948 groups), 0.31 for three or more (n=349)",
        "source": "this work, on the BigSolDB-derived corpus",
    },
    "attia_2025": {
        "statistic": "inter-laboratory RMSE / standard deviation between duplicate solutions",
        "value_log10_S": {"rmse": 0.75, "sd": 0.34},
        "detail": "34 solutions, 8 solutes, 6 solvents; quoted as the aleatoric limit",
        "source": "Attia et al., Nat. Commun. 2025, 16, 7497",
    },
    "warning": (
        "the two are different statistics on different bases (mean absolute vs RMSE; "
        "ln mole fraction vs log10 mol/L) and must not be pooled or converted into "
        "one another"
    ),
}


# --------------------------------------------------------------------------- #
def _e5_module():
    spec = importlib.util.spec_from_file_location("e5_cmp", HERE / "run_e5_comparison.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["e5_cmp"] = mod
    spec.loader.exec_module(mod)
    return mod


_KEY = ["solute_smiles", "solvent_smiles", "T"]
# Arms that define the intersection lock.  `oracle` is deliberately NOT among them:
# results/e5_sigma_grounding/seed_44/oracle_predictions.csv holds 295 rows, not the
# 8103 every other arm/seed file holds, so locking on it would collapse seed 44 to
# n=295 and silently change every number.  See the `deposit_defects` block in the
# emitted summary.  Locking on the five intact arms reproduces the paper's per-seed
# MAEs exactly, because at every seed each arm's eligible row set is the same 5608.
LOCK_ARMS = ("nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b")
ALL_ARMS = LOCK_ARMS + ("oracle",)


def _locked_rows(seed: int, e5) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Per-arm prediction rows on the cross-arm intersection lock (the same lock
    run_e5_comparison.py uses for the paper's headline MAEs), keyed and aligned.

    Returns (locked frames indexed by key, names of arms dropped for short files).
    """
    frames, dropped = {}, []
    for arm in ALL_ARMS:
        p = E5 / f"seed_{seed}" / f"{arm}_predictions.csv"
        if p.exists():
            frames[arm] = pd.read_csv(p, low_memory=False)
    keys = e5.intersection_keys({a: frames[a] for a in LOCK_ARMS})
    locked = {}
    for arm, df in frames.items():
        d = df.copy()
        d["T"] = d["T"].round(6)
        d = d.drop_duplicates(_KEY, keep="first").set_index(_KEY)
        have = [k for k in keys if k in d.index]
        if len(have) < len(keys):
            dropped.append(f"{arm}@seed{seed}: covers {len(have)}/{len(keys)} locked rows")
            continue
        locked[arm] = d.loc[have].reset_index()
    return locked, dropped


def _metrics(true: np.ndarray, pred: np.ndarray, *, mask: np.ndarray | None = None) -> dict:
    """Metrics on the rows `mask` selects, or on the finite ones if no mask is given.

    A mask is passed whenever the row set must not depend on the arm being scored:
    dropping each arm's own non-finite predictions would make the exclusions
    arm-dependent, which is what `_common_logS_mask` exists to prevent.
    """
    true = np.asarray(true, float)
    pred = np.asarray(pred, float)
    ok = np.isfinite(true) & np.isfinite(pred) if mask is None else np.asarray(mask, bool)
    true, pred = true[ok], pred[ok]
    if true.size == 0:
        return {"n": 0}
    d = pred - true
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    return {
        "n": int(true.size),
        "mae": float(np.mean(np.abs(d))),
        "rmse": float(np.sqrt(np.mean(d ** 2))),
        "bias": float(np.mean(d)),
        "r2": float(1.0 - np.sum(d ** 2) / ss_tot) if ss_tot > 0 else float("nan"),
    }


def tier1() -> tuple[dict, pd.DataFrame]:
    """This work's arms on the scaffold split, in ln x2 and in log10 S (mol/L)."""
    e5 = _e5_module()
    per_seed: dict[str, dict[int, dict]] = {arm: {} for arm in ARMS}
    mean_ref: dict[int, dict] = {}
    mean_ref_log: dict[int, dict] = {}
    defect_seed: dict[str, dict[int, dict]] = {arm: {} for arm in ARMS}
    clip_seed: dict[float, dict[str, dict[int, float]]] = {
        c: {a: {} for a in ARMS} for c in CLIP_SWEEP}
    parity = None
    defects: list[str] = []
    for seed in SEEDS:
        locked, dropped = _locked_rows(seed, e5)
        defects.extend(dropped)
        # one logS conversion per seed, on the arm-independent (true) column and on
        # each arm's prediction; the converter needs solvent_smiles + an ln x2 column
        base = locked["directgnn"][[*_KEY, "ln_x2_true"]].copy()
        base["logS_true"] = logS_from_ln_x2(
            base.rename(columns={"ln_x2_true": "ln_x2"}), ln_x2_col="ln_x2")
        # The log10 S row set is fixed by the TRUE column alone -- the rows whose
        # solvent has a molarity, so logS_true exists -- and is therefore the same for
        # every arm and every metric in the block.  Predictions are clipped at
        # x2 = 0.999999 before conversion (clip_ln_x2_for_logS, the repo's convention
        # for prediction-side conversions, used by every other benchmark script here),
        # so an arm that saturates at x2 = 1 keeps its row with a large finite error
        # instead of converting to +inf and being dropped.  Dropping them would remove
        # each arm's most catastrophic predictions, and only the arms that saturate:
        # an arm-dependent exclusion inside a comparison table.
        logS_true = base["logS_true"].to_numpy(float)
        common = np.isfinite(logS_true)
        for arm in ARMS:
            if arm not in locked:
                continue
            d = locked[arm]
            m_ln = _metrics(d["ln_x2_true"], d["ln_x2_pred"])
            tmp = d[["solvent_smiles", "ln_x2_pred"]].rename(columns={"ln_x2_pred": "ln_x2"})
            tmp["ln_x2"] = clip_ln_x2_for_logS(tmp["ln_x2"].to_numpy(float))
            logS_pred = logS_from_ln_x2(tmp, ln_x2_col="ln_x2").to_numpy(float)
            n_saturated = int(np.sum(
                (d["ln_x2_pred"].to_numpy(float) > MAX_FINITE_LN_X2_FOR_LOGS) & common))
            if not np.all(np.isfinite(logS_pred[common])):
                defects.append(
                    f"{arm}@seed{seed}: non-finite logS prediction survives clipping")
            m_log = _metrics(logS_true, logS_pred, mask=common)
            m_log["n_saturated_kept_by_clipping"] = n_saturated
            per_seed[arm][seed] = {"ln_x2": m_ln, "logS": m_log}

            # (a) what the repaired defect was worth, per arm: convert UNCLIPPED and
            # let each arm's own +inf rows drop, which is what the earlier version did.
            tmp["ln_x2"] = d["ln_x2_pred"].to_numpy(float)
            raw = logS_from_ln_x2(tmp, ln_x2_col="ln_x2").to_numpy(float)
            ok = common & np.isfinite(raw)
            m_def = _metrics(logS_true, raw, mask=ok)
            m_def["n_dropped_by_the_defect"] = int(common.sum() - ok.sum())
            defect_seed[arm][seed] = m_def

            # (b) the clip is a chosen constant; record what the column reads at others
            for c in CLIP_SWEEP:
                tmp["ln_x2"] = np.minimum(d["ln_x2_pred"].to_numpy(float), np.log(c))
                swept = logS_from_ln_x2(tmp, ln_x2_col="ln_x2").to_numpy(float)
                clip_seed[c][arm][seed] = _metrics(logS_true, swept, mask=common)["rmse"]
        # predict-the-test-mean reference (assumption-free scale for ln x2)
        t = locked["directgnn"]["ln_x2_true"].to_numpy(float)
        mean_ref[seed] = _metrics(t, np.full_like(t, t.mean()))
        # ...and the same constant prediction carried through the same unit bridge, so
        # the log10 S column has a within-block reference too.  The 5440-row mask is
        # arm-independent, so nothing stops this being computed; leaving it out left
        # 1.39-1.57 with no upper reference in the one column the paper is placed in.
        cst = locked["directgnn"][["solvent_smiles"]].copy()
        cst["ln_x2"] = np.full(len(cst), float(t.mean()))
        logS_null = logS_from_ln_x2(cst, ln_x2_col="ln_x2").to_numpy(float)
        m_null = _metrics(logS_true, logS_null, mask=common)
        # the stricter variant: predict the mean of the TRUE log10 S on those rows
        m_null["rmse_predicting_mean_of_true_logS"] = float(np.sqrt(np.mean(
            (logS_true[common] - logS_true[common].mean()) ** 2)))
        mean_ref_log[seed] = m_null
        if seed == 42:
            parity = base.copy()
            for arm in ARMS:
                if arm in locked:
                    parity[f"pred_{arm}"] = locked[arm]["ln_x2_pred"].to_numpy(float)

    out = {}
    for arm, label in ARMS.items():
        seeds_ok = sorted(per_seed[arm])

        def agg(space: str, key: str, arm=arm, seeds_ok=seeds_ok):
            vals = [per_seed[arm][s][space][key] for s in seeds_ok]
            return float(np.mean(vals)), float(np.std(vals))  # ddof=0, as the paper uses

        out[arm] = {
            "label": label,
            "n": per_seed[arm][seeds_ok[0]]["ln_x2"]["n"],
            "n_logS": per_seed[arm][seeds_ok[0]]["logS"]["n"],
            "seeds": seeds_ok,
            "ln_x2": {k: {"mean": agg("ln_x2", k)[0], "sd": agg("ln_x2", k)[1],
                          "per_seed": {s: per_seed[arm][s]["ln_x2"][k] for s in seeds_ok}}
                      for k in ("mae", "rmse", "r2")},
            "logS_mol_per_L": {k: {"mean": agg("logS", k)[0], "sd": agg("logS", k)[1]}
                               for k in ("mae", "rmse", "r2")},
            "logS_rows_saturated_at_x2_eq_1": {
                s: per_seed[arm][s]["logS"]["n_saturated_kept_by_clipping"] for s in seeds_ok
            },
        }
    out["_predict_the_mean_reference"] = {
        "label": "predict the test-set mean of ln x2 (assumption-free scale)",
        "mae_ln_x2": float(np.mean([mean_ref[s]["mae"] for s in SEEDS])),
        "rmse_ln_x2": float(np.mean([mean_ref[s]["rmse"] for s in SEEDS])),
        "n": mean_ref[SEEDS[0]]["n"],
        # the same constant prediction in log10 S, on the arm-independent 5440 rows.
        # It does not saturate, so it does not move with the clip.
        "n_logS": mean_ref_log[SEEDS[0]]["n"],
        "mae_logS": float(np.mean([mean_ref_log[s]["mae"] for s in SEEDS])),
        "rmse_logS": float(np.mean([mean_ref_log[s]["rmse"] for s in SEEDS])),
        "r2_logS": float(np.mean([mean_ref_log[s]["r2"] for s in SEEDS])),
        "rmse_logS_predicting_mean_of_true_logS": float(np.mean(
            [mean_ref_log[s]["rmse_predicting_mean_of_true_logS"] for s in SEEDS])),
        "note": (
            "The log10 S figure converts the same constant ln x2 prediction through the "
            "same unit bridge as every arm above it, on the same 5440 rows. It is BELOW "
            "all three physics arms (1.39, 1.54, 1.57) and above the DirectGNN control "
            "(1.00): predicting one number for the whole test set beats every physics arm "
            "in the column this table is placed against published work in."
        ),
    }
    out["_defect_unclipped_arm_dependent"] = {
        "what": (
            "the repaired defect, per arm: convert predictions UNCLIPPED and let each "
            "arm's own +inf rows drop. The row set then depends on the arm."
        ),
        "per_arm": {
            arm: {
                "rmse_logS_mean": float(np.mean(
                    [defect_seed[arm][s]["rmse"] for s in sorted(defect_seed[arm])])),
                "rows_dropped_per_seed": {
                    s: defect_seed[arm][s]["n_dropped_by_the_defect"]
                    for s in sorted(defect_seed[arm])},
            }
            for arm in ARMS if defect_seed[arm]
        },
    }
    for arm, blk in out["_defect_unclipped_arm_dependent"]["per_arm"].items():
        blk["repaired_minus_defect"] = float(
            out[arm]["logS_mol_per_L"]["rmse"]["mean"] - blk["rmse_logS_mean"])
    out["_clip_sensitivity"] = {
        "what": (
            "RMSE log10 S as a function of the saturation clip. The control never "
            "saturates and does not move; the physics arms do. Read as: the ordering "
            "claims that survive the sweep are usable, the ones that do not are not."
        ),
        "clip_used": float(MAX_X2_USED),
        "by_clip": {
            f"{c:.12g}": {
                arm: float(np.mean([clip_seed[c][arm][s] for s in sorted(clip_seed[c][arm])]))
                for arm in ARMS if clip_seed[c][arm]
            }
            for c in CLIP_SWEEP
        },
        "by_clip_per_seed": {
            f"{c:.12g}": {
                arm: {str(s): float(clip_seed[c][arm][s]) for s in sorted(clip_seed[c][arm])}
                for arm in ARMS if clip_seed[c][arm]
            }
            for c in CLIP_SWEEP
        },
    }
    # Is each physics arm's deficit against the control LARGER in log10 S than in MAE?
    # The article states this reading of two arms only; this block is where that
    # restriction is checked.  Positive = the arm trails by more in log10 S.  Both the
    # seed-averaged and the per-seed forms are recorded, because the reading survives the
    # sweep for two arms at every seed and fails for the third at some clips at both.
    ctl = "directgnn"
    mae_mean = {a: float(np.mean([per_seed[a][s]["ln_x2"]["mae"] for s in sorted(per_seed[a])]))
                for a in ARMS if per_seed[a]}
    excess_mean, excess_seed = {}, {}
    for a in ARMS:
        if a == ctl or not per_seed[a]:
            continue
        dm = mae_mean[a] - mae_mean[ctl]
        excess_mean[a] = {
            f"{c:.12g}": float(
                np.mean([clip_seed[c][a][s] for s in sorted(clip_seed[c][a])])
                - np.mean([clip_seed[c][ctl][s] for s in sorted(clip_seed[c][ctl])]) - dm)
            for c in CLIP_SWEEP}
        excess_seed[a] = {}
        for s in sorted(per_seed[a]):
            dms = per_seed[a][s]["ln_x2"]["mae"] - per_seed[ctl][s]["ln_x2"]["mae"]
            excess_seed[a][str(s)] = {
                f"{c:.12g}": float(clip_seed[c][a][s] - clip_seed[c][ctl][s] - dms)
                for c in CLIP_SWEEP}
    out["_trails_control_by_more_in_logS_than_in_MAE"] = {
        "what": (
            "(RMSE log10 S of the arm - of the control) - (MAE ln x2 of the arm - of the "
            "control), per clip. Positive means the arm trails its control by MORE in the "
            "log10 S column than in MAE. It is positive for nrtl and grounded_a at every "
            "clip and at every seed; for the oracle it is NEGATIVE at the three tightest "
            "clips in the seed average, at all seven clips at seed 42, and at the two "
            "tightest at seed 43. Note the functionals differ (RMSE against MAE)."
        ),
        "seed_averaged": excess_mean,
        "per_seed": excess_seed,
    }
    out["_deposit_defects"] = defects
    return out, parity


def tier2() -> dict:
    """External models re-run in this work, read from the committed bundles."""
    rows = {}
    specs = [
        ("fastsolv_retrained_here", "solute/fastsolv_contract_v2/summary.csv", "fastsolv", None),
        ("solprop_cycle_recalibrated", "solute/solprop_calibrated_contract_v2/summary.csv",
         "solprop_calibrated", None),
        ("solprop_cycle_zero_shot", "solute/solprop_calibrated_contract_v2/summary.csv",
         "solprop_zero_shot", None),
        ("solprop_encoder_retrained_no_cycle", "solute/solprop_native_contract_v2/summary.csv",
         None, "native"),
        ("fastsolv_retrained_here_pair_random", "pair_random/fastsolv_contract_v2/summary.csv",
         "fastsolv", None),
        ("solprop_encoder_retrained_no_cycle_pair_random",
         "pair_random/solprop_native_contract_v2/summary.csv", None, "native"),
    ]
    for name, rel, model, kind in specs:
        p = EXT / rel
        if not p.exists():
            continue
        d = pd.read_csv(p)
        d = d[d["split"] == "test"] if "split" in d.columns else d
        if model is not None:
            d = d[d["model"] == model]
        if len(d) == 0:
            continue
        r = d.iloc[0]
        if kind == "native":
            rows[name] = {
                "n": int(r["n_samples"]),
                "ln_x2": {"mae": float(r["mae"]), "rmse": float(r["rmse"]), "r2": float(r["r2"])},
                "logS_mol_per_L": {"mae": float(r["logS_mae_finite"]),
                                   "rmse": float(r["logS_rmse_finite"]),
                                   "r2": float(r["logS_r2_finite"]),
                                   "n": int(r["logS_n_samples_finite"])},
            }
        else:
            rows[name] = {
                "n": int(r["n_samples"]),
                "ln_x2": {"mae": float(r["mae"]), "rmse": float(r["rmse"]), "r2": float(r["r2"])},
                "logS_mol_per_L": {"mae": float(r["mae_logS_finite_subset"]),
                                   "rmse": float(r["rmse_logS_finite_subset"]),
                                   "r2": float(r["r2_logS_finite_subset"]),
                                   "n": int(r["n_samples_logS_finite_subset"])},
            }
        rows[name]["n_logS"] = int(rows[name]["logS_mol_per_L"]["n"])
        rows[name]["split"] = ("pair_random" if "pair_random" in rel else "by-solute")
        rows[name]["source_artifact"] = str(p.relative_to(REPO))
    return rows


# --------------------------------------------------------------------------- #
_TEX_ESCAPE = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$"}


def _tex(s: str) -> str:
    """Escape the alignment/comment characters that appear in these labels.

    `&` in an author list and `_` in a split name both break a tabular row, so
    every string that reaches the .tex goes through here.  Math is inserted after
    escaping, by the TEX_* tables below.
    """
    return "".join(_TEX_ESCAPE.get(c, c) for c in str(s))


TEX_MODEL = {
    "grounded_a": r"TGNN, COSMO-SAC closure, supervised $\hat\sigma$ (physics)",
    "nrtl": r"TGNN, NRTL closure (physics)",
    "directgnn": r"DirectGNN, same encoder, no closure \emph{(control)}",
    "oracle": r"TGNN, COSMO-SAC, reference $\sigma^\star$ substituted at evaluation",
}
TEX_SPLIT = {
    "solute scaffold (this corpus)": "solute scaffold, this corpus",
    "by-solute (this corpus)": "by-solute, this corpus",
    "pair_random (this corpus)": "random pair, this corpus",
}


def _fmt(v, nd=2):
    return "--" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{nd}f}"


def _int_or_none(v) -> int | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if np.isfinite(f) else None


def _fmt_n(n_ln, n_log) -> str:
    """The row's two sample sizes, printed as `n_lnx / n_logS`.

    Both are printed whenever they differ, because the two metric columns of this
    table are not computed on the same rows: the log10 S conversion needs a solvent
    molarity and drops the rows that have none.  A single n would describe only the
    MAE column and would silently mis-describe the RMSE one.
    """
    a, b = _int_or_none(n_ln), _int_or_none(n_log)
    if a is None and b is None:
        return "--"
    if a is None:
        return f"-- / {b}"
    if b is None:
        return f"{a} / --"
    return f"{a}" if a == b else f"{a} / {b}"


def article_table(t1: dict, t2: dict) -> pd.DataFrame:
    rows = []
    for arm in ARTICLE_ROW_ORDER:
        label = ARMS[arm]
        b = t1[arm]
        seeds = b["seeds"]
        rows.append({
            "tier": "this work",
            "model": label + ("" if len(seeds) == 3 else f" (seeds {seeds} only)"),
            "tex_model": TEX_MODEL[arm] + ("" if len(seeds) == 3
                                           else r" [seeds $42,43$ only\tnote{$\ast$}]"),
            "split": "solute scaffold (this corpus)",
            "n": b["n"],
            "n_logS": b["n_logS"],
            "mae_ln_x2": b["ln_x2"]["mae"]["mean"],
            "sd_mae_ln_x2": b["ln_x2"]["mae"]["sd"],
            "rmse_ln_x2": b["ln_x2"]["rmse"]["mean"],
            "mae_logS": b["logS_mol_per_L"]["mae"]["mean"],
            "rmse_logS": b["logS_mol_per_L"]["rmse"]["mean"],
            "sd_rmse_logS": b["logS_mol_per_L"]["rmse"]["sd"],
            "r2_ln_x2": b["ln_x2"]["r2"]["mean"],
            "sd_r2_ln_x2": b["ln_x2"]["r2"]["sd"],
            "comparable_to": "each other (three seeds, one locked row set)",
        })
    mr = t1["_predict_the_mean_reference"]
    rows.append({
        "tier": "reference", "model": mr["label"],
        "tex_model": r"predict the test-set mean of $\lnx$",
        "split": "solute scaffold (this corpus)",
        "n": mr["n"], "n_logS": mr["n_logS"],
        "mae_ln_x2": mr["mae_ln_x2"], "sd_mae_ln_x2": None,
        "rmse_ln_x2": mr["rmse_ln_x2"], "mae_logS": mr["mae_logS"],
        "rmse_logS": mr["rmse_logS"], "sd_rmse_logS": None,
        "r2_ln_x2": 0.0, "sd_r2_ln_x2": None,
        "comparable_to": "the rows above; fixes the scale of ln x2 and of log10 S",
    })
    label2 = {
        "fastsolv_retrained_here": "FastSolv, retrained on this corpus",
        "solprop_cycle_recalibrated": "SolProp cycle, released model + 3-parameter recalibration",
        "solprop_cycle_zero_shot": "SolProp cycle, released model, zero-shot",
        "solprop_encoder_retrained_no_cycle": "SolProp encoder retrained on ln x2, cycle discarded",
        "fastsolv_retrained_here_pair_random": "FastSolv, retrained on this corpus",
        "solprop_encoder_retrained_no_cycle_pair_random":
            "SolProp encoder retrained on ln x2, cycle discarded",
    }
    for name, b in t2.items():
        rows.append({
            "tier": "external, re-run here",
            "model": label2.get(name, name),
            "tex_model": _tex(label2.get(name, name)).replace("ln x2", r"$\lnx$"),
            "split": f"{b['split']} (this corpus)",
            "n": b["n"],
            "n_logS": b["n_logS"],
            "mae_ln_x2": b["ln_x2"]["mae"], "sd_mae_ln_x2": None,
            "rmse_ln_x2": b["ln_x2"]["rmse"],
            "mae_logS": b["logS_mol_per_L"]["mae"], "rmse_logS": b["logS_mol_per_L"]["rmse"],
            "sd_rmse_logS": None,
            "r2_ln_x2": b["ln_x2"]["r2"], "sd_r2_ln_x2": None,
            "comparable_to": "each other; NOT to the scaffold rows (different split); ONE RUN",
        })
    for b in PUBLISHED:
        rows.append({
            "tier": "external, as published",
            "model": f"{b['model']} [{b['source']}]",
            "tex_model": _tex(b["model"]) + " " + b["bibcmd"],
            "split": b["test_set"],
            "n": None, "n_logS": None,
            "mae_ln_x2": None, "sd_mae_ln_x2": None, "rmse_ln_x2": None,
            "mae_logS": b["mae"], "rmse_logS": b["rmse"], "sd_rmse_logS": None,
            "r2_ln_x2": None, "sd_r2_ln_x2": None,
            "comparable_to": "nothing else in this table: different corpus, split and unit",
        })
    return pd.DataFrame(rows)


def latex_table(df: pd.DataFrame) -> str:
    lines = [
        "% Auto-generated by scripts/analysis/run_external_baseline_comparison.py.",
        "% Do not hand-edit: re-run the script.",
        r"\begin{tabular}{@{}llrrrr@{}}",
        r"\toprule",
        r"Model & Test set & $n$ ($\lnx$ / $\log_{10}S$) & MAE $\lnx$ & RMSE $\log_{10}S$"
        r" & $R^2$ $\lnx$ \\",
        r"\midrule",
    ]
    tier_head = {
        "this work": r"\multicolumn{6}{@{}l}{\emph{This work, scaffold split; mean $\pm$ s.d. over seeds, three unless the row says otherwise}}\\",
        "reference": r"\multicolumn{6}{@{}l}{\emph{Scale reference on the same rows}}\\",
        "external, re-run here": r"\multicolumn{6}{@{}l}{\emph{External models re-run on this corpus, by-solute split, one run each---not comparable to the block above}}\\",
        "external, as published": r"\multicolumn{6}{@{}l}{\emph{As published, on their own corpora and splits, $\log_{10}S$ in mol\,L$^{-1}$}}\\",
    }

    def _pm(value, sd) -> str:
        """A cell, with its seed spread beside it whenever there is one.

        A bare mean under a header that promises a spread is how a three-seed cell
        that rests on one low seed reads as a settled number; every tier-1 cell here
        is a mean of per-seed metrics and carries its population s.d.
        """
        cell = _fmt(value)
        if sd is not None and np.isfinite(sd if sd is not None else np.nan):
            cell = f"{cell} $\\pm$ {sd:.2f}"
        return cell

    seen = set()
    for _, r in df.iterrows():
        if r["tier"] not in seen:
            seen.add(r["tier"])
            lines.append(tier_head[r["tier"]])
        split = TEX_SPLIT.get(r["split"], _tex(r["split"]))
        lines.append(
            f"{r['tex_model']} & {split} & {_fmt_n(r['n'], r['n_logS'])} & "
            f"{_pm(r['mae_ln_x2'], r['sd_mae_ln_x2'])} & "
            f"{_pm(r['rmse_logS'], r['sd_rmse_logS'])} & "
            f"{_pm(r['r2_ln_x2'], r['sd_r2_ln_x2'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t1, parity = tier1()
    t2 = tier2()
    df = article_table(t1, t2)

    summary = {
        "what": "absolute solubility accuracy of this work against published models",
        "tier1_this_work_scaffold_split": t1,
        "tier2_external_rerun_here": t2,
        "tier3_published": PUBLISHED,
        "noise_estimates": NOISE,
        "deposit_defects": {
            "found": t1["_deposit_defects"],
            "detail": (
                "results/e5_sigma_grounding/seed_44/oracle_predictions.csv holds 295 rows "
                "where every other arm/seed file holds 8103, so the sigma-oracle arm cannot "
                "be recomputed at seed 44 from the committed artifacts. The committed "
                "seed_44/comparison.json records oracle MAE 2.242 on n=5608, i.e. it was "
                "produced from a longer file that is no longer deposited. The three-seed "
                "oracle bar of the paper's Fig. 2 therefore does not reproduce from the "
                "deposit; the other five arms do, exactly."
            ),
        },
        "comparability": {
            "tier1_vs_tier2": (
                "NOT like-for-like: tier 1 is the solute-scaffold split, tier 2 the "
                "by-solute split of the same corpus. A by-solute split is easier; the "
                "tier-2 numbers bound the task's difficulty on this corpus and do not "
                "rank the models against tier 1."
            ),
            "tier1_vs_tier3": (
                "NOT like-for-like on three axes: corpus (this corpus vs the SolProp and "
                "Leeds sets), split, and metric base (ln mole fraction here; log10 S in "
                "mol/L there). The log10 S column is computed here through the same "
                "converter the tier-2 runs used, so the UNIT matches; the task does not."
            ),
            "within_tier1": (
                "like-for-like: one locked row set (n as reported), three seeds, the same "
                "encoder. In MAE ln x2 the physics arms trail the direct control in the "
                "SEED MEAN; per seed, the COSMO-SAC arms trail it at every seed and the "
                "NRTL arm at two of three, being ahead at seed 42 (1.7335 against 1.7485). "
                "One of the fourteen arm x seed cells beats the control."
            ),
            "logS_row_set": (
                "The log10 S column of tier 1 is computed on the rows where the TRUE value "
                "converts, i.e. where the solvent has a molarity: the same rows for every "
                "arm and every seed, 5440 of the 5608 locked rows. Predictions are clipped "
                "at x2 = 0.999999 (clip_ln_x2_for_logS) before conversion, so an arm that "
                "saturates at x2 = 1 keeps its row with a large finite error. Without the "
                "clip those rows convert to +inf and are dropped, which removes each arm's "
                "most catastrophic predictions and only from the arms that saturate -- an "
                "arm-dependent exclusion, and one that flatters the physics arms, whose "
                "log10 S RMSE it lowers by 0.21 (sigma-oracle), 0.31 (COSMO-SAC-grounded) "
                "and 0.48 (NRTL) while leaving the DirectGNN control, which never "
                "saturates, untouched -- see `_defect_unclipped_arm_dependent'. Tier 2's "
                "two n values come from the deposited bundles and are printed for the "
                "same reason."
            ),
            "logS_column_depends_on_the_clip": (
                "The clip is a chosen constant and three of the four tier-1 cells in the "
                "log10 S column are a function of it: see `_clip_sensitivity'. Over "
                "x2 = 1-1e-3 .. 1-1e-10 the control does not move at all while the physics "
                "arms move by 0.6-0.85. TWO readings survive the whole span, and separately "
                "at each seed for the arms that seed deposits: the control is below every "
                "physics arm; every physics arm is above every published leader. FOUR do "
                "not, and each of the four fails on the SEED axis as well as the clip one. "
                "(1) The NRTL and sigma-oracle rows exchange places just past the value "
                "used in the seed-averaged sweep, two clips earlier at seed 42, and not at "
                "all at seed 43, where NRTL is the lower at all seven. (2) The "
                "predict-the-mean reference does not saturate and so does not move with the "
                "clip -- it reads 1.3255 at every clip and at every seed, the locked row "
                "set being the same 5440 rows at all three -- and the physics arms are "
                "under it in 15 of the 56 arm x seed x clip cells: seed-averaged, the "
                "COSMO-SAC-grounded arm at the three tightest clips and NRTL at the two "
                "tightest; per seed, grounded at all seven clips at seed 42 (at the "
                "DEPOSITED clip 1.1254 against 1.3255, the one cell of the printed column "
                "that beats the reference), at the tightest at seed 43 and at the two "
                "tightest at seed 44; NRTL at the tightest at seed 42 and at the two "
                "tightest at seeds 43 and 44; the sigma-oracle at no clip and no seed. So "
                "the reading is a property of the seed-mean column at the deposited clip, "
                "not of the models. In MAE ln x2 every arm including the sigma-oracle is "
                "below the same reference (2.3249) at every seed. (3) At the tightest clip "
                "the NRTL and grounded arms read below 1.43, the better end of the "
                "published physics-informed cycle, at every seed, and the sigma-oracle's "
                "seed mean (1.4232) does too though not its seed-43 value (1.4793). (4) The "
                "physics arms do not uniformly trail the control by more in this column "
                "than in MAE (an RMSE deficit against an MAE one): the NRTL and "
                "COSMO-SAC-grounded arms do at every clip and at each seed, but the "
                "sigma-oracle's seed-averaged log10 S deficit runs 0.428/0.469/0.517/0.571/"
                "0.631/0.695/0.835 across the sweep against an MAE deficit of 0.554, so it "
                "fails at the three tightest clips and holds at the deposited one by 0.017; "
                "per seed it fails at all seven clips at seed 42 and at the two tightest at "
                "seed 43. A FIFTH reading fails on the seed axis alone and "
                "neither the article nor its SI carries it: the COSMO-SAC-grounded arm is "
                "the lowest of the three physics arms at every clip in the seed-averaged "
                "sweep, but at seed 43 the NRTL arm is lower at all seven, so that ordering "
                "is a property of the seed-mean column and not of the models. This block is "
                "the same inventory the article's Table 5 footnote a and its SI print; "
                "`_clip_sensitivity' (by_clip, by_clip_per_seed) and "
                "`_trails_control_by_more_in_logS_than_in_MAE' carry the numbers."
            ),
            "fastsolv_rows_are_defective": (
                "DEFECT, disclosed in the article's Table 5 footnote b and its SI. The two "
                "FastSolv rows are read from bundles whose prediction path standardises the "
                "model's inputs TWICE: scripts/run_fastsolv.py::_predict_with_model scales "
                "solute, solvent and temperature with the checkpoint's own buffers and then "
                "calls trainer.predict, whose fastsolv._classes._fastsolv.predict_step "
                "scales the same tensors again. The network's sigmoid input activation then "
                "saturates on the twice-scaled temperature (it arrives at about -19.3 "
                "instead of about -1.5, sigmoid ~ 4e-9), and the deposited predictions are "
                "EXACTLY constant in temperature for all 1102 by-solute and 1149 "
                "random-pair (solute, solvent) pairs spanning more than 5 K, where the "
                "measurements move a median 0.62 log10 S over a median 40 K. Training and "
                "validation steps do not re-scale, so the fitted model is not at fault: "
                "forwarding the same checkpoint on singly-scaled inputs restores a "
                "temperature response (span 0.135 against a measured 0.179 on a sample "
                "pair) and tracks the deposit far worse (Pearson 0.85) than the "
                "doubly-scaled path does (0.99). Both FastSolv rows are therefore a FLOOR "
                "on that model, not a rendering of it, and the by-solute/random-pair "
                "contrast in those rows is a symptom and not a measurement of the split. "
                "The SolProp rows use a different path and do carry a temperature response "
                "(median predicted span 1.31 ln x2 against a measured 1.35)."
            ),
            "hyperparameter_confound": (
                "the physics and control arms were tuned separately, so the tier-1 gap is "
                "not attributable to the bottleneck; the article states this."
            ),
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    df.to_csv(out / "table_rows.csv", index=False)
    (out / "table_article.tex").write_text(latex_table(df))
    if parity is not None:
        parity.to_csv(out / "parity_rows_seed42.csv", index=False)

    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(df[["tier", "model", "split", "n", "n_logS", "mae_ln_x2", "rmse_logS",
                  "r2_ln_x2"]].to_string(index=False))
    print("\nWhat the arm-dependent exclusion was worth, per arm (repaired - defect):")
    for arm, blk in t1["_defect_unclipped_arm_dependent"]["per_arm"].items():
        print(f"  {arm:11s} {blk['rmse_logS_mean']:.4f} -> "
              f"{t1[arm]['logS_mol_per_L']['rmse']['mean']:.4f}  "
              f"(+{blk['repaired_minus_defect']:.4f}; dropped "
              f"{list(blk['rows_dropped_per_seed'].values())})")
    print("\nRMSE log10 S against the saturation clip:")
    for c, blk in t1["_clip_sensitivity"]["by_clip"].items():
        print(f"  x2<= {c:<14s} " + "  ".join(f"{a}={v:.3f}" for a, v in blk.items()))
    mr = t1["_predict_the_mean_reference"]
    print(f"\npredict-the-mean reference: MAE ln x2 {mr['mae_ln_x2']:.4f}, "
          f"RMSE log10 S {mr['rmse_logS']:.4f} on n={mr['n_logS']} "
          f"(mean of the true log10 S instead: "
          f"{mr['rmse_logS_predicting_mean_of_true_logS']:.4f})")


if __name__ == "__main__":
    main()
