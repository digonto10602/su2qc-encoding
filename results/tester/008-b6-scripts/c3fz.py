import sys,json,pathlib,math
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
import numpy as np
from su2plaq.compress import robust as RB, evaluate as E
from su2plaq.compress.spec import default_spec
d=json.load(open("/home/digimonk/Projects/su2qc-encoding/scratch/t419/new_fz.json"))["fuzzy_ub"]
rho1=sorted(r[0] for r in d["ranking"] if not r[3]); print("rho=1 ids (",len(rho1),"):",rho1)
spec=default_spec("fuzzy_ub","UB")
from su2plaq.compress import archive as A
arch=A.Archive.load("fuzzy_ub",root=pathlib.Path("/home/digimonk/Projects/su2qc-encoding"),n_alt=len(spec.alt_angles),strict=True)
ents={e.id:e for e in arch.entries()}
pairs=[*RB.ANGLE_SET,(spec.alpha,spec.beta)]
for eid in ("r12-F1-012","r10-F1-010","r10-F2-010"):
    p=pathlib.Path("/home/digimonk/Projects/su2qc-encoding")/ents[eid].program_path
    circs,_=E._build_in_subprocess(p.read_bytes(),[spec.with_angles(a,b) for a,b in pairs],E.BUILD_TIMEOUT_S)
    th=np.array([RB.rotation_angles(c) for c in circs]); A_=np.array(pairs)
    # affine fit
    X=np.c_[A_,np.ones(len(A_))]; co=np.linalg.lstsq(X[:20],th[:20],rcond=None)[0]
    res_aff=np.abs(X@co-th).max(); co0=np.linalg.lstsq(A_[:20],th[:20],rcond=None)[0]; res_lin=np.abs(A_@co0-th).max()
    off=co[2]; nz=off[np.abs(off)>1e-9]
    print(eid,"n rotations",th.shape[1],"affine resid",f"{res_aff:.2e}","linear resid",f"{res_lin:.2e}","n nonzero offsets",len(nz),"offsets/(pi/2):",np.round(nz/(math.pi/2),9).tolist())
