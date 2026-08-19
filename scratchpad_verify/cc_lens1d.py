import os; os.environ.setdefault("KMP_DUPLICATE_LIB_OK","TRUE")
import sys,csv;from pathlib import Path
import numpy as np,torch
ROOT=Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv");sys.path.insert(0,str(ROOT/"src"))
from tgnn_solv.layers import CosmoSacLayer
L=CosmoSacLayer().eval()
h=None
with open(ROOT/"results/sigma_profile_artifact/sigma_profiles.csv") as fh:
    r=csv.reader(fh);h=next(r);rows=[x for x in r if len(x)==len(h)]
ia,ip=h.index("sigma_area"),h.index("sigma_p_0")
area=np.array([float(x[ia]) for x in rows]);P=np.array([[float(v) for v in x[ip:ip+51]] for x in rows])
TEMPS=[298.15];FLOOR=0.7
rng=np.random.default_rng(7);picks=rng.choice(len(P),60,replace=False)
for npart in (9,):
  zs=[];ms=[]
  for draw in range(6):
    pj=rng.choice(len(P),npart,replace=False)
    part=torch.tensor(P[pj],dtype=torch.float32);ap=torch.tensor(area[pj],dtype=torch.float32)
    def lng(p,a):
        pp=torch.tensor(np.repeat(p[None,:],npart,0),dtype=torch.float32)
        return torch.cat([L._residual_ln_gamma2(pp,part,torch.full((npart,),float(a)),ap,torch.zeros(npart),torch.full((npart,),float(t)),n_iter=30) for t in TEMPS])
    with torch.no_grad():
        d=[ (lng(P[s][::-1].copy(),area[s])-lng(P[s],area[s])).numpy() for s in picks]
    d=np.array(d);dc=d-d.mean(1,keepdims=True); z=np.sqrt((dc**2).sum(1))/FLOOR
    zs.append(z);ms.append(np.median(np.abs(d),1))
  z=np.concatenate(zs);m=np.concatenate(ms)
  print(f"n_partners={npart}, 1 T, 6 draws x 60 molecules: median per-pair |dlng| {np.median(m):.3f}"
        f" frac(<{FLOOR}) {(m<FLOOR).mean():.1%} | z: median {np.median(z):.2f}, frac(z<2) {(z<2).mean():.1%}, frac(z<3) {(z<3).mean():.1%}")
