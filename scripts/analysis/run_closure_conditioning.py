#!/usr/bin/env python
"""Is the closure ill-conditioned along the direction the substitution moves, or is the learned
profile simply not an estimate of the reference one?

WHY THIS EXISTS
---------------
Wu, Xiao, Sun and Wang (J. Fluid Mech. 869:553, 2019) report the same shape of experiment in
another field: substituting Reynolds stresses carrying under 0.5% error from DNS into RANS produces
up to 35% velocity error.  Their diagnosis is ILL-CONDITIONING of the closure map -- the fixed
physical model amplifies a small input perturbation.  This manuscript's Sec. 3.3 diagnoses
something different: COMPENSATION -- the learned intermediate is not a noisy estimate of the
reference quantity but an effective parameter that has absorbed the closure's misspecification.

The two mechanisms make opposite predictions about one measurable quantity, and nothing in this
corpus measured it:

  ill-conditioning   ||delta||/||sigma|| is SMALL and the output change is LARGE.
                     amplification = (relative output change) / (relative input change) >> 1.
  compensation       ||delta||/||sigma|| is LARGE -- the learned profile is nowhere near the
                     reference -- and the output change is PROPORTIONATE.  amplification ~ 1.

So the amplification ratio, and above all the relative size of the substitution step itself,
separates them.  This script measures both on the rows the substitution was measured on.

WHAT IS COMPUTED
----------------
For every test row whose solute AND solvent both carry a VT-2005 reference profile:

  sigma_hat        the learned profiles, read off the one trained COSMO-SAC head the tree retains
                   (checkpoints/cosmo_sac/tgnn_cosmo.pt, the retired run of Sec. 3.3)
  sigma_star       the reference profiles, from results/sigma_profile_artifact/sigma_profiles.csv
  delta            sigma_star - sigma_hat, the direction the evaluation-time substitution moves
  ln gamma         through the FIXED CosmoSacLayer, at both, at infinite dilution

and the two nulls, because a ratio without a null arm is a number and not a finding:

  N1 area-preserving random direction of the SAME NORM as delta.  Isolates shape: it answers
     "does a step of this size in a random direction do this much damage?"
  N2 CHEMISTRY-BLIND SUBSTITUTION -- the reference profile of a DIFFERENT molecule, drawn from the
     same pool.  The project's own null idiom: the right kind of object, the wrong molecule.  It
     answers "is the reference profile of the correct molecule better than an arbitrary one?"

THE SEGMENT COUNT IS PART OF THE MAP.  CLAUDE.md: the retired run trained at 8 segment iterations
and was scored at 30, and the pair is a free hyperparameter between fitting and scoring.  A
conditioning number is a property of the map, so both counts are reported and neither is called
the answer.

Usage
-----
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_conditioning.py \
        --out results/closure_conditioning/summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.data.dataset import make_loader  # noqa: E402
from tgnn_solv.inference import load_model  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402


def _canonical(smiles: object) -> str | None:
    """RDKit canonical SMILES, or None. Imported late so a --help does not pay for RDKit."""
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    return Chem.MolToSmiles(mol) if mol is not None else None

CKPT = ROOT / "checkpoints/cosmo_sac/tgnn_cosmo.pt"
REFERENCE = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"


def learned_profiles(cache: Path, device: torch.device) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """(solute profiles, solvent profiles, row metadata) for the test split, from the retired head.

    Cached, because the forward pass over the split costs minutes on CPU and nothing in it depends
    on anything this script varies.
    """
    meta_path = cache.with_suffix(".meta.csv")
    if cache.exists() and meta_path.exists():
        z = np.load(cache)
        return z["p_solute"], z["p_solvent"], pd.read_csv(meta_path, low_memory=False)

    model, cfg = load_model(str(CKPT), device=device)
    model.eval()
    df = pd.read_csv(TEST, low_memory=False)
    loader = make_loader(
        df, batch_size=64, shuffle=False, num_workers=0, cache=True, drop_last=False,
        use_pair_temperature_batching=False,
        use_morgan_features=cfg.use_morgan_features, morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_augmentation=cfg.use_descriptor_augmentation,
        use_ionic_features=cfg.use_ionic_features,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.requires_group_prior_features,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
        explicit_h_small_molecules=cfg.explicit_h_small_molecules,
        explicit_h_max_heavy_atoms=cfg.explicit_h_max_heavy_atoms,
        use_pseudo_hansen=False, seed=42)

    p_sol, p_slv, temps = [], [], []
    with torch.no_grad():
        for sol_b, slv_b, targets in loader:
            _out, inter = model(sol_b, slv_b, targets["T"], targets=targets,
                                return_intermediates=True)
            p_sol.append(inter["nrtl_p_solute"].cpu().numpy())
            p_slv.append(inter["nrtl_p_solvent"].cpu().numpy())
            temps.append(targets["T"].cpu().numpy())
    P2 = np.concatenate(p_sol)
    P1 = np.concatenate(p_slv)
    meta = df.iloc[: len(P2)][["solute_smiles", "solvent_smiles", "temperature"]].copy()
    meta["T"] = np.concatenate(temps)[: len(P2)]
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, p_solute=P2, p_solvent=P1)
    meta.to_csv(meta_path, index=False)
    return P2, P1, meta


def ln_gamma(layer: CosmoSacLayer, P2: torch.Tensor, P1: torch.Tensor, T: torch.Tensor,
             n_iter: int) -> torch.Tensor:
    """ln gamma_2^inf through the fixed closure at a given segment-iteration count."""
    layer.n_iter_eval = n_iter
    layer.eval()
    A2, A1 = P2.sum(-1), P1.sum(-1)
    # The Staverman-Guggenheim term needs volumes this deposit does not carry, and it is a function
    # of area and volume alone -- it does not read the profile SHAPE, which is the whole of what
    # the substitution moves.  Dropping it prices the residual term, which is the term under test.
    return layer.ln_gamma_inf(P2, P1, A2, A1, None, None, T)


def relative_condition_number(P2: np.ndarray, P1: np.ndarray, T: np.ndarray,
                              n_iter: int) -> np.ndarray:
    """kappa = ||J|| * ||sigma|| / |ln gamma|, the LOCAL RELATIVE CONDITION NUMBER of the closure.

    THIS IS WU ET AL.'S OWN METRIC, and it is reported so that their diagnosis and this one can be
    read on the same axis rather than argued about.  They evaluate a local condition number of the
    RANS operator and conclude the map amplifies input error; kappa here is the same quantity for
    sigma -> ln gamma^inf: the factor by which a relative perturbation of the input is multiplied,
    in the worst direction, to first order.

    WHAT IT DOES AND DOES NOT SETTLE.  kappa is a WORST-CASE, INFINITESIMAL number: it bounds the
    amplification over all directions and it is a first-order statement.  The substitution is
    neither -- it moves 1.5 times the profile's own norm, which is not infinitesimal, and it moves
    in one particular direction.  So a large kappa does not by itself explain the degradation, and
    that is exactly the gap the directional measurement above fills.  Reported together, they say:
    the map CAN amplify by kappa, and along the direction the substitution actually takes it does
    not.

    The gradient is taken with respect to both profiles jointly (the 102-vector the substitution
    moves), which is the object the amplification above is also computed on.
    """
    layer = CosmoSacLayer(None)
    layer.n_iter_eval = n_iter
    layer.eval()
    out = np.empty(len(P2))
    for i in range(len(P2)):
        p2 = torch.tensor(P2[i], dtype=torch.float32, requires_grad=True)
        p1 = torch.tensor(P1[i], dtype=torch.float32, requires_grad=True)
        lng = layer.ln_gamma_inf(p2[None], p1[None], p2.sum()[None], p1.sum()[None],
                                 None, None, torch.tensor([T[i]], dtype=torch.float32))[0]
        g2, g1 = torch.autograd.grad(lng, (p2, p1))
        jac = float(torch.linalg.vector_norm(torch.cat([g2, g1])))
        sig = float(np.linalg.norm(np.concatenate([P2[i], P1[i]])))
        out[i] = jac * sig / max(abs(float(lng.detach())), 1e-6)
    return out


def _relative(delta: np.ndarray, base: np.ndarray) -> np.ndarray:
    return np.linalg.norm(delta, axis=-1) / np.maximum(np.linalg.norm(base, axis=-1), 1e-12)


def _boot_ci(values: np.ndarray, clusters: np.ndarray, rng: np.random.Generator,
             draws: int = 2000, stat: str = "median") -> list[float]:
    """90% percentile interval on a statistic of `values`, resampling SOLUTE clusters.

    The unit is the solute and not the row: 354 rows sit on 64 solutes, and a row-level interval
    would price a sample size the design does not have.  Matches the resampling unit of Sec. 3.

    `stat` MATTERS AND WAS WRONG ONCE.  Bootstrapping the median of a 0/1 indicator returns [1,1]
    whenever more than half the rows are 1 -- a degenerate interval that reads like certainty.  A
    fraction takes the mean; keep them separate.
    """
    f = np.median if stat == "median" else np.mean
    groups = [np.flatnonzero(clusters == c) for c in np.unique(clusters)]
    out = []
    for _ in range(draws):
        drawn = rng.integers(0, len(groups), len(groups))
        out.append(float(f(values[np.concatenate([groups[i] for i in drawn])])))
    return [round(float(np.percentile(out, 5)), 4), round(float(np.percentile(out, 95)), 4)]


#: Sec. 3.3's conditioning paragraph states eleven numbers from this measurement, in running prose,
#: which is the position all six stale values of this manuscript were found in.  They are bound
#: here rather than trusted.  --check-article fails if any has drifted from the deposit.
# The conditioning paragraph moved to the Supporting Information's positioning section on
# 2026-08-19 (the article's Sec. 3.3 length pass). The gate follows the prose; the 25 numerals it
# binds and the deposit behind them are unchanged.
SECTION = ROOT / "paper/sections/SI.tex"


def check_article(result: dict, section: Path) -> int:
    import re
    # WHITESPACE-NORMALISED BEFORE MATCHING.  This pattern spans four sentences and used to pin
    # the column each of them wrapped at; the 2026-08-19 readability pass moved a line break and
    # the gate reported the paragraph "reworded" with no bound value having changed.  Values are
    # bound, line breaks are not.  Same repair as check_donor_window_caption.py.
    tex = re.sub(r"\s+", " ", section.read_text())
    c8, c30 = result["cells"]["8"], result["cells"]["30"]
    sub8, sub30 = c8["substitution"], c30["substitution"]
    c8k, c30k = c8["relative_condition_number"], c30["relative_condition_number"]
    want = [
        ("kappa, n=8", f"{c8k['median']:.0f}"),
        ("its interval, low", f"{c8k['ci90'][0]:.0f}"),
        ("its interval, high", f"{c8k['ci90'][1]:.0f}"),
        ("kappa, n=30", f"{c30k['median']:.0f}"),
        ("its interval, low", f"{c30k['ci90'][0]:.0f}"),
        ("its interval, high", f"{c30k['ci90'][1]:.0f}"),
        ("matched rows", str(result["n_rows"])),
        ("solutes", str(result["n_solutes"])),
        ("solvents", str(result["n_solvents"])),
        ("share of the split", f"{100 * result['n_rows'] / result['n_rows_test_split']:.1f}"),
        ("relative step", f"{sub8['rel_input_step_median']:.2f}"),
        ("relative step, low", f"{sub8['rel_input_step_ci90'][0]:.2f}"),
        ("relative step, high", f"{sub8['rel_input_step_ci90'][1]:.2f}"),
        ("random-beats-substitution, n=8",
         f"{100 * c8['substitution_amplifies_less_than_random']['fraction_of_rows']:.0f}"),
        ("its interval, low",
         f"{100 * c8['substitution_amplifies_less_than_random']['ci90'][0]:.0f}"),
        ("its interval, high",
         f"{100 * c8['substitution_amplifies_less_than_random']['ci90'][1]:.0f}"),
        ("random-beats-substitution, n=30",
         f"{100 * c30['substitution_amplifies_less_than_random']['fraction_of_rows']:.0f}"),
        ("its interval, low",
         f"{100 * c30['substitution_amplifies_less_than_random']['ci90'][0]:.0f}"),
        ("its interval, high",
         f"{100 * c30['substitution_amplifies_less_than_random']['ci90'][1]:.0f}"),
        ("amplification, n=8", f"{sub8['amplification_median']:.2f}"),
        ("its interval, low", f"{sub8['amplification_ci90'][0]:.2f}"),
        ("its interval, high", f"{sub8['amplification_ci90'][1]:.2f}"),
        ("amplification, n=30", f"{sub30['amplification_median']:.2f}"),
        ("its interval, low", f"{sub30['amplification_ci90'][0]:.2f}"),
        ("its interval, high", f"{sub30['amplification_ci90'][1]:.2f}"),
    ]
    pattern = (r"condition number [^$]*\$[^$]*\$ at the\s+learned profile is \$(\d+)\$ "
               r"\$\[(\d+),(\d+)\]\$ at eight segment iterations and \$(\d+)\$ "
               r"\$\[(\d+),(\d+)\]\$\s+at thirty.*?"
               r"On the \$(\d+)\$ test rows whose solute and solvent both\s+"
               r"carry a VT-2005 profile \(\$(\d+)\$ solutes, \$(\d+)\$ solvents, \$([\d.]+)\\%\$ of the "
               r"split\), it is not\. The reference\s+profile stands \$([\d.]+)\$ \$\[([\d.]+),([\d.]+)\]\$ "
               r"times.*?on \$(\d+)\\%\$ \$\[(\d+),(\d+)\]\$ of those rows at eight segment iterations\s+"
               r"and on \$(\d+)\\%\$ \$\[(\d+),(\d+)\]\$ at thirty.*?"
               r"\(median \$([\d.]+)\$ \$\[([\d.]+),([\d.]+)\]\$ against \$([\d.]+)\$ "
               r"\$\[([\d.]+),([\d.]+)\]\$\)")
    m = re.search(pattern, tex, re.S)
    if m is None:
        print(f"FAIL: the conditioning paragraph is not in {section} in the form this gate reads; "
              f"it was reworded or removed")
        return 1
    bad = 0
    print("\narticle bind:")
    for (what, artifact), claimed in zip(want, m.groups()):
        ok = claimed == artifact
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {what:32s} paper {claimed:>8s}   deposit {artifact:>8s}")
    print(f"{len(want)} numerals bound, {bad} mismatched")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path,
                    default=ROOT / "results/closure_conditioning/summary.json")
    ap.add_argument("--cache", type=Path, default=None,
                    help="npz of learned profiles (default: beside --out)")
    ap.add_argument("--n-iter", type=int, nargs="+", default=[8, 30],
                    help="segment-iteration counts to report; the pair is a free hyperparameter")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--check-article", action="store_true",
                    help="also bind Sec. 3.3's numerals to this run and fail on any drift")
    a = ap.parse_args()

    device = torch.device("cpu")
    cache = a.cache or a.out.parent / "learned_profiles.npz"
    P2, P1, meta = learned_profiles(cache, device)
    print(f"learned profiles: {P2.shape} solute, {P1.shape} solvent")

    ref = pd.read_csv(REFERENCE)
    pcols = [c for c in ref.columns if c.startswith("sigma_p_")]
    if len(pcols) != P2.shape[1]:
        raise SystemExit(f"reference grid is {len(pcols)} bins, the head emits {P2.shape[1]}")

    # THE MATCH IS CANONICAL, and it is not a detail.  Keyed on the SMILES as written, the two
    # tables agree on 31 of the split's 2634 solutes and the matched set is 66 rows; canonicalised
    # through RDKit they agree on 64 and it is 354.  A five-fold difference in n, produced entirely
    # by string form, is the sort of thing that silently decides whether a measurement says
    # anything, so the raw count is reported beside the canonical one rather than replaced by it.
    table = {}
    for smiles, row in zip(ref["smiles"], ref[pcols].to_numpy(float)):
        key = _canonical(smiles)
        if key is not None:
            table.setdefault(key, row)
    sol_key = [_canonical(s) for s in meta["solute_smiles"]]
    slv_key = [_canonical(s) for s in meta["solvent_smiles"]]
    meta = meta.copy()
    meta["solute_key"], meta["solvent_key"] = sol_key, slv_key
    raw = sum((s in set(ref["smiles"])) and (v in set(ref["smiles"]))
              for s, v in zip(meta["solute_smiles"], meta["solvent_smiles"]))

    have = np.array([(s in table) and (v in table) for s, v in zip(sol_key, slv_key)])
    print(f"matched on the SMILES as written: {raw} rows; canonicalised: {have.sum()}")
    print(f"rows with a reference profile on BOTH sides: {have.sum()} of {len(have)} "
          f"({100 * have.mean():.1f}%)")
    if have.sum() < 30:
        raise SystemExit("too few matched rows to say anything; nothing is reported")

    idx = np.flatnonzero(have)
    S2 = np.stack([table[s] for s in meta["solute_key"].to_numpy()[idx]])
    S1 = np.stack([table[s] for s in meta["solvent_key"].to_numpy()[idx]])
    H2, H1, T = P2[idx], P1[idx], meta["T"].to_numpy(float)[idx]

    rng = np.random.default_rng(a.seed)
    clusters = meta["solute_key"].to_numpy()[idx]
    # N1: an area-preserving random direction of the same norm, one per row per side.
    def _rand_like(delta: np.ndarray, base: np.ndarray) -> np.ndarray:
        g = rng.standard_normal(delta.shape)
        g -= g.mean(-1, keepdims=True)                       # sum-zero: area preserved
        g *= (np.linalg.norm(delta, axis=-1, keepdims=True)
              / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12))
        out = base + g
        return np.clip(out, 0.0, None)                       # a profile is non-negative

    # N2: the reference profile of a DIFFERENT molecule, drawn from the same pool.
    pool = np.stack(list(table.values()))
    shuf2 = pool[rng.integers(0, len(pool), len(idx))]
    shuf1 = pool[rng.integers(0, len(pool), len(idx))]

    arms = {
        "substitution": (S2, S1),
        "random_direction": (_rand_like(S2 - H2, H2), _rand_like(S1 - H1, H1)),
        "chemistry_blind": (shuf2, shuf1),
    }

    t = lambda x: torch.tensor(np.ascontiguousarray(x), dtype=torch.float32)  # noqa: E731
    layer = CosmoSacLayer(None)
    result = {"n_rows": int(len(idx)), "n_rows_uncanonicalised": int(raw),
              "n_rows_test_split": int(len(meta)),
              "n_solutes": int(pd.unique(meta['solute_key'].to_numpy()[idx]).size),
              "n_solvents": int(pd.unique(meta['solvent_key'].to_numpy()[idx]).size),
              "checkpoint": str(CKPT.relative_to(ROOT)), "cells": {}}

    for n_iter in a.n_iter:
        base = ln_gamma(layer, t(H2), t(H1), t(T), n_iter).numpy()
        cell = {"ln_gamma_learned_median": float(np.median(base)),
                "ln_gamma_learned_absmedian": float(np.median(np.abs(base)))}
        per_arm_amp: dict[str, np.ndarray] = {}
        kappa = relative_condition_number(H2, H1, T, n_iter)
        # ITS OWN GENERATOR.  Drawing kappa's interval from `rng` shifts the stream the arm
        # bootstraps below then read, so adding this diagnostic silently moved three published
        # interval endpoints -- caught by --check-article on the first run.  A diagnostic must not
        # be able to change the numbers it is a diagnostic of.
        cell["relative_condition_number"] = {
            "median": float(np.median(kappa)),
            "ci90": _boot_ci(kappa, clusters, np.random.default_rng(a.seed + 1000)),
            "p90": float(np.percentile(kappa, 90)),
            "what": "||J|| ||sigma|| / |ln gamma| at the learned profile: worst-case, "
                    "first-order amplification of a RELATIVE input perturbation",
        }
        for name, (Q2, Q1) in arms.items():
            got = ln_gamma(layer, t(Q2), t(Q1), t(T), n_iter).numpy()
            d_in = np.concatenate([Q2 - H2, Q1 - H1], axis=-1)
            b_in = np.concatenate([H2, H1], axis=-1)
            rel_in = _relative(d_in, b_in)
            rel_out = np.abs(got - base) / np.maximum(np.abs(base), 1e-6)
            amp = rel_out / np.maximum(rel_in, 1e-12)
            cell[name] = {
                "rel_input_step_median": float(np.median(rel_in)),
                "rel_input_step_ci90": _boot_ci(rel_in, clusters, rng),
                "rel_output_change_median": float(np.median(rel_out)),
                "amplification_median": float(np.median(amp)),
                "amplification_ci90": _boot_ci(amp, clusters, rng),
                "amplification_p90": float(np.percentile(amp, 90)),
                "abs_ln_gamma_shift_median": float(np.median(np.abs(got - base))),
            }
            per_arm_amp[name] = amp

        # THE DISCRIMINATOR, stated as a per-row comparison rather than as a ratio of medians:
        # on what fraction of rows does the closure amplify the substitution direction LESS than a
        # random direction of the same norm?  Ill-conditioning along the substitution direction
        # predicts a small fraction; the compensation reading predicts no preference or the reverse.
        less = per_arm_amp["substitution"] < per_arm_amp["random_direction"]
        cell["substitution_amplifies_less_than_random"] = {
            "fraction_of_rows": float(less.mean()),
            "ci90": _boot_ci(less.astype(float), clusters, rng, stat="mean"),
        }
        result["cells"][str(n_iter)] = cell

        k = cell["relative_condition_number"]
        print(f"\n--- segment iterations n={n_iter} "
              f"(|ln gamma| median {cell['ln_gamma_learned_absmedian']:.3f}) ---")
        print(f"local relative condition number kappa = {k['median']:.2f} "
              f"[{k['ci90'][0]:.2f}, {k['ci90'][1]:.2f}], p90 {k['p90']:.2f}  "
              f"(worst-case, first-order)")
        print(f"{'arm':18s} {'rel. input':>11s} {'rel. output':>12s} {'amplification':>14s} "
              f"{'|d ln gamma|':>13s}")
        for name in arms:
            c = cell[name]
            print(f"{name:18s} {c['rel_input_step_median']:11.3f} "
                  f"{c['rel_output_change_median']:12.3f} {c['amplification_median']:14.3f} "
                  f"{c['abs_ln_gamma_shift_median']:13.3f}")
        d = cell["substitution_amplifies_less_than_random"]
        print(f"  the substitution direction amplifies LESS than a random one of the same norm "
              f"on {100 * d['fraction_of_rows']:.1f}% of rows "
              f"[{100 * d['ci90'][0]:.0f}, {100 * d['ci90'][1]:.0f}]")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nwrote {a.out}")
    if a.check_article and check_article(result, SECTION):
        raise SystemExit("the article and the deposit disagree")


if __name__ == "__main__":
    main()
