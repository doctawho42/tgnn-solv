#!/usr/bin/env python3
"""General fidelity-dial engine — Phase 2 of the general-theory expansion.

Reproducible, domain-free demonstration of the two structural facts behind the
"grounding paradox" (paper ``paper/grounding_paradox.tex``, memo
``paper/GENERAL_THEORY_MEMO.md``):

  DIAL (parts a,b): closure *fidelity* alone sets the true-input penalty.
      A teacher draws a latent z* and a target m = T(z*)+noise via a known map T.
      A FIXED candidate closure g_F reconstructs the target from z* under a tunable
      misspecification (fidelity F: F=1 -> g_F=T exactly; F falls -> further off).
      We measure  dR2 = R2(oracle g_F(z*)) - R2(free head fitted to m on z*).
      dR2 = 0 at F=1 and grows negative monotonically as F falls, ACROSS several
      non-chemistry teacher families and misspecification functional forms. This is
      B_clos manifesting: the free head recovers E[m|z*]=T, the oracle uses the
      misspecified g_F, so the gap is (R2_head - R2_oracle) ~ B_clos / Var(m).

  CONFLATION (part c): why the grounding gap Gamma is NOT a standalone certificate.
      Gamma := R_orc - R_e2e (oracle-through-closure risk minus best end-to-end
      composed risk). The hostile-referee counterexample (memo, Counterexample A):
      a *well-specified* closure (B_clos=0) can still give Gamma>0 when the
      intermediate z* is a LOSSY bottleneck (assumption A2 fails). We control A2 via
      --sufficiency and show:
        * A2 holds  -> Gamma tracks B_clos as fidelity varies (proxy is valid);
        * A2 fails, g well-specified -> B_clos=0 but Gamma>0, growing with the
          discarded variance. => Gamma conflates closure bias with input
          insufficiency; the convention-independent decomposition (Lemma 3) is the
          actual instrument.
      Construction keeps the closure's OUTER map linear so the composed end-to-end
      fit g(h(x)) reduces to OLS(m ~ x): R_e2e is exact and gradient-free.

PROVENANCE NOTE. The dial numbers previously quoted in synthetic-dial.tex
(F=0.76 -> -0.096, etc.) were never produced by committed code. This script is the
reproducible replacement; its output SUPERSEDES those narrative numbers. Run:

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_fidelity_dial.py \
        --out-json results/synthetic_dial/summary.json \
        --fig-dir paper/figs --seed 0

numpy + scikit-learn + matplotlib only (no torch/rdkit -> no libomp conflict).
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # defensive; no torch here anyway

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold


# --------------------------------------------------------------------------- #
# basic helpers
# --------------------------------------------------------------------------- #
def r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def standardize(v: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-std (so a deformation's magnitude is comparable to the signal)."""
    s = v.std()
    return (v - v.mean()) / s if s > 0 else v - v.mean()


# --------------------------------------------------------------------------- #
# teacher families  T: R^d -> R  (E[m | z*]).  Distinct nonlinearities = "domains".
# --------------------------------------------------------------------------- #
def make_teachers(rng: np.random.Generator, d: int) -> dict[str, Callable[[np.ndarray], np.ndarray]]:
    w = rng.standard_normal(d) / np.sqrt(d)
    w1 = rng.standard_normal(d) / np.sqrt(d)
    w2 = rng.standard_normal(d) / np.sqrt(d)
    return {
        # generic linear regression target
        "linear": lambda z: z @ w,
        # generic monotone-nonlinear closure (saturating)
        "monotone_nonlinear": lambda z: np.tanh(1.5 * (z @ w)),
        # kinetics-like: an Arrhenius/rate closure lives in exponential space
        "kinetics_exp": lambda z: np.exp(0.4 * (z @ w)),
        # PDE-surrogate-like: a fixed smooth oscillatory field (solution operator)
        "pde_field": lambda z: np.sin(z @ w1) + 0.5 * np.cos(1.3 * (z @ w2)),
    }


# --------------------------------------------------------------------------- #
# misspecification functionals  D: R^d -> R  (added to T, scaled by (1-F)).
# The paper's claim: monotone ordering holds across ALL of these -> it is a
# property of |misspecification|, not of one functional form.
# --------------------------------------------------------------------------- #
def make_shapes(rng: np.random.Generator, d: int) -> dict[str, Callable[[np.ndarray], np.ndarray]]:
    u = rng.standard_normal(d) / np.sqrt(d)
    return {
        "linear_bias": lambda z: z @ u,
        "quadratic": lambda z: (z @ u) ** 2 - 1.0,
        "cubic": lambda z: (z @ u) ** 3 - 3.0 * (z @ u),
        "abs": lambda z: np.abs(z @ u) - np.sqrt(2.0 / np.pi),
        "sinusoidal": lambda z: np.sin(2.0 * (z @ u)),
        "cross_term": lambda z: z[:, 0] * z[:, 1] if z.shape[1] >= 2 else (z @ u) ** 2 - 1.0,
    }


# --------------------------------------------------------------------------- #
# DIAL: dR2(F) across teacher families x misspecification shapes
# --------------------------------------------------------------------------- #
@dataclass
class DialRecord:
    family: str
    shape: str
    fidelity: float
    r2_oracle: float
    r2_head: float
    delta_r2: float           # r2_oracle - r2_head  (<= 0)
    b_clos_over_var: float     # (R2_head - R2_oracle) proxy for B_clos / Var(m)


def run_dial(
    rng: np.random.Generator,
    n: int,
    d: int,
    snr: float,
    fidelities: list[float],
    shapes_subset: list[str] | None,
) -> list[DialRecord]:
    teachers = make_teachers(rng, d)
    shapes = make_shapes(rng, d)
    if shapes_subset:
        shapes = {k: v for k, v in shapes.items() if k in shapes_subset}

    z = rng.standard_normal((n, d))
    records: list[DialRecord] = []

    for fam_name, T in teachers.items():
        t = np.asarray(T(z), dtype=float)
        sig = t.std()
        noise_sd = sig / np.sqrt(snr) if sig > 0 else 1.0 / np.sqrt(snr)
        m = t + rng.standard_normal(n) * noise_sd

        # free head: out-of-fold RandomForest ~ E[m | z*]  (the "learned head")
        head_pred = np.empty(n)
        kf = KFold(n_splits=5, shuffle=True, random_state=0)
        for tr, te in kf.split(z):
            rf = RandomForestRegressor(
                n_estimators=150, max_depth=None, min_samples_leaf=5,
                n_jobs=-1, random_state=0,
            )
            rf.fit(z[tr], m[tr])
            head_pred[te] = rf.predict(z[te])
        r2_head = r2(m, head_pred)

        for shape_name, D in shapes.items():
            d_unit = standardize(np.asarray(D(z), dtype=float))
            for F in fidelities:
                alpha = 1.0 - F                       # F=1 -> exact; F<1 -> deformed
                g = t + alpha * sig * d_unit          # FIXED misspecified closure g_F(z*)
                r2_oracle = r2(m, g)
                records.append(DialRecord(
                    family=fam_name, shape=shape_name, fidelity=float(F),
                    r2_oracle=r2_oracle, r2_head=r2_head,
                    delta_r2=r2_oracle - r2_head,
                    b_clos_over_var=r2_head - r2_oracle,
                ))
    return records


# --------------------------------------------------------------------------- #
# CONFLATION: Gamma vs B_clos, under A2 (sufficiency) on/off.
# Outer closure map kept LINEAR so composed end-to-end fit = OLS(m ~ x).
# --------------------------------------------------------------------------- #
@dataclass
class ConflationRecord:
    regime: str                # "A2_holds" | "A2_violated"
    knob: float                # fidelity F (A2_holds) or discarded-variance frac (A2_violated)
    b_clos: float              # closed-form E[(E[m|z*]-g(z*))^2]
    r_orc: float               # E[(m - g(z*))^2]
    r_e2e: float               # OLS(m ~ x) residual MSE  (best composed end-to-end)
    r_free: float              # E[Var(m|x)] estimate (OLS on full x, = r_e2e here)
    gamma: float               # r_orc - r_e2e


def _ols_mse(X: np.ndarray, y: np.ndarray) -> float:
    Xb = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xb, y, rcond=None)
    resid = y - Xb @ beta
    return float(np.mean(resid ** 2))


def run_conflation(
    rng: np.random.Generator,
    n: int,
    d: int,
    snr: float,
    fidelities: list[float],
) -> list[ConflationRecord]:
    records: list[ConflationRecord] = []
    a = rng.standard_normal(d) / np.sqrt(d)          # linear "captured" map coefficients (invertible outer closure)
    k = 3                                            # number of discarded coordinates
    b = rng.standard_normal(k) / np.sqrt(k)          # discarded-coordinate contribution

    # --- Panel 1: A2 HOLDS (z* sufficient; m depends only on captured coords) ---
    # Vary closure fidelity F on z*; show Gamma tracks B_clos.
    x_cap = rng.standard_normal((n, d))
    signal = x_cap @ a
    noise_sd = signal.std() / np.sqrt(snr)
    u = rng.standard_normal(d) / np.sqrt(d)
    shape = standardize(x_cap @ u)                   # a fixed linear misspecification direction
    sig = signal.std()
    for F in fidelities:
        m = signal + rng.standard_normal(n) * noise_sd     # A2: m ⟂ discarded coords
        alpha = 1.0 - F
        # E[m|z*] = signal (z* = x_cap is sufficient). Misspecified closure:
        g_z = signal + alpha * sig * shape                 # g(z*) with B_clos = alpha^2 sig^2 Var(shape)
        b_clos = float(np.mean((signal - g_z) ** 2))
        r_orc = float(np.mean((m - g_z) ** 2))
        # end-to-end: g outer-linear so g(h(x)) with linear h = OLS(m ~ x_cap)
        r_e2e = _ols_mse(x_cap, m)
        records.append(ConflationRecord(
            regime="A2_holds", knob=float(F), b_clos=b_clos, r_orc=r_orc,
            r_e2e=r_e2e, r_free=r_e2e, gamma=r_orc - r_e2e,
        ))

    # --- Panel 2: A2 VIOLATED (lossy bottleneck), closure WELL-SPECIFIED (B_clos=0) ---
    # z* = captured coords only; m also depends on discarded coords. g(z*)=E[m|z*] exactly.
    # Sweep the fraction of target variance carried by the discarded coords.
    for frac in [0.0, 0.1, 0.2, 0.35, 0.5, 0.7]:
        x_cap = rng.standard_normal((n, d))
        x_dis = rng.standard_normal((n, k))
        cap_signal = x_cap @ a
        dis_signal = x_dis @ b
        # scale discarded contribution so Var(dis) / Var(total signal) ~ frac
        cvar = cap_signal.var()
        if dis_signal.var() > 0 and frac > 0:
            scale = np.sqrt(frac / (1.0 - frac) * cvar / dis_signal.var())
        else:
            scale = 0.0
        dis_signal = dis_signal * scale
        total = cap_signal + dis_signal
        noise_sd = np.sqrt(total.var()) / np.sqrt(snr)
        m = total + rng.standard_normal(n) * noise_sd
        # WELL-SPECIFIED closure on z*: g(z*) = E[m|z*] = cap_signal + E[dis] = cap_signal (dis mean 0)
        g_z = cap_signal.copy()
        b_clos = float(np.mean((cap_signal - g_z) ** 2))     # == 0 by construction
        r_orc = float(np.mean((m - g_z) ** 2))               # = Var(dis) + noise = B_insuff
        x_full = np.column_stack([x_cap, x_dis])
        r_e2e = _ols_mse(x_full, m)                          # composed e2e sees full x -> ~ noise floor
        records.append(ConflationRecord(
            regime="A2_violated", knob=float(frac), b_clos=b_clos, r_orc=r_orc,
            r_e2e=r_e2e, r_free=r_e2e, gamma=r_orc - r_e2e,
        ))
    return records


# --------------------------------------------------------------------------- #
# figures
# --------------------------------------------------------------------------- #
def make_figures(dial: list[DialRecord], conf: list[ConflationRecord], fig_dir: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path as _Path
    _st = _Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"
    if _st.exists():
        plt.style.use(str(_st))

    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # Fig 1: dial dR2(F) per teacher family, averaged over misspecification shapes
    fams = sorted({r.family for r in dial})
    Fs = sorted({r.fidelity for r in dial}, reverse=True)
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    pretty = {"linear": "linear", "monotone_nonlinear": "monotone nonlinear",
              "kinetics_exp": "kinetics (exp.)", "pde_field": "PDE field"}
    for fam in fams:
        ys = []
        for F in Fs:
            vals = [r.delta_r2 for r in dial if r.family == fam and r.fidelity == F]
            ys.append(np.mean(vals))
        ax.plot(Fs, ys, marker="o", label=pretty.get(fam, fam.replace("_", " ")))
    ax.axhline(0, color="0.6", lw=0.8, ls="--")
    ax.set_xlabel("closure fidelity  F   (1 = exact map)")
    ax.set_ylabel(r"true-input penalty  $\Delta R^2 = R^2_{\rm oracle}-R^2_{\rm head}$")
    ax.set_title("Fidelity sets the true-input penalty (all domains, all shapes)")
    ax.invert_xaxis()
    ax.legend(fontsize=8, title="teacher family")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = fig_dir / f"fig_fidelity_dial.{ext}"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        written.append(str(p))
    plt.close(fig)

    # Fig 2: conflation — Gamma vs B_clos (A2 holds) | B_clos=0 but Gamma>0 (A2 violated)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
    a2 = [r for r in conf if r.regime == "A2_holds"]
    a2 = sorted(a2, key=lambda r: -r.knob)
    axes[0].plot([r.knob for r in a2], [r.b_clos for r in a2], marker="s", label=r"$B_{\rm clos}$ (measured)")
    axes[0].plot([r.knob for r in a2], [r.gamma for r in a2], marker="o", label=r"$\Gamma$ (oracle gap)")
    axes[0].set_xlabel("closure fidelity  F")
    axes[0].set_ylabel("risk units")
    axes[0].set_title("A2 holds: $\\Gamma$ tracks $B_{\\rm clos}$\n($\\Gamma$ is a valid proxy)")
    axes[0].invert_xaxis()
    axes[0].legend(fontsize=8)

    av = [r for r in conf if r.regime == "A2_violated"]
    av = sorted(av, key=lambda r: r.knob)
    axes[1].plot([r.knob for r in av], [r.b_clos for r in av], marker="s", label=r"$B_{\rm clos}$ (=0, well-spec.)")
    axes[1].plot([r.knob for r in av], [r.gamma for r in av], marker="o", label=r"$\Gamma$ (oracle gap)")
    axes[1].axhline(0, color="0.6", lw=0.8, ls="--")
    axes[1].set_xlabel("fraction of target variance discarded")
    axes[1].set_ylabel("risk units")
    axes[1].set_title("A2 violated, closure well-specified:\n$B_{\\rm clos}=0$ yet $\\Gamma>0$ (Counterexample A)")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = fig_dir / f"fig_grounding_conflation.{ext}"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        written.append(str(p))
    plt.close(fig)
    return written


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--d", type=int, default=4)
    ap.add_argument("--snr", type=float, default=8.0, help="signal-to-noise ratio Var(T)/Var(noise)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fidelities", type=float, nargs="+",
                    default=[1.0, 0.9, 0.76, 0.6, 0.38, 0.2, 0.0, -0.5])
    ap.add_argument("--shapes", type=str, nargs="*", default=None,
                    help="subset of misspecification shapes (default: all six)")
    ap.add_argument("--out-json", type=Path, default=Path("results/synthetic_dial/summary.json"))
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    dial = run_dial(rng, args.n, args.d, args.snr, args.fidelities, args.shapes)
    conf = run_conflation(rng, args.n, args.d, args.snr, args.fidelities)

    figs: list[str] = []
    if not args.no_figures:
        figs = make_figures(dial, conf, args.fig_dir)

    # concise reference table: dial dR2 averaged over shapes, per (family, F)
    fams = sorted({r.family for r in dial})
    Fs = sorted({r.fidelity for r in dial}, reverse=True)
    dial_table = {
        fam: {f"F={F:+.2f}": float(np.mean([r.delta_r2 for r in dial
                                             if r.family == fam and r.fidelity == F]))
              for F in Fs}
        for fam in fams
    }

    out = {
        "config": {"n": args.n, "d": args.d, "snr": args.snr, "seed": args.seed,
                   "fidelities": args.fidelities},
        "dial_delta_r2_by_family": dial_table,
        "dial_records": [asdict(r) for r in dial],
        "conflation_records": [asdict(r) for r in conf],
        "figures": figs,
        "note": "Supersedes the un-scripted dial numbers in synthetic-dial.tex.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))

    # human summary
    print(f"[dial] wrote {args.out_json}")
    print("[dial] dR2 (avg over 6 misspecification shapes), by teacher family:")
    header = "  family              " + "".join(f"{('F=%+.2f' % F):>9}" for F in Fs)
    print(header)
    for fam in fams:
        row = "  " + f"{fam:<20}" + "".join(f"{dial_table[fam][f'F={F:+.2f}']:>9.3f}" for F in Fs)
        print(row)
    print("\n[conflation] A2 HOLDS (Gamma should track B_clos):")
    for r in conf:
        if r.regime == "A2_holds":
            print(f"  F={r.knob:+.2f}  B_clos={r.b_clos:6.3f}  Gamma={r.gamma:6.3f}")
    print("[conflation] A2 VIOLATED, well-specified closure (B_clos=0, Gamma>0 => not a certificate):")
    for r in conf:
        if r.regime == "A2_violated":
            print(f"  discarded_frac={r.knob:.2f}  B_clos={r.b_clos:6.3f}  Gamma={r.gamma:6.3f}")
    if figs:
        print("\n[dial] figures:", ", ".join(figs))


if __name__ == "__main__":
    main()
