import sys, json, hashlib, pathlib
sys.path.insert(0, __file__.rsplit("/",1)[0])
from qiskit import transpile
from su2plaq.spinnet import loop as L
root = pathlib.Path(sys.argv[1]); sp = L.spec()
d = json.loads((root/"results/compress/spinnet/round-000.json").read_text())
import importlib.util
res = []
for c in d["candidates"]:
    f = root / c["program_path"]
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    ns = {}; exec(compile(f.read_text(), str(f), "exec"), ns)
    qc = ns["build"](sp).circuit()
    # own CX count: full decomposition to {cx, u}
    t = transpile(qc, basis_gates=["cx", "u"], optimization_level=0)
    ops = t.count_ops()
    # own T count of Clifford gates: count t/tdg in builder circuit + RCCX/CCX macro T content from a decomposed Clifford+T+rz basis
    t2 = transpile(qc, basis_gates=["cx", "h", "s", "sdg", "t", "tdg", "rz", "p", "x", "z", "cz"], optimization_level=0)
    o2 = t2.count_ops()
    nrot = sum(o2.get(k, 0) for k in ("rz", "p"))
    res.append({"label": c["label"], "sha_equal": sha == c["program_sha256"], "cx_own": ops.get("cx", 0), "cx_key": c["key"][0],
                "t_fixed_own": o2.get("t", 0) + o2.get("tdg", 0), "t_fixed_metrics": c["metrics"]["t_fixed"], "rot_own": nrot, "n_rot_metrics": c["metrics"]["n_rot"],
                "qubits_own": qc.num_qubits, "qubits_key": c["key"][3]})
print(json.dumps(res, indent=1))
