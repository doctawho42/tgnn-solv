"""Does the single-molecule flip stay 'below the noise floor' once you aggregate over partners?"""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys, csv
from pathlib import Path
import numpy as np, torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

L = CosmoSacLayer().eval()
PROF = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"
with open(PROF) as fh:
    rdr = csv.reader(fh); h = next(rdr); rows = [r for r in rdr if len(r) == len(h)]
ia, ip = h.index("sigma_area"), h.index("sigma_p_0")
area = np.array([float(r[ia]) for r in rows])
P = np.array([[float(v) for v in r[ip:ip + 51]] for r in rows])
shape = P / P.sum(1, keepdims=True)
rng = np.random.default_rng(3)
TEMPS = [273.15, 298.15, 323.15]
FLOOR = 0.7

picks = rng.choice(len(P), 60, replace=False)
res = {}
for npart in (1, 5, 60):
    pj = rng.choice(len(P), npart, replace=False)
    part = torch.tensor(P[pj], dtype=torch.float32)
    ap = torch.tensor(area[pj], dtype=torch.float32)

    def lng(p_np, a):
        pp = torch.tensor(np.repeat(p_np[None, :], npart, 0), dtype=torch.float32)
        return torch.cat([L._residual_ln_gamma2(pp, part, torch.full((npart,), float(a)), ap,
                                                torch.zeros(npart), torch.full((npart,), float(t)),
                                                n_iter=30) for t in TEMPS])
    med, z = [], []
    with torch.no_grad():
        for si in picks:
            b = lng(P[si], area[si]); m = lng(P[si][::-1].copy(), area[si])
            d = (m - b).numpy()
            med.append(np.median(np.abs(d)))
            # z-score for detecting the flip from n_obs measurements with iid noise sd=FLOOR
            z.append(np.sqrt((d ** 2).sum()) / FLOOR)
    med, z = np.array(med), np.array(z)
    res[npart] = (med, z)
    print(f"n_partners={npart:>2} (n_obs={npart*3:>3}):  median per-pair |dlng| = {np.median(med):.3f}"
          f"  frac(median<{FLOOR}) = {(med < FLOOR).mean():.1%}"
          f"  |  aggregate detection z: median {np.median(z):.1f},"
          f" frac(z<2) = {(z < 2).mean():.1%}, frac(z<3) = {(z < 3).mean():.1%}")
