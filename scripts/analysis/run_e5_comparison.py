"""Aggregate run_e5 arms: lock metrics to the cross-arm n_supervised intersection,
compute pre-registered criteria (rescue, keeps-constraint), and stratify by aux regime."""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from rdkit import Chem

_KEY = ["solute_smiles", "solvent_smiles", "T"]


def _round_key(df: pd.DataFrame) -> pd.DataFrame:
    """Round float `T` to 6 dp so bit-identical-float drift can't silently drop rows."""
    df = df.copy()
    df["T"] = df["T"].round(6)
    return df


def _supervised_finite(df: pd.DataFrame) -> pd.DataFrame:
    """Rows that are labelled AND finite-predicted.

    The `fin` half of this conjunction is OUTCOME-dependent: it would remove from
    every arm's score the rows some arm failed on, which biases the comparison in
    favour of whichever arm fails most.  On the deposited e5 runs it is inert, and
    that is audited, not assumed: over all 22 per-row files in
    results/e5_sigma_grounding/seed_{42,43,44}/ the count of non-finite ln_x2_pred
    is 0 in every file, across all 8103 test rows and not merely the labelled ones.
    The lock is therefore 5608 = the rows with has_solubility True, the same
    set for every arm, and deleting `fin` returns it unchanged; the remaining 2495
    rows carry a melting point and no solubility.  See SI Sec. "The scored row set,
    and why it is not arm-dependent".

    If a future arm DOES produce a non-finite ln_x2_pred, this function silently
    becomes arm-dependent again -- score on the labelled rows and report the
    per-arm non-finite count instead of intersecting it away.
    """
    df = df.drop_duplicates(_KEY, keep="first")
    if df["has_solubility"].dtype == object:
        sup = df["has_solubility"].map(lambda v: str(v).strip().lower() in ("true", "1"))
    else:
        sup = df["has_solubility"].fillna(False).astype(bool)
    fin = np.isfinite(df["ln_x2_pred"].to_numpy(dtype=float))
    return df[sup & fin]


def intersection_keys(frames: dict[str, pd.DataFrame]):
    """Keys (solute,solvent,T) supervised AND finite-pred in EVERY arm."""
    common = None
    for df in frames.values():
        elig = _supervised_finite(_round_key(df))
        keys = set(map(tuple, elig[_KEY].itertuples(index=False, name=None)))
        common = keys if common is None else (common & keys)
    return sorted(common or set())


def r2(true: np.ndarray, pred: np.ndarray) -> float:
    true = np.asarray(true, float)
    pred = np.asarray(pred, float)
    if true.size < 2:  # <2-row set has ss_tot ~ 0; R2 undefined, avoid false 1.0
        return float("nan")
    ss_res = float(np.sum((true - pred) ** 2))
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    return float(1.0 - ss_res / (ss_tot + 1e-12))


def is_ring_bearing(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(str(smiles))
    return bool(mol is not None and mol.GetRingInfo().NumRings() > 0)


def _metrics_on_keys(df: pd.DataFrame, keys) -> dict:
    idx = _round_key(df).drop_duplicates(_KEY, keep="first").set_index(_KEY)
    sub = idx.loc[[k for k in keys if k in idx.index]]
    if not keys or len(sub) == 0:
        return {"r2": float("nan"), "mae": float("nan"), "lngamma_std": float("nan"), "n": 0}
    true = sub["ln_x2_true"].to_numpy(float)
    pred = sub["ln_x2_pred"].to_numpy(float)
    lng = sub["ln_gamma2_pred"].to_numpy(float) if "ln_gamma2_pred" in sub else np.array([np.nan])
    lng = lng[np.isfinite(lng)]
    return {
        "r2": r2(true, pred),
        "mae": float(np.mean(np.abs(true - pred))),
        "lngamma_std": float(np.std(lng, ddof=1)) if lng.size > 1 else float("nan"),
        "n": int(len(true)),
    }


def evaluate_criteria(per_arm: dict, *, direct_label: str, lngamma_band) -> dict:
    """Score the two pre-registered criteria, distinguishing "failed" from "not tested".

    Both criteria used to collapse to `False` when they could not be evaluated at all --
    `rescue` whenever the `direct_label` arm was absent from this run, `keeps_constraint`
    whenever an arm carried no `ln_gamma2_pred` column. That is the failure mode this
    project treats as worse than a wrong positive: a negative that was never established
    reads exactly like one that was, and nothing downstream can tell them apart. The
    leak-free A1 gate runs `ungrounded` and `grounded_a` only, with no `directgnn` arm,
    so every seed's comparison.json said `rescue: false` for arms no comparator had been
    measured against.

    An unevaluable criterion is `None` now -- JSON `null` -- and `criteria_not_evaluated`
    says which, and why, so a reader who sees neither true nor false is told the reason
    rather than left to infer one.
    """
    lo, hi = lngamma_band
    direct_r2 = per_arm.get(direct_label, {}).get("r2", float("nan"))
    direct_missing = direct_label not in per_arm
    rescue, keeps, why = {}, {}, {}
    for label, mtr in per_arm.items():
        if direct_missing:
            rescue[label] = None
            why[f"rescue.{label}"] = (
                f"no {direct_label!r} arm in this run, so there is no comparator R^2"
            )
        elif not np.isfinite(direct_r2):
            rescue[label] = None
            why[f"rescue.{label}"] = f"{direct_label!r} arm scored a non-finite R^2"
        elif not np.isfinite(mtr["r2"]):
            rescue[label] = None
            why[f"rescue.{label}"] = "this arm scored a non-finite R^2"
        else:
            rescue[label] = bool(mtr["r2"] >= direct_r2)

        std = mtr.get("lngamma_std", float("nan"))
        if not np.isfinite(std):
            keeps[label] = None
            why[f"keeps_constraint.{label}"] = (
                "no finite ln_gamma2_pred spread (column absent, or fewer than two rows)"
            )
        else:
            keeps[label] = bool(lo <= std <= hi)
    return {"rescue": rescue, "keeps_constraint": keeps,
            "matched_direct_r2": direct_r2,
            "criteria_not_evaluated": why}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="append", required=True, help="LABEL=predictions.csv")
    ap.add_argument("--direct-label", default="directgnn")
    ap.add_argument("--lngamma-band", nargs=2, type=float, default=[1.0, 2.0])
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    frames = {}
    for spec in args.run:
        label, path = spec.split("=", 1)
        frames[label] = pd.read_csv(path)
    keys = intersection_keys(frames)
    if len(keys) == 0:
        raise SystemExit(
            "run_e5_comparison: empty cross-arm intersection (n_locked=0) — check "
            "--direct-label and that all arms share supervised, finite-prediction rows."
        )
    per_arm = {label: _metrics_on_keys(df, keys) for label, df in frames.items()}
    # ring/acyclic stratification of the locked key set
    ring_keys = [k for k in keys if is_ring_bearing(k[0])]
    acyc_keys = [k for k in keys if not is_ring_bearing(k[0])]
    strat = {
        label: {
            "ring_bearing": _metrics_on_keys(df, ring_keys),
            "acyclic": _metrics_on_keys(df, acyc_keys),
        } for label, df in frames.items()
    }
    criteria = evaluate_criteria(per_arm, direct_label=args.direct_label,
                                 lngamma_band=tuple(args.lngamma_band))
    out = {"n_locked": len(keys), "n_ring_bearing": len(ring_keys),
           "n_acyclic": len(acyc_keys), "per_arm": per_arm,
           "stratified": strat, "criteria": criteria,
           "lngamma_band": list(args.lngamma_band)}
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(criteria, indent=2))


if __name__ == "__main__":
    main()
