import sys, json, math, pathlib, numpy as np
from qiskit import transpile
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress.spec import default_spec
root=pathlib.Path(sys.argv[1])
BASIS=["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
rc=json.load(open(root/"results/compress/spinnet/robust.json"))["entries"]
def rots(path,a,b):
    ns={"__name__":"prog"}; exec(compile(path.read_text(),str(path),"exec"),ns)
    qc=ns["build"](default_spec("spinnet","step").with_angles(a,b)).circuit()
    low=transpile(qc,basis_gates=BASIS,optimization_level=0)
    return [(i.operation.name,float(i.operation.params[0])) for i in low.data if i.operation.name in("rz","p")]
pairs=[(0.37,0.61),(0.91,0.23),(1.7,1.0),(0.5,0.9),(1.3,0.4),(0.2,0.3)]
out={}
for e in sorted(rc):
    path=root/json.load(open(root/f"compress/archive/spinnet/entries/{e}.json"))["program_path"]
    R=[rots(path,a,b) for a,b in pairs]
    n={len(r) for r in R}; assert len(n)==1,(e,n)
    X=np.array([[a,b,1.0] for a,b in pairs]); worst=0.0; nl=0
    detail=[]
    for k in range(len(R[0])):
        th=np.array([R[j][k][1] for j in range(len(pairs))])
        c,res,*_=np.linalg.lstsq(X,th,rcond=None)
        resid=np.max(np.abs(X@c-th))
        c0m=(c[2]/(2*math.pi)); off=abs(c0m-round(c0m))*(2*math.pi)   # STRICT: constant offset must vanish mod 2pi
        bad=bool((resid>1e-9) or off>1e-9)
        nl+=bad
        if bad: detail.append((R[0][k][0],[round(float(x),6) for x in c],round(float(resid),9),round(float(off),6)))
    lin = nl==0
    out[e]={"own_angle_linear":bool(lin),"n_rot":len(R[0]),"n_bad":int(nl),"cache_linear":rc[e]["angle_linear"],"detail":detail[:3]}
    print(e,"own_linear",lin,"cache",rc[e]["angle_linear"],"n_rot",len(R[0]),"n_bad",nl, detail[:2],flush=True)
json.dump(out,open(root/"results/spinnet/tester/4_3b/probe_c_strict.json","w"),indent=1)
print("MISMATCH:",[e for e in out if out[e]["own_angle_linear"]!=out[e]["cache_linear"]])
