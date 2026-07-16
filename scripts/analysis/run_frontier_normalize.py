"""Put every frontier anchor on ONE dimensionless axis (units flag from review).

Raw slopes are incommensurable: A1 synthetic S in [0, 0.17] vs A2 pKa S = +2.48 -- different MAE
units and different deviation normalisations, so they cannot share Fig 13's axis. This recomputes
a dimensionless slope by normalising BOTH axes to each system's free (lambda=0) operating point:

    x = D / D_free       (D = mean|z_hat - z*| : latent INFIDELITY; 0 = physical)
    y = MAE / MAE_free
    S_norm = -d(y)/d(x)  over the lambda-sweep   (dimensionless; comparable across systems)

Sign convention (unchanged, now correctly named): S_norm > 0  <=>  reducing infidelity (making the
latent more physical) INCREASES error  <=>  the closure is misspecified.

Also reports the endpoint fractional reference-input penalty  MAE_oracle/MAE_free - 1  where an
oracle (D=0) exists (pKa): the two-point dimensionless slope.

Reads the committed artifacts; no retraining.
    python scripts/analysis/run_frontier_normalize.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SYNTH = Path("results/frontier/frontier_synth.json")
PKA = Path("results/frontier/frontier_pka_curve.json")
OUT = Path("results/frontier/frontier_normalized.json")


def norm_slope(D, mae):
    """S_norm = -d(mae/mae_free)/d(D/D_free) over the sweep (free = largest-lambda-independent ref).

    free operating point = the lambda=0 row (max infidelity, no supervision) = first entry."""
    D, mae = np.asarray(D, float), np.asarray(mae, float)
    D_free, mae_free = D[0], mae[0]
    if D_free <= 0 or mae_free <= 0:
        return float("nan")
    x, y = D / D_free, mae / mae_free
    if x.std() < 1e-9:
        return 0.0
    return float(-np.polyfit(x, y, 1)[0])


def main():
    rows = []

    # --- A1 synthetic: per fidelity F, average normalized slope over family x shape ---
    syn = json.loads(SYNTH.read_text())
    pts = syn["points"]
    fids = sorted({p["fidelity"] for p in pts}, reverse=True)
    fams = sorted({p["family"] for p in pts})
    shps = sorted({p["shape"] for p in pts})
    for F in fids:
        slopes = []
        for fam in fams:
            for sh in shps:
                sub = sorted([p for p in pts if p["fidelity"] == F and p["family"] == fam
                              and p["shape"] == sh], key=lambda p: p["lam"])
                if len(sub) >= 3:
                    slopes.append(norm_slope([p["physicality"] for p in sub],
                                             [p["mae_rel"] for p in sub]))
        rows.append({"system": f"synthetic F={F:.2f}", "S_norm": round(float(np.mean(slopes)), 3),
                     "S_norm_sd": round(float(np.std(slopes)), 3), "endpoint_penalty": None})

    # --- A2 pKa: per stratum, normalized slope over lambda + endpoint oracle penalty ---
    pka = json.loads(PKA.read_text())
    for label, blk in pka["strata"].items():
        curve = blk["curve"]
        S = norm_slope([c["P_mean"] for c in curve], [c["mae_mean"] for c in curve])
        mae_free = curve[0]["mae_mean"]
        endpoint = blk["mae_oracle_laminf_P0"] / mae_free - 1.0 if mae_free > 0 else float("nan")
        rows.append({"system": f"pKa {label}", "S_norm": round(S, 3), "S_norm_sd": None,
                     "endpoint_penalty": round(endpoint, 3)})

    out = {"definition": "S_norm = -d(MAE/MAE_free)/d(D/D_free); D = latent infidelity ||z_hat-z*||. "
                         ">0 = misspecified. endpoint_penalty = MAE_oracle/MAE_free - 1 (pKa only).",
           "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print("Frontier anchors on one dimensionless axis  (S_norm > 0 = closure misspecified)")
    print(f"  {'system':<32} {'S_norm':>8} {'sd':>6} {'endpt penalty':>14}")
    for r in rows:
        sd = "" if r["S_norm_sd"] is None else f"{r['S_norm_sd']:.3f}"
        ep = "" if r["endpoint_penalty"] is None else f"{r['endpoint_penalty']:+.3f}"
        print(f"  {r['system']:<32} {r['S_norm']:>+8.3f} {sd:>6} {ep:>14}")
    print(f"\n  wrote {OUT}")


if __name__ == "__main__":
    main()
