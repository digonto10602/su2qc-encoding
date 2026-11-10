import sys, json, pathlib, mpmath
from qiskit import transpile
import pygridsynth
from su2plaq.spinnet import loop as L
root = pathlib.Path(sys.argv[1]); sp = L.spec(); out = {}
for stem in ("001-spinnet_v2_pairs9", "000-general", "002-spinnet_v2_flags4"):
    f = root/"compress/programs/spinnet/seed"/f"{stem}.py"; ns = {}; exec(compile(f.read_text(), str(f), "exec"), ns)
    qc = ns["build"](sp).circuit()
    t2 = transpile(qc, basis_gates=["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"], optimization_level=0)
    tf = sum(1 for i in t2.data if i.operation.name in ("t","tdg"))
    tr = 0; n = 0
    for i in t2.data:
        if i.operation.name in ("rz","p"):
            th = float(i.operation.params[0]); n += 1
            s = pygridsynth.gridsynth_gates(mpmath.mpf(th), mpmath.mpf("1e-6"))
            tr += str(s).count("T")
    out[stem] = {"T_fixed": tf, "n_rot": n, "T_rot_sum": tr, "T_total_own": tf + tr}
print(json.dumps(out))
