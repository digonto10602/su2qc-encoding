"""Tester 118: own (CX, sumT, rho, sum depth_CT, qubits) over the 20 E3 pairs for the CX=31 competitors; own rho by strict angle fit; own ranking.
depth_CT: lowered circuit with every rz/p replaced by my own pygridsynth word (exact pi/4 multiples as S/T words), QuantumCircuit.depth()."""
import sys, json, math, pathlib, numpy as np, mpmath, pygridsynth
from qiskit import transpile, QuantumCircuit
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress.spec import default_spec
root = pathlib.Path(".")
BASIS = ["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
pairs = [tuple(p) for p in json.load(open(root/"results/spinnet/tester/4_6_r5/probe_a.json"))["pairs"]]
EX = {0:"",1:"T",2:"S",3:"ST",4:"SS",5:"SST",6:"SSS",7:"SSST"}
cache = {}
def word(th, eps=1e-6):
    k = th/(math.pi/4)
    if abs(k-round(k)) < 1e-12: return EX[round(k) % 8]
    key = repr(th)
    if key not in cache: cache[key] = str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps))))
    return cache[key]
def build(path, a, b):
    ns = {"__name__": "prog"}; exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns["build"](default_spec("spinnet","step").with_angles(a,b)).circuit()
def lowered_depth(low):
    q = QuantumCircuit(low.num_qubits)
    for i in low.data:
        nm = i.operation.name; qs = [low.find_bit(x).index for x in i.qubits]
        if nm in ("rz","p"):
            for ch in reversed(word(float(i.operation.params[0]))):
                if ch == "H": q.h(qs[0])
                elif ch == "S": q.s(qs[0])
                elif ch == "T": q.t(qs[0])
                elif ch == "X": q.h(qs[0]); q.s(qs[0]); q.s(qs[0]); q.h(qs[0])
        else: q.append(i.operation, qs)
    return q.depth()
out = {}
for e in sys.argv[1:]:
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{e}.json")); f = root/ent["program_path"]
    Ts, Ds, CXs, Qs = [], [], set(), set(); angs = []; sk = None; same = True
    for (a, b) in pairs:
        qc = build(f, a, b); low = transpile(qc, basis_gates=BASIS, optimization_level=0)
        sk_now = [(i.operation.name, tuple(qc.find_bit(x).index for x in i.qubits)) for i in qc.data]; sk = sk or sk_now; same &= (sk_now == sk)
        tf = sum(1 for i in low.data if i.operation.name in ("t","tdg"))
        rots = [float(i.operation.params[0]) for i in low.data if i.operation.name in ("rz","p")]
        Ts.append(tf + sum(word(t).count("T") for t in rots)); angs.append(rots)
        Ds.append(lowered_depth(low)); Qs.add(qc.num_qubits)
        CXs.add(sum(1 for i in transpile(qc, basis_gates=["cx","u"], optimization_level=0).data if i.operation.name == "cx"))
    A = np.array(angs); X = np.array([[a,b,1.0] for a,b in pairs]); bad = 0
    for j in range(A.shape[1]):
        c, *_ = np.linalg.lstsq(X, A[:, j], rcond=None); res = np.max(np.abs(X@c - A[:, j]))
        c0 = c[2]/(2*math.pi); off = abs(c0 - round(c0))*2*math.pi
        bad += bool(res > 1e-9 or off > 1e-9)
    rho = 0 if bad == 0 else 1
    out[e] = {"cx": sorted(CXs), "sumT": int(sum(Ts)), "rho": rho, "n_nonlinear_rot": int(bad), "sumDepth": int(sum(Ds)), "qubits": sorted(Qs), "skeleton_same": same, "T": Ts, "depth": Ds, "laptop_key": ent["key"]}
    print(e, {k: v for k, v in out[e].items() if k not in ("T", "depth")}, flush=True)
json.dump(out, open("results/spinnet/tester/4_6_r5/robust_depth_" + sys.argv[1] + ".json", "w"), indent=1)
rc = json.load(open("results/compress/spinnet/robust.json"))["entries"]
for e in out:
    c = rc[e]; print(e, "cache robust_key", c["robust_key"], "t_eps equal", c["t_eps"] == out[e]["T"], "depth_ct equal", c["depth_ct"] == out[e]["depth"], "cache depth_sum", c["depth_sum"])
rows = sorted((out[e]["cx"][0], out[e]["sumT"], out[e]["rho"], out[e]["sumDepth"], out[e]["qubits"][0], tuple(out[e]["laptop_key"]), e) for e in out)
print("OWN RANKING (CX=31 competitors):"); [print("  ", r) for r in rows]
