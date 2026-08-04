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

from tgnn_solv.external_benchmarking import logS_from_ln_x2  # noqa: E402

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


def _metrics(true: np.ndarray, pred: np.ndarray) -> dict:
    true = np.asarray(true, float)
    pred = np.asarray(pred, float)
    ok = np.isfinite(true) & np.isfinite(pred)
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
        for arm in ARMS:
            if arm not in locked:
                continue
            d = locked[arm]
            m_ln = _metrics(d["ln_x2_true"], d["ln_x2_pred"])
            tmp = d[["solvent_smiles", "ln_x2_pred"]].rename(columns={"ln_x2_pred": "ln_x2"})
            logS_pred = logS_from_ln_x2(tmp, ln_x2_col="ln_x2").to_numpy(float)
            m_log = _metrics(base["logS_true"].to_numpy(float), logS_pred)
            per_seed[arm][seed] = {"ln_x2": m_ln, "logS": m_log}
        # predict-the-test-mean reference (assumption-free scale for ln x2)
        t = locked["directgnn"]["ln_x2_true"].to_numpy(float)
        mean_ref[seed] = _metrics(t, np.full_like(t, t.mean()))
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
            "seeds": seeds_ok,
            "ln_x2": {k: {"mean": agg("ln_x2", k)[0], "sd": agg("ln_x2", k)[1],
                          "per_seed": {s: per_seed[arm][s]["ln_x2"][k] for s in seeds_ok}}
                      for k in ("mae", "rmse", "r2")},
            "logS_mol_per_L": {k: {"mean": agg("logS", k)[0], "sd": agg("logS", k)[1]}
                               for k in ("mae", "rmse", "r2")},
        }
    out["_predict_the_mean_reference"] = {
        "label": "predict the test-set mean of ln x2 (assumption-free scale)",
        "mae_ln_x2": float(np.mean([mean_ref[s]["mae"] for s in SEEDS])),
        "rmse_ln_x2": float(np.mean([mean_ref[s]["rmse"] for s in SEEDS])),
        "n": mean_ref[SEEDS[0]]["n"],
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


def article_table(t1: dict, t2: dict) -> pd.DataFrame:
    rows = []
    for arm, label in ARMS.items():
        b = t1[arm]
        seeds = b["seeds"]
        rows.append({
            "tier": "this work",
            "model": label + ("" if len(seeds) == 3 else f" (seeds {seeds} only)"),
            "tex_model": TEX_MODEL[arm] + ("" if len(seeds) == 3
                                           else r" [seeds $42,43$ only\tnote{$\ast$}]"),
            "split": "solute scaffold (this corpus)",
            "n": b["n"],
            "mae_ln_x2": b["ln_x2"]["mae"]["mean"],
            "sd_mae_ln_x2": b["ln_x2"]["mae"]["sd"],
            "rmse_ln_x2": b["ln_x2"]["rmse"]["mean"],
            "mae_logS": b["logS_mol_per_L"]["mae"]["mean"],
            "rmse_logS": b["logS_mol_per_L"]["rmse"]["mean"],
            "r2_ln_x2": b["ln_x2"]["r2"]["mean"],
            "comparable_to": "each other (three seeds, one locked row set)",
        })
    mr = t1["_predict_the_mean_reference"]
    rows.append({
        "tier": "reference", "model": mr["label"],
        "tex_model": r"predict the test-set mean of $\lnx$",
        "split": "solute scaffold (this corpus)",
        "n": mr["n"], "mae_ln_x2": mr["mae_ln_x2"], "sd_mae_ln_x2": None,
        "rmse_ln_x2": mr["rmse_ln_x2"], "mae_logS": None, "rmse_logS": None,
        "r2_ln_x2": 0.0, "comparable_to": "the rows above; fixes the scale of ln x2",
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
            "mae_ln_x2": b["ln_x2"]["mae"], "sd_mae_ln_x2": None,
            "rmse_ln_x2": b["ln_x2"]["rmse"],
            "mae_logS": b["logS_mol_per_L"]["mae"], "rmse_logS": b["logS_mol_per_L"]["rmse"],
            "r2_ln_x2": b["ln_x2"]["r2"],
            "comparable_to": "each other; NOT to the scaffold rows (different split)",
        })
    for b in PUBLISHED:
        rows.append({
            "tier": "external, as published",
            "model": f"{b['model']} [{b['source']}]",
            "tex_model": _tex(b["model"]) + " " + b["bibcmd"],
            "split": b["test_set"],
            "n": None,
            "mae_ln_x2": None, "sd_mae_ln_x2": None, "rmse_ln_x2": None,
            "mae_logS": b["mae"], "rmse_logS": b["rmse"],
            "r2_ln_x2": None,
            "comparable_to": "nothing else in this table: different corpus, split and unit",
        })
    return pd.DataFrame(rows)


def latex_table(df: pd.DataFrame) -> str:
    lines = [
        "% Auto-generated by scripts/analysis/run_external_baseline_comparison.py.",
        "% Do not hand-edit: re-run the script.",
        r"\begin{tabular}{@{}llrrrr@{}}",
        r"\toprule",
        r"Model & Test set & $n$ & MAE $\lnx$ & RMSE $\log_{10}S$ & $R^2$ $\lnx$ \\",
        r"\midrule",
    ]
    tier_head = {
        "this work": r"\multicolumn{6}{@{}l}{\emph{This work, scaffold split; three seeds, mean $\pm$ s.d.}}\\",
        "reference": r"\multicolumn{6}{@{}l}{\emph{Scale reference on the same rows}}\\",
        "external, re-run here": r"\multicolumn{6}{@{}l}{\emph{External models re-run on this corpus, by-solute split---not comparable to the block above}}\\",
        "external, as published": r"\multicolumn{6}{@{}l}{\emph{As published, on their own corpora and splits, $\log_{10}S$ in mol\,L$^{-1}$}}\\",
    }
    seen = set()
    for _, r in df.iterrows():
        if r["tier"] not in seen:
            seen.add(r["tier"])
            lines.append(tier_head[r["tier"]])
        mae = _fmt(r["mae_ln_x2"])
        if r["sd_mae_ln_x2"] is not None and np.isfinite(r["sd_mae_ln_x2"] or np.nan):
            mae = f"{mae} $\\pm$ {r['sd_mae_ln_x2']:.2f}"
        split = TEX_SPLIT.get(r["split"], _tex(r["split"]))
        lines.append(
            f"{r['tex_model']} & {split} & "
            f"{'--' if r['n'] is None or not np.isfinite(r['n'] or np.nan) else int(r['n'])} & "
            f"{mae} & {_fmt(r['rmse_logS'])} & {_fmt(r['r2_ln_x2'])} \\\\"
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
                "encoder. The physics arm trails the direct control."
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
        print(df[["tier", "model", "split", "n", "mae_ln_x2", "rmse_logS", "r2_ln_x2"]].to_string(index=False))


if __name__ == "__main__":
    main()
