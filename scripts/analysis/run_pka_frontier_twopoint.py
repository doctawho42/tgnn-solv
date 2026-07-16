"""Experiment A2 (spine, real-data anchor) -- two-point slope sign on the pKa/Hammett arm.

The full physicality-accuracy frontier (Experiment A) sweeps the latent-supervision
weight lambda. The pKa rig already gives the two ENDPOINTS of that sweep, stratified by
closure fidelity, from committed artifacts -- no OPERA SDF or retraining required:

    lambda = 0   (free sigma_hat, no supervision)   = arm "physics_learned_sigma"
    lambda = inf (sigma_hat pinned to true Hammett)  = arm "sigma_oracle_fixed_LFER"

Physicality-deviation P = ||sigma_hat - sigma_true||: P>0 at lambda=0, P=0 at lambda=inf,
so d P < 0 from lambda=0 to inf. The frontier slope

    S = -d(MAE)/dP     (accuracy paid per unit of un-physicality)

has sign  sign(S) = sign(MAE_oracle - MAE_free)  (since dP<0). The law predicts:

    well-specified closure (meta/para): S < 0  (physicality helps; oracle << free)
    misspecified   closure (ortho):     S > 0  (physicality hurts; oracle >  free)

This computes that sign per stratum from results/pka_hammett/trained_by_stratum.json.
The full lambda-curve (intermediate points -> slope magnitude) needs the OPERA pKa_QR.sdf
and a retrain with a lambda*MSE(sigma_hat, g.sigma) supervision term (spec A2). Sign is
decisive without it.
"""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path("results/pka_hammett/trained_by_stratum.json")
OUT = Path("results/frontier/frontier_pka_twopoint.json")


def main() -> None:
    d = json.loads(SRC.read_text())
    strata = d["strata"]
    rows = []
    for name, blk in strata.items():
        arms = blk["arms"]
        free = arms["physics_learned_sigma"]["mae_mean"]      # lambda = 0
        oracle = arms["sigma_oracle_fixed_LFER"]["mae"]       # lambda = inf
        direct = arms["direct"]["mae_mean"]                   # black-box reference
        dmae = oracle - free                                  # sign(S) = sign(dmae)
        rows.append({
            "stratum": name,
            "n": blk["n"],
            "mae_free_lam0": free,
            "mae_oracle_laminf": oracle,
            "mae_direct": direct,
            "delta_mae_oracle_minus_free": round(dmae, 3),
            "S_sign": "positive (physicality HURTS -> misspecified)" if dmae > 0
                      else "negative (physicality HELPS -> well specified)",
        })

    summary = {
        "source": str(SRC),
        "definition": "S = -d(MAE)/dP, P=||sigma_hat-sigma_true||; sign(S)=sign(MAE_oracle-MAE_free)",
        "law": "well-specified closure -> S<=0 ; misspecified closure -> S>0",
        "strata": rows,
        "caveat": "endpoints only (lambda in {0, inf}); full curve/magnitude needs pKa_QR.sdf + supervised retrain (spec A2).",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))

    print("pKa frontier, two-point slope sign (spine A2, real data, from committed strata)")
    print(f"  {'stratum':<26} {'n':>5} {'free(l=0)':>10} {'oracle(l=inf)':>13} {'dMAE':>7}  S")
    for r in rows:
        tag = "HURTS (misspec)" if r["delta_mae_oracle_minus_free"] > 0 else "HELPS (well-spec)"
        print(f"  {r['stratum']:<26} {r['n']:>5} {r['mae_free_lam0']:>10.3f} "
              f"{r['mae_oracle_laminf']:>13.3f} {r['delta_mae_oracle_minus_free']:>+7.3f}  {tag}")
    print(f"\n  wrote {OUT}")


if __name__ == "__main__":
    main()
