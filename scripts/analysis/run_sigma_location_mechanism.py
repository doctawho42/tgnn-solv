"""Градуирован ли штраф по доле HB-окон растворителя — и не объясняется ли это трудностью растворителя.

Правило чтения и пороги объявлены ДО счёта в
`results/sigma_location_robustness/PRE_DECLARATION.md`, поправка 1.

НУЛЕВОЕ ПЛЕЧО здесь главное. Корреляция «штраф против доли HB-окон» сама по себе ничего не
доказывает: полярные растворители могут просто хуже предсказываться. Поэтому та же корреляция
считается для MAE КОНТРОЛЬНОГО плеча на тех же растворителях, и читается РАЗНОСТЬ.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

GEOM = Path("results/sigma_displacement_geometry")
RESID = Path("results/sigma_profile_residual")
OUT = Path("results/sigma_location_robustness")
TREATED, BASE, CONTROL = "core_to_corner", "core_to_core", "control"
#: Объявлены до счёта.
MIN_GAP_OVER_NULL = 0.15
STRONG_NULL_RHO = 0.5
NO_GRADIENT_RHO = 0.2


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = pd.read_csv(GEOM / "per_row.csv")
    mol = pd.read_csv(RESID / "per_molecule.csv")

    # доля HB-окон по ЭТАЛОННОМУ профилю: донор + акцептор
    mol["hb_frac_reference"] = mol.area_frac_reference_donor + mol.area_frac_reference_acceptor
    hb = mol.set_index(["seed", "smiles"]).hb_frac_reference

    per_seed: dict[int, dict] = {}
    frames = []
    for sd, g in rows.groupby("seed"):
        t = g[g.arm == TREATED].groupby("solvent_smiles").abs_err.mean()
        b = g[g.arm == BASE].groupby("solvent_smiles").abs_err.mean()
        c = g[g.arm == CONTROL].groupby("solvent_smiles").abs_err.mean()
        common = t.index.intersection(b.index).intersection(c.index)
        pen = (t[common] - b[common])
        have = [s for s in common if (sd, s) in hb.index]
        if len(have) < 8:
            per_seed[int(sd)] = {"n_solvents": len(have), "note": "слишком мало сопоставленных"}
            continue
        x = np.array([hb[(sd, s)] for s in have])
        p = pen[have].values
        ctrl = c[have].values
        rho_p, pv_p = spearmanr(p, x)
        rho_c, pv_c = spearmanr(ctrl, x)
        per_seed[int(sd)] = {
            "n_solvents": int(len(have)),
            "rho_penalty_vs_hb": float(rho_p), "p_penalty": float(pv_p),
            "rho_control_mae_vs_hb": float(rho_c), "p_control": float(pv_c),
            "gap_abs": float(abs(rho_p) - abs(rho_c)),
        }
        frames.append(pd.DataFrame({"seed": sd, "solvent": have, "penalty": p,
                                    "control_mae": ctrl, "hb_frac_reference": x}))

    good = [v for v in per_seed.values() if "rho_penalty_vs_hb" in v]
    rp = [v["rho_penalty_vs_hb"] for v in good]
    gaps = [v["gap_abs"] for v in good]
    rc = [v["rho_control_mae_vs_hb"] for v in good]

    res = {
        "thresholds_predeclared": {"min_gap_over_null": MIN_GAP_OVER_NULL,
                                   "strong_null_rho": STRONG_NULL_RHO,
                                   "no_gradient_rho": NO_GRADIENT_RHO},
        "per_seed": per_seed,
        "summary": {
            "median_rho_penalty": float(np.median(rp)) if rp else None,
            "median_rho_control_null": float(np.median(rc)) if rc else None,
            "median_gap": float(np.median(gaps)) if gaps else None,
            "seeds_rho_penalty_positive": int(sum(1 for x in rp if x > 0)),
            "seeds_gap_over_threshold": int(sum(1 for x in gaps if x > MIN_GAP_OVER_NULL)),
            "n_seeds": len(good),
        },
    }
    s = res["summary"]
    if s["n_seeds"] == 0:
        res["verdict"] = "НЕ ИЗМЕРЕНО: нет сопоставленных растворителей"
    elif (s["seeds_rho_penalty_positive"] >= 4 and s["seeds_gap_over_threshold"] >= 4):
        res["verdict"] = "МЕХАНИЗМ ПОДДЕРЖАН: отклик градуирован по доле HB-окон сильнее контрольного"
    elif abs(s["median_rho_control_null"] or 0) > STRONG_NULL_RHO or (s["median_gap"] or 0) <= MIN_GAP_OVER_NULL:
        res["verdict"] = ("ЭТО ПРО ТРУДНОСТЬ РАСТВОРИТЕЛЯ, НЕ ПРО ЗАМЫКАНИЕ: "
                          "нулевое плечо коррелирует не хуже")
    elif abs(s["median_rho_penalty"] or 0) < NO_GRADIENT_RHO or s["seeds_rho_penalty_positive"] not in (0, len(good)):
        res["verdict"] = "НЕТ ГРАДИЕНТА: знак не держится или связь слабее порога"
    else:
        res["verdict"] = "НЕРАЗРЕШЕНО: читать односторонней границей, не точкой"
    res["instrument_is_weak_by_construction"] = (
        "64-70 растворителей, Kish n ~17: отрицательный исход механизм НЕ закрывает")

    if frames:
        pd.concat(frames).to_csv(OUT / "per_solvent_mechanism.csv", index=False)
    (OUT / "mechanism.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
