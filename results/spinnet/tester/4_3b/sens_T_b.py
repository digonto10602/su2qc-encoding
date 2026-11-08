"""Tester 116 (b): own sum T over the E3 angle set (my regenerated pairs, probe_a.json) for given entries.
T = T_fixed (t/tdg after lowering to cx,h,s,sdg,t,tdg,rz,p,x,z,cz) + sum over rz/p rotations of pygridsynth T (eps=1e-6), exact multiples of pi/4 costed 0/1 (as keys_own.py / report 113-114).
Usage: sens_T.py <root> <out.json>; 20 random (alpha,beta) in [0.05,2.0]x[0.05,1.2], random.Random(20261109), plus the 3 official pairs."""
import sys, json, math, random, pathlib, time
import numpy as np, mpmath, pygridsynth
from qiskit import transpile
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress.spec import default_spec
root = pathlib.Path(sys.argv[1]); outp = pathlib.Path(sys.argv[2])
BASIS = ["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
def build(path, a, b):
    ns = {"__name__": "prog"}; exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns["build"](default_spec("spinnet","step").with_angles(a,b)).circuit()
cache = {}
def word_T(th, eps=1e-6):
    k = th/(math.pi/4)
    if abs(k-round(k)) < 1e-12:
        return [0,1,0,1,0,1,0,1][round(k) % 8]
    key = round(th % (2*math.pi), 13)   # rz(th) and rz(th+2pi) differ only by a global sign; gridsynth works mod 2pi? keep the raw angle to be safe
    key = repr(th)
    if key not in cache:
        cache[key] = str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps)))).count("T")
    return cache[key]
def metrics(path, a, b):
    qc = build(path, a, b)
    low = transpile(qc, basis_gates=BASIS, optimization_level=0)
    tf = sum(1 for i in low.data if i.operation.name in ("t","tdg"))
    cx = sum(1 for i in transpile(qc, basis_gates=["cx","u"], optimization_level=0).data if i.operation.name == "cx")
    rots = [(i.operation.name, float(i.operation.params[0])) for i in low.data if i.operation.name in ("rz","p")]
    Tr = [word_T(th) for _, th in rots]
    return {"cx": cx, "T_fixed": tf, "T_rot": Tr, "T": tf + sum(Tr), "n_rot": len(rots), "kinds": [k for k,_ in rots]}
ents = {e: json.load(open(root/f"compress/archive/spinnet/entries/{e}.json")) for e in sys.argv[3:]}
paths = {e: root/ents[e]["program_path"] for e in ents}
pairs_in = json.load(open(root/"results/spinnet/tester/4_3b/probe_a.json"))["pairs"]
pairs = [tuple(p) for p in pairs_in]
res = {"pairs": pairs, "entries": {e: [] for e in ents}}
t0 = time.time()
for (a,b) in pairs:
    for e in ents:
        m = metrics(paths[e], a, b); m["alpha"], m["beta"] = a, b; res["entries"][e].append(m)
    print(a, b, {e: res["entries"][e][-1]["T"] for e in ents}, round(time.time()-t0,1), flush=True)
json.dump(res, open(outp, "w"), indent=1)
